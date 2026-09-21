"""Ciclo com falhas de autorização (feature 002, D-08, RF-08, RF-09, data-delta.md §7)."""

from __future__ import annotations

import pytest

from .conftest import CLIENT_SECRET

pytestmark = pytest.mark.integracao

CAIXA_2 = "fiscal@cliente.example"
CAIXA_3 = "compras@cliente.example"


def _autorizacao(cenario, endereco=CAIXA_2):
    return cenario.dir_autorizacoes / f"{endereco}.json"


def test_autorizacao_ausente(cenario_oauth):
    cenario = cenario_oauth
    cenario.caixa_oauth(2, CAIXA_2, autorizada=False)
    cenario.entregar("boleto_simples.eml")
    assert cenario.executar("executar") == 1
    assert len(cenario.arquivos_no_destino()) == 1  # a caixa em senha segue
    aviso = cenario.transporte.enviadas[0]
    assert "caixa 2: autorização OAuth ausente (rode autorizar-caixa 2)" in aviso
    assert cenario.servico.requisicoes == []
    assert "AUTHENTICATE" not in cenario.servidor.nomes_de_comandos()
    assert "resumo: 1 caixa, 1 extraídos, 1 enviados, 1 falhas, 1 de autorização" in cenario.log()


def test_invalid_grant_pede_nova_autorizacao_e_preserva_o_arquivo(cenario_oauth):
    cenario = cenario_oauth
    cenario.caixa_oauth(2, CAIXA_2, resposta="invalid_grant")
    antes = _autorizacao(cenario).read_bytes()
    assert cenario.executar("executar") == 1
    aviso = cenario.transporte.enviadas[0]
    assert "caixa 2: autorização OAuth recusada (rode autorizar-caixa 2)" in aviso
    assert "autenticação recusada" not in aviso  # RF-08: causa distinta da senha recusada
    assert _autorizacao(cenario).read_bytes() == antes
    assert "AUTHENTICATE" not in cenario.servidor.nomes_de_comandos()


def test_autorizacao_de_outro_cliente_oauth(cenario_oauth):
    cenario = cenario_oauth
    cenario.caixa_oauth(2, CAIXA_2)
    cenario.env["OAUTH_CLIENT_ID"] = "outro-cliente.apps.example"
    assert cenario.executar("executar") == 1
    assert "caixa 2: autorização OAuth inválida: autorização emitida para outro cliente OAuth (rode autorizar-caixa 2)" \
        in cenario.transporte.enviadas[0]
    assert cenario.servico.requisicoes == []


@pytest.mark.parametrize("resposta", ["503", "429", "lento", "json-invalido"])
def test_servico_indisponivel_e_transitorio_e_preserva_o_arquivo(cenario_oauth, resposta):
    cenario = cenario_oauth
    cenario.caixa_oauth(2, CAIXA_2, resposta=resposta)
    antes = _autorizacao(cenario).read_bytes()
    assert cenario.executar("executar") == 1
    aviso = cenario.transporte.enviadas[0]
    assert ("caixa 2: serviço de autorização do Google indisponível. Nova tentativa na próxima execução.") in aviso
    assert "autorizar-caixa" not in aviso
    assert _autorizacao(cenario).read_bytes() == antes
    assert cenario.servico.contagem("/token") == 1  # D-09


def test_recuperacao_depois_da_falha_transitoria(cenario_oauth):
    cenario = cenario_oauth
    cenario.caixa_oauth(2, CAIXA_2, resposta="503")
    assert cenario.executar("executar") == 1
    assert cenario.executar("executar") == 1
    assert len(cenario.transporte.enviadas) == 1  # supressão de 6 h do gerenciador existente
    cenario.servico.programar_renovacao("1//duravel-da-caixa-2", "ok", "ya29.temporaria-da-caixa-2")
    assert cenario.executar("executar") == 0
    assert "caixa 2 voltou a funcionar" in cenario.transporte.enviadas[-1]


def test_cliente_recusado_gera_um_aviso_so_e_pula_as_demais_caixas_oauth(cenario_oauth):
    cenario = cenario_oauth
    cenario.caixa_oauth(2, CAIXA_2, resposta="invalid_client")
    cenario.caixa_oauth(3, CAIXA_3)
    cenario.entregar("boleto_simples.eml")
    assert cenario.executar("executar") == 1
    aviso = cenario.transporte.enviadas[0]
    assert aviso.count("credenciais do cliente OAuth recusadas pelo Google. "
                       "Ação: confira OAUTH_CLIENT_ID e OAUTH_CLIENT_SECRET no .env.") == 1
    assert "caixa 3" not in aviso
    assert cenario.servico.contagem("/token") == 1  # a caixa 3 é pulada sem nova requisição
    assert "AUTHENTICATE" not in cenario.servidor.nomes_de_comandos()
    assert len(cenario.arquivos_no_destino()) == 1
    assert "resumo: 1 caixa, 1 extraídos, 1 enviados, 2 falhas, 2 de autorização" in cenario.log()
    assert CLIENT_SECRET not in cenario.log()


def test_authenticate_recusado_pelo_servidor_de_email(cenario_oauth):
    cenario = cenario_oauth
    cenario.caixa_oauth(2, CAIXA_2)
    cenario.servidor.credenciais_oauth[CAIXA_2] = "ya29.outra-que-o-imap-espera"
    assert cenario.executar("executar") == 1
    aviso = cenario.transporte.enviadas[0]
    assert "caixa 2: autorização OAuth recusada pelo servidor de e-mail" in aviso
    assert "confira se o IMAP está ativo na conta" in aviso
    assert "1 de autorização" in cenario.log()
    assert "ya29.temporaria-da-caixa-2" not in cenario.log()


def test_todas_as_caixas_em_falha_de_autorizacao_sai_com_codigo_2(cenario_oauth):
    cenario = cenario_oauth
    for chave in ("EMAIL1", "SENHA_EMAIL1", "EMPRESA_EMAIL1", "IMAP_HOST_EMAIL1"):
        del cenario.env[chave]
    cenario.caixa_oauth(2, CAIXA_2, resposta="invalid_grant")
    assert cenario.executar("executar") == 2


def test_credenciais_do_cliente_ausentes_viram_erro_de_configuracao_da_caixa(cenario_oauth):
    cenario = cenario_oauth
    cenario.caixa_oauth(2, CAIXA_2)
    del cenario.env["OAUTH_CLIENT_SECRET"]
    cenario.entregar("boleto_simples.eml")
    assert cenario.executar("executar") == 1
    assert "caixa 2: credenciais do cliente OAuth ausentes" in cenario.transporte.enviadas[0]
    assert cenario.servico.requisicoes == []
    assert "de autorização" not in cenario.log()  # é falha de configuração, não de autorização
