"""Testes do registro de processados (data-delta.md §2 a §6, D-09, D-17)."""

from __future__ import annotations

import os
import stat
from datetime import datetime, timezone

import pytest

from email_nf_onedrive.registro.banco import (
    EstadoAviso,
    Registro,
    RegistroCorrompido,
    RegistroDuplicado,
    TransicaoInvalida,
)


def _dt(dia: int) -> datetime:
    return datetime(2026, 9, dia, 12, 0, tzinfo=timezone.utc)


def _campos(**extras):
    campos = dict(
        caixa_endereco="financeiro@empresa.example",
        caixa_indice=1,
        message_id="<m1@fornecedor.example>",
        sha256="a" * 64,
        nome_original="boleto.pdf",
        remetente="cobranca@fornecedor.example",
        assunto="Boleto",
        data_mensagem=_dt(10),
        classe="palavra-chave",
        estado="extraido",
    )
    campos.update(extras)
    return campos


@pytest.fixture
def caminho(home):
    return home / "var" / "registro.sqlite3"


def test_cria_banco_com_permissao_600(caminho):
    with Registro.abrir(caminho):
        pass
    assert caminho.exists()
    assert stat.S_IMODE(os.stat(caminho).st_mode) == 0o600


def test_esquema_registra_versao(caminho):
    with Registro.abrir(caminho) as reg:
        assert reg.meta_obter("versao_esquema") == "1"


def test_registrar_e_buscar(caminho):
    with Registro.abrir(caminho) as reg:
        anexo = reg.registrar_anexo(**_campos())
        assert anexo.estado == "extraido"
        assert anexo.tentativas_envio == 0
        encontrado = reg.buscar("financeiro@empresa.example", "<m1@fornecedor.example>", "a" * 64)
    assert encontrado == anexo
    assert encontrado.data_mensagem == _dt(10)


def test_chave_usa_endereco_em_minusculas(caminho):
    with Registro.abrir(caminho) as reg:
        reg.registrar_anexo(**_campos(caixa_endereco="Financeiro@Empresa.example"))
        assert reg.buscar("financeiro@empresa.example", "<m1@fornecedor.example>", "a" * 64)


def test_renumerar_caixa_nao_duplica(caminho):
    with Registro.abrir(caminho) as reg:
        reg.registrar_anexo(**_campos(caixa_indice=1))
        with pytest.raises(RegistroDuplicado):
            reg.registrar_anexo(**_campos(caixa_indice=2))


def test_estado_inicial_so_extraido_ou_retido(caminho):
    with Registro.abrir(caminho) as reg:
        with pytest.raises(ValueError):
            reg.registrar_anexo(**_campos(estado="enviado"))


def test_persistencia_entre_aberturas(caminho):
    with Registro.abrir(caminho) as reg:
        reg.registrar_anexo(**_campos())
    with Registro.abrir(caminho) as reg:
        assert reg.buscar("financeiro@empresa.example", "<m1@fornecedor.example>", "a" * 64)


def test_excecao_desfaz_a_transacao(caminho):
    with pytest.raises(RuntimeError):
        with Registro.abrir(caminho) as reg:
            reg.registrar_anexo(**_campos())
            raise RuntimeError("falha no meio")
    with Registro.abrir(caminho) as reg:
        assert reg.buscar("financeiro@empresa.example", "<m1@fornecedor.example>", "a" * 64) is None


# --- Máquina de estados -----------------------------------------------------------


def test_extraido_para_enviado(caminho):
    with Registro.abrir(caminho) as reg:
        anexo = reg.registrar_anexo(**_campos())
        reg.marcar_enviado(anexo.id, "Destino/2026-09-10_cobranca_boleto.pdf")
        atual = reg.buscar(anexo.caixa_endereco, anexo.message_id, anexo.sha256)
    assert atual.estado == "enviado"
    assert atual.caminho_destino == "Destino/2026-09-10_cobranca_boleto.pdf"


def test_falha_incrementa_tentativas_e_permite_nova_tentativa(caminho):
    with Registro.abrir(caminho) as reg:
        anexo = reg.registrar_anexo(**_campos())
        assert reg.marcar_falha_envio(anexo.id, "timeout") == 1
        assert reg.marcar_falha_envio(anexo.id, "403") == 2
        atual = reg.buscar(anexo.caixa_endereco, anexo.message_id, anexo.sha256)
        assert atual.estado == "falha-envio"
        assert atual.ultimo_erro == "403"
        reg.marcar_enviado(anexo.id, "Destino/x.pdf")
        assert reg.buscar(anexo.caixa_endereco, anexo.message_id, anexo.sha256).estado == "enviado"


@pytest.mark.parametrize("terminal", ["enviado", "retido"])
def test_estados_terminais_nao_mudam(caminho, terminal):
    with Registro.abrir(caminho) as reg:
        if terminal == "retido":
            anexo = reg.registrar_anexo(**_campos(estado="retido", classe="sem-classificacao"))
        else:
            anexo = reg.registrar_anexo(**_campos())
            reg.marcar_enviado(anexo.id, "Destino/x.pdf")
        with pytest.raises(TransicaoInvalida):
            reg.marcar_falha_envio(anexo.id, "erro")
        with pytest.raises(TransicaoInvalida):
            reg.marcar_enviado(anexo.id, "Destino/y.pdf")


def test_ultimo_erro_e_limitado(caminho):
    with Registro.abrir(caminho) as reg:
        anexo = reg.registrar_anexo(**_campos())
        reg.marcar_falha_envio(anexo.id, "e" * 2000)
        atual = reg.buscar(anexo.caixa_endereco, anexo.message_id, anexo.sha256)
    assert len(atual.ultimo_erro) == 500


# --- Consultas da janela de busca --------------------------------------------------


def test_consultas_da_janela(caminho):
    with Registro.abrir(caminho) as reg:
        caixa = "financeiro@empresa.example"
        assert reg.ultima_data_mensagem(caixa) is None
        assert reg.pendente_mais_antiga(caixa) is None

        enviado = reg.registrar_anexo(**_campos(message_id="<a>", data_mensagem=_dt(1)))
        reg.marcar_enviado(enviado.id, "Destino/a.pdf")
        falhou = reg.registrar_anexo(**_campos(message_id="<b>", data_mensagem=_dt(3)))
        reg.marcar_falha_envio(falhou.id, "erro")
        reg.registrar_anexo(**_campos(message_id="<c>", data_mensagem=_dt(5)))
        reg.registrar_anexo(**_campos(message_id="<d>", data_mensagem=_dt(10), estado="retido"))
        reg.registrar_anexo(**_campos(caixa_endereco="outra@empresa.example", data_mensagem=_dt(20)))

        assert reg.ultima_data_mensagem(caixa) == _dt(10)
        assert reg.pendente_mais_antiga(caixa) == _dt(3)
        assert sorted(a.message_id for a in reg.pendentes(caixa)) == ["<b>", "<c>"]


# --- Ocorrências, meta e avisos -----------------------------------------------------


def test_ocorrencia_e_registrada_uma_vez(caminho):
    with Registro.abrir(caminho) as reg:
        assert reg.registrar_ocorrencia("financeiro@empresa.example", "<x>", "sem-anexo")
        assert not reg.registrar_ocorrencia("financeiro@empresa.example", "<x>", "sem-anexo")
        assert reg.registrar_ocorrencia("financeiro@empresa.example", "<x>", "compactado")
        with pytest.raises(ValueError):
            reg.registrar_ocorrencia("financeiro@empresa.example", "<x>", "outro-tipo")


def test_meta(caminho):
    with Registro.abrir(caminho) as reg:
        assert reg.meta_obter("ultima_execucao_em") is None
        reg.meta_definir("ultima_execucao_em", "2026-09-18T12:00:00+00:00")
        assert reg.meta_obter("ultima_execucao_em") == "2026-09-18T12:00:00+00:00"


def test_estado_de_avisos(caminho):
    with Registro.abrir(caminho) as reg:
        assert reg.aviso_obter("caixa1:autenticacao") is None
        estado = EstadoAviso(
            causa="caixa1:autenticacao",
            primeira_ocorrencia=_dt(18),
            ultimo_aviso=None,
            ativa=True,
            mensagem="caixa 1: autenticação recusada",
            entrega_pendente=True,
        )
        reg.aviso_salvar(estado)
        assert reg.aviso_obter("caixa1:autenticacao") == estado
        assert reg.avisos_ativos() == [estado]
        assert reg.avisos_com_entrega_pendente() == [estado]

        resolvido = EstadoAviso(**{**estado.__dict__, "ativa": False, "entrega_pendente": False})
        reg.aviso_salvar(resolvido)
        assert reg.avisos_ativos() == []
        assert reg.avisos_com_entrega_pendente() == []


# --- Simulação e corrupção -------------------------------------------------------------


def test_simulacao_nao_persiste(caminho):
    with Registro.abrir(caminho) as reg:
        reg.registrar_anexo(**_campos(message_id="<existente>"))
    with Registro.abrir(caminho, simulacao=True) as reg:
        reg.registrar_anexo(**_campos(message_id="<simulado>"))
        assert reg.buscar("financeiro@empresa.example", "<simulado>", "a" * 64)
    with Registro.abrir(caminho) as reg:
        assert reg.buscar("financeiro@empresa.example", "<existente>", "a" * 64)
        assert reg.buscar("financeiro@empresa.example", "<simulado>", "a" * 64) is None


def test_simulacao_sem_banco_nao_cria_arquivo(caminho):
    with Registro.abrir(caminho, simulacao=True) as reg:
        reg.registrar_anexo(**_campos())
    assert not caminho.exists()


def test_banco_corrompido_aborta(caminho):
    caminho.write_bytes(b"isto nao e um banco sqlite" * 100)
    with pytest.raises(RegistroCorrompido):
        Registro.abrir(caminho)
    assert caminho.read_bytes().startswith(b"isto nao e")
