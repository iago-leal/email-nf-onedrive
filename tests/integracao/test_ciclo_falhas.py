"""Cenários de falha de ponta a ponta (T041, requirements.md §7)."""

from __future__ import annotations

import errno
import os
import time

import pytest

from email_nf_onedrive.cli import main

from .conftest import CAIXA_1, SENHA_1, TOKEN

pytestmark = pytest.mark.integracao

CAIXA_2 = "compras@empresa.example"
SENHA_2 = "app-senha-caixa-2"


def _com_caixa_2(cenario, senha_no_env=SENHA_2):
    cenario.servidor.adicionar_caixa(CAIXA_2, SENHA_2)
    cenario.env.update({"EMAIL2": CAIXA_2, "IMAP_HOST_EMAIL2": "imap2.example"})
    if senha_no_env is not None:
        cenario.env["SENHA_EMAIL2"] = senha_no_env


def test_caixa_sem_senha_nao_impede_as_demais(cenario):
    _com_caixa_2(cenario, senha_no_env=None)
    cenario.entregar("boleto_simples.eml")
    assert cenario.executar("executar") == 1
    assert len(cenario.arquivos_no_destino()) == 1
    assert "caixa 2: SENHA_EMAIL2 ausente" in cenario.transporte.enviadas[0]
    assert ("LOGIN", CAIXA_2) not in cenario.servidor.comandos


def test_senha_errada_so_na_caixa_2_sai_com_codigo_1(cenario):
    _com_caixa_2(cenario, senha_no_env="senha-errada")
    cenario.entregar("boleto_simples.eml")
    assert cenario.executar("executar") == 1
    aviso = cenario.transporte.enviadas[0]
    assert "execução com falha (código 1)" in aviso
    assert "caixa 2: autenticação recusada" in aviso
    assert "verifique a senha de app" in aviso
    assert len(cenario.arquivos_no_destino()) == 1


def test_todas_as_caixas_com_falha_sai_com_codigo_2(cenario):
    cenario.servidor.fora_do_ar.add("imap1.example")
    assert cenario.executar("executar") == 2
    assert "servidor IMAP inacessível" in cenario.transporte.enviadas[0]


def test_erro_global_de_configuracao_sem_acesso_a_rede(cenario):
    del cenario.env["RCLONE_REMOTE"]
    assert cenario.executar("executar") == 2
    assert cenario.servidor.comandos == []
    assert "configuração: RCLONE_REMOTE ausente" in cenario.log()
    assert cenario.transportes_criados == [(TOKEN, "42")]  # transporte de emergência
    assert "RCLONE_REMOTE ausente" in cenario.transporte.enviadas[0]


def test_data_inicial_fora_do_formato_aborta_antes_da_rede(cenario):
    cenario.env["DATA_INICIAL"] = "18/09/2026"
    assert cenario.executar("executar") == 2
    assert cenario.servidor.comandos == []
    assert "DATA_INICIAL fora do formato AAAA-MM-DD" in cenario.log()


def test_supressao_por_6_horas_e_aviso_de_recuperacao(cenario):
    cenario.env["SENHA_EMAIL1"] = "senha-errada"
    for _ in range(6):  # 3 h de falha contínua, uma execução a cada 30 min
        assert cenario.executar("executar") == 2
        cenario.relogio.avancar(minutes=30)
    assert len(cenario.transporte.enviadas) == 1

    cenario.relogio.avancar(hours=3)  # 6 h desde o primeiro aviso
    assert cenario.executar("executar") == 2
    assert len(cenario.transporte.enviadas) == 2

    cenario.env["SENHA_EMAIL1"] = SENHA_1
    cenario.relogio.avancar(minutes=30)
    assert cenario.executar("executar") == 0
    assert "recuperado: caixa 1 voltou a funcionar" in cenario.transporte.enviadas[-1]
    cenario.relogio.avancar(minutes=30)
    assert cenario.executar("executar") == 0
    assert len(cenario.transporte.enviadas) == 3  # a recuperação é avisada uma vez só


def test_telegram_fora_do_ar_reenvia_na_execucao_seguinte(cenario):
    cenario.env["SENHA_EMAIL1"] = "senha-errada"
    cenario.transporte.disponivel = False
    assert cenario.executar("executar") == 2
    assert "aviso não entregue: timeout" in cenario.log()
    cenario.transporte.disponivel = True
    cenario.relogio.avancar(minutes=30)
    assert cenario.executar("executar") == 2
    assert len(cenario.transporte.enviadas) == 1


def test_credenciais_ausentes_do_log_dos_avisos_e_do_verificar_config(cenario, capsys):
    _com_caixa_2(cenario, senha_no_env="senha-errada-que-nao-pode-vazar")
    cenario.entregar("boleto_simples.eml")
    cenario.executar("executar")
    cenario.env["TELEGRAM_CHAT_ID"] = ""  # erro global com par do Telegram incompleto
    del cenario.env["DATA_INICIAL"]
    cenario.executar("executar")
    assert cenario.executar("verificar-config") == 2
    saida = capsys.readouterr()
    textos = [cenario.log(), *cenario.transporte.enviadas, saida.out, saida.err]
    for segredo in (SENHA_1, SENHA_2, "senha-errada-que-nao-pode-vazar", TOKEN):
        assert all(segredo not in texto for texto in textos), segredo


def test_verificar_config_lista_caixas_com_senha_mascarada(cenario, capsys):
    cenario.env["EMAIL3"] = "sem-arroba"
    assert cenario.executar("verificar-config") == 0
    saida = capsys.readouterr().out
    assert f"1 · {CAIXA_1} · INBOX · {cenario.destino} · empresa ACME · senha ****" in saida
    assert "inválida: caixa 3: EMAIL3 inválido" in saida
    assert SENHA_1 not in saida
    assert cenario.servidor.comandos == []


def test_execucoes_sobrepostas(cenario):
    trava = cenario.home / "var" / "execucao.lock"
    trava.write_text(f"{os.getpid()}\n{time.time()}\n")
    inicio = time.monotonic()
    assert cenario.executar("executar") == 0
    assert time.monotonic() - inicio < 1
    assert "execução anterior em andamento" in cenario.log()
    assert cenario.servidor.comandos == []
    assert trava.exists()  # a trava alheia não é removida


def test_trava_abandonada_e_removida(cenario):
    trava = cenario.home / "var" / "execucao.lock"
    trava.write_text(f"{os.getpid()}\n{time.time() - 30 * 60}\n")
    assert cenario.executar("executar") == 0
    assert "trava abandonada removida" in cenario.log()
    assert cenario.servidor.comandos
    assert not trava.exists()


def _fabrica_que_falha(erro):
    def fabrica(_caixa):
        raise erro
    return fabrica


def test_excecao_nao_prevista(cenario):
    deps = cenario.deps()
    deps.fabrica_imap = _fabrica_que_falha(RuntimeError("defeito de programação"))
    assert cenario.executar("executar", deps=deps) == 2
    log = cenario.log()
    assert "exceção não prevista" in log and "Traceback" in log
    assert "exceção não prevista (RuntimeError)" in cenario.transporte.enviadas[0]
    assert not (cenario.home / "var" / "execucao.lock").exists()
    assert list((cenario.home / "var" / "trabalho").iterdir()) == []


def test_disco_cheio(cenario):
    deps = cenario.deps()
    deps.fabrica_imap = _fabrica_que_falha(OSError(errno.ENOSPC, "No space left on device"))
    assert cenario.executar("executar", deps=deps) == 2
    assert "disco cheio" in cenario.transporte.enviadas[0]


def test_testar_onedrive(cenario, capsys):
    assert cenario.executar("testar-onedrive") == 0
    assert f"OneDrive: escrita confirmada em {cenario.destino}" in capsys.readouterr().out
    assert cenario.arquivos_no_destino() == []
    cenario.env["DESTINO_ONEDRIVE"] = str(cenario.destino.with_name("NAO-EXISTE"))
    assert cenario.executar("testar-onedrive") == 2


def test_home_por_variavel_de_ambiente(cenario, monkeypatch, capsys):
    cenario._escrever_env(cenario.env)
    monkeypatch.setenv("EMAIL_NF_HOME", str(cenario.home))
    assert main(["verificar-config"]) == 0
    assert CAIXA_1 in capsys.readouterr().out
