"""Testes da lógica de avisos (EM RF-07 a RF-09, fluxo B, data-delta.md §4)."""

from __future__ import annotations

import pytest

from email_nf_onedrive import segredos
from email_nf_onedrive.execucao.avisos import LIMITE_TEXTO, GerenciadorAvisos
from email_nf_onedrive.registro.banco import Registro


class TransporteFalso:
    """Registra as mensagens enviadas; pode simular indisponibilidade."""

    def __init__(self) -> None:
        self.enviadas: list[str] = []
        self.disponivel = True

    def __call__(self, texto: str) -> tuple[bool, str | None]:
        if not self.disponivel:
            return False, "timeout"
        self.enviadas.append(texto)
        return True, None


@pytest.fixture
def transporte():
    return TransporteFalso()


@pytest.fixture
def executar(home, relogio, transporte):
    """Simula uma execução: abre o registro, registra falhas e finaliza com o código dado."""
    caminho = home / "var" / "registro.sqlite3"

    def _executar(codigo: int, falhas: list[tuple[str, str]] = ()) -> None:
        with Registro.abrir(caminho) as reg:
            avisos = GerenciadorAvisos(reg, transporte, agora=relogio.agora)
            for causa, mensagem in falhas:
                avisos.registrar_falha(causa, mensagem)
            avisos.finalizar(codigo)

    return _executar


FALHA_CAIXA1 = ("caixa1:autenticacao", "caixa 1: autenticação recusada. Ação: verifique a senha de app no .env.")


def test_primeira_falha_notifica(executar, transporte):
    executar(1, [FALHA_CAIXA1])
    assert len(transporte.enviadas) == 1
    texto = transporte.enviadas[0]
    assert "código 1" in texto
    assert "caixa 1" in texto
    assert "autenticação recusada" in texto
    assert "verifique a senha de app" in texto


def test_falhas_da_mesma_execucao_viram_uma_mensagem(executar, transporte):
    executar(1, [FALHA_CAIXA1, ("caixa2:pasta", "caixa 2: pasta inexistente")])
    assert len(transporte.enviadas) == 1
    assert "caixa 2: pasta inexistente" in transporte.enviadas[0]


def test_mesma_falha_por_3_horas_gera_um_aviso(executar, transporte, relogio):
    for _ in range(6):
        executar(1, [FALHA_CAIXA1])
        relogio.avancar(minutes=30)
    assert len(transporte.enviadas) == 1


def test_falha_persistente_renotifica_apos_6_horas(executar, transporte, relogio):
    executar(1, [FALHA_CAIXA1])
    relogio.avancar(hours=6)
    executar(1, [FALHA_CAIXA1])
    assert len(transporte.enviadas) == 2


def test_causa_nova_notifica_mesmo_com_outra_suprimida(executar, transporte, relogio):
    executar(1, [FALHA_CAIXA1])
    relogio.avancar(minutes=30)
    executar(1, [FALHA_CAIXA1, ("onedrive:token", "OneDrive: reautorize o remote")])
    assert len(transporte.enviadas) == 2
    assert "reautorize" in transporte.enviadas[1]
    assert "caixa 1" not in transporte.enviadas[1]


def test_recuperacao_notificada_uma_vez(executar, transporte, relogio):
    executar(1, [FALHA_CAIXA1])
    relogio.avancar(minutes=30)
    executar(0)
    relogio.avancar(minutes=30)
    executar(0)
    assert len(transporte.enviadas) == 2
    assert "recuperado" in transporte.enviadas[1]
    assert "caixa 1 voltou a funcionar" in transporte.enviadas[1]


def test_sucesso_sem_falhas_anteriores_nao_notifica(executar, transporte):
    executar(0)
    assert transporte.enviadas == []


def test_falha_apos_recuperacao_notifica_de_novo(executar, transporte, relogio):
    executar(1, [FALHA_CAIXA1])
    relogio.avancar(minutes=30)
    executar(0)
    relogio.avancar(minutes=30)
    executar(1, [FALHA_CAIXA1])
    assert len(transporte.enviadas) == 3


def test_aviso_nao_entregue_e_reenviado_na_execucao_seguinte(executar, transporte, relogio):
    transporte.disponivel = False
    executar(1, [FALHA_CAIXA1])
    assert transporte.enviadas == []
    transporte.disponivel = True
    relogio.avancar(minutes=30)
    executar(1, [FALHA_CAIXA1])
    assert len(transporte.enviadas) == 1
    assert "caixa 1" in transporte.enviadas[0]


def test_recuperacao_nao_entregue_e_reenviada(executar, transporte, relogio):
    executar(1, [FALHA_CAIXA1])
    transporte.disponivel = False
    relogio.avancar(minutes=30)
    executar(0)
    transporte.disponivel = True
    relogio.avancar(minutes=30)
    executar(0)
    assert len(transporte.enviadas) == 2
    assert "recuperado" in transporte.enviadas[1]


def test_texto_truncado_no_limite_do_telegram(executar, transporte):
    falhas = [(f"anexo:{i}:tentativas", "x" * 300) for i in range(30)]
    executar(1, falhas)
    texto = transporte.enviadas[0]
    assert len(texto) <= LIMITE_TEXTO == 4096
    assert texto.endswith("(ver log)")


def test_mensagem_nunca_contem_segredos(executar, transporte):
    segredos.registrar("senha-de-app-secreta")
    executar(1, [("caixa1:autenticacao", "caixa 1: servidor recusou senha-de-app-secreta")])
    assert "senha-de-app-secreta" not in transporte.enviadas[0]
    assert "****" in transporte.enviadas[0]
