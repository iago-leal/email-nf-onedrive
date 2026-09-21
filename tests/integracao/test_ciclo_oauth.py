"""Ciclo com caixas em modo oauth, caminho feliz (feature 002, RF-01, RF-07, D-06, D-13, RN-01)."""

from __future__ import annotations

import pytest

from .conftest import CLIENT_SECRET, SENHA_1, TOKEN

pytestmark = pytest.mark.integracao

CAIXA_2 = "fiscal@cliente.example"
DURAVEL_2 = "1//duravel-da-caixa-2"
TEMPORARIA_2 = "ya29.temporaria-da-caixa-2"


def test_instalacao_mista_coleta_as_caixas_dos_dois_modos(cenario_oauth):
    cenario = cenario_oauth
    cenario.caixa_oauth(2, CAIXA_2)
    cenario.entregar("boleto_simples.eml")
    cenario.entregar("nfe_xml.eml", caixa=CAIXA_2)
    autorizacao = cenario.dir_autorizacoes / f"{CAIXA_2}.json"
    antes = autorizacao.read_bytes()

    assert cenario.executar("executar") == 0

    assert len(cenario.arquivos_no_destino()) == 2
    log = cenario.log()
    assert "caixa 1: conectada (senha)" in log
    assert "caixa 2: conectada (oauth)" in log
    assert "resumo: 2 caixas, 2 extraídos, 2 enviados, 0 falhas" in log
    assert "de autorização" not in log  # D-13: o segmento só aparece quando há falha de autorização
    assert cenario.servico.contagem("/token", "refresh_token") == 1
    assert ("LOGIN", CAIXA_2) not in cenario.servidor.comandos
    assert autorizacao.read_bytes() == antes  # RF-09: o ciclo nunca regrava a autorização
    assert cenario.transporte.enviadas == []


def test_nenhum_segredo_chega_ao_log(cenario_oauth):
    cenario = cenario_oauth
    cenario.caixa_oauth(2, CAIXA_2)
    cenario.entregar("nfe_xml.eml", caixa=CAIXA_2)
    assert cenario.executar("executar") == 0
    log = cenario.log()
    for segredo in (CLIENT_SECRET, DURAVEL_2, TEMPORARIA_2, SENHA_1, TOKEN):
        assert segredo not in log


def test_instalacao_sem_oauth_nao_fala_com_o_servico_de_autorizacao(cenario_oauth):
    cenario = cenario_oauth
    cenario.entregar("boleto_simples.eml")
    assert cenario.executar("executar") == 0
    assert cenario.servico.requisicoes == []
    assert "AUTHENTICATE" not in cenario.servidor.nomes_de_comandos()
    assert "resumo: 1 caixa, 1 extraídos, 1 enviados, 0 falhas" in cenario.log()


def test_credencial_temporaria_e_renovada_a_cada_execucao(cenario_oauth):
    cenario = cenario_oauth
    cenario.caixa_oauth(2, CAIXA_2)
    assert cenario.executar("executar") == 0
    assert cenario.executar("executar") == 0
    assert cenario.servico.contagem("/token", "refresh_token") == 2  # D-06: nada guardado entre execuções
    assert not (cenario.home / "var" / "trabalho").exists() or not list((cenario.home / "var" / "trabalho").iterdir())


def test_instalacao_so_com_caixas_oauth(cenario_oauth):
    cenario = cenario_oauth
    for chave in ("EMAIL1", "SENHA_EMAIL1", "EMPRESA_EMAIL1", "IMAP_HOST_EMAIL1"):
        del cenario.env[chave]
    cenario.caixa_oauth(2, CAIXA_2)
    cenario.entregar("boleto_simples.eml", caixa=CAIXA_2)
    assert cenario.executar("executar") == 0
    assert "LOGIN" not in cenario.servidor.nomes_de_comandos()
    assert len(cenario.arquivos_no_destino()) == 1


def test_simulacao_tambem_autentica_por_oauth(cenario_oauth):
    cenario = cenario_oauth
    cenario.caixa_oauth(2, CAIXA_2)
    cenario.entregar("nfe_xml.eml", caixa=CAIXA_2)
    assert cenario.executar("executar", "--simular") == 0
    assert cenario.arquivos_no_destino() == []
    assert "caixa 2: conectada (oauth)" in cenario.log()


def test_troca_de_modo_nao_duplica_documentos(cenario_oauth):
    """RN-07: a identidade da caixa é o endereço; mudar de senha para oauth não reenvia o que já foi arquivado."""
    from .conftest import CAIXA_1
    cenario = cenario_oauth
    cenario.entregar("boleto_simples.eml")
    assert cenario.executar("executar") == 0
    assert len(cenario.arquivos_no_destino()) == 1

    mensagens = cenario.servidor.caixas[CAIXA_1][1]
    cenario.caixa_oauth(1, CAIXA_1)
    cenario.servidor.caixas[CAIXA_1][1].update(mensagens)
    del cenario.env["SENHA_EMAIL1"]
    assert cenario.executar("executar") == 0

    assert "caixa 1: conectada (oauth)" in cenario.log()
    assert len(cenario.arquivos_no_destino()) == 1
    assert cenario.estados() == ["enviado"]


def test_permissao_aberta_da_autorizacao_vira_alerta_no_log(cenario_oauth):
    import os
    cenario = cenario_oauth
    cenario.caixa_oauth(2, CAIXA_2)
    os.chmod(cenario.dir_autorizacoes / f"{CAIXA_2}.json", 0o644)
    assert cenario.executar("executar") == 0  # RF-12: alerta, não bloqueio
    assert "permissão da autorização da caixa 2 mais aberta que 600" in cenario.log()
