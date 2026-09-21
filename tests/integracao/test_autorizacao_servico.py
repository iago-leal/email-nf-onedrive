"""Cliente do serviço de autorização contra o dublê local (feature 002, D-08, D-09, interfaces/google-oauth.md)."""

from __future__ import annotations

import logging

import pytest

from email_nf_onedrive import segredos
from email_nf_onedrive.autorizacao import servico
from email_nf_onedrive.autorizacao.servico import Enderecos, ErroServico
from email_nf_onedrive.configuracao.modelo import ClienteOAuth

from .conftest import CLIENT_ID, CLIENT_SECRET

pytestmark = pytest.mark.integracao

CLIENTE = ClienteOAuth(CLIENT_ID, CLIENT_SECRET)
DURAVEL = "1//autorizacao-duravel"


@pytest.fixture
def enderecos(servico_oauth) -> Enderecos:
    return Enderecos(consentimento=f"{servico_oauth.base}/auth", token=f"{servico_oauth.base}/token",
                     revogacao=f"{servico_oauth.base}/revoke", tempo_limite_s=0.3)


def test_renovacao_devolve_a_credencial_e_a_registra_como_segredo(servico_oauth, enderecos):
    servico_oauth.programar_renovacao(DURAVEL, "ok", "ya29.temporaria")
    credencial = servico.renovar(enderecos, CLIENTE, DURAVEL)
    assert credencial.access_token == "ya29.temporaria"
    assert credencial.expira_em_s == 3599
    assert "ya29.temporaria" not in repr(credencial)
    assert segredos.mascarar("Bearer ya29.temporaria") == "Bearer ****"
    rota, campos = servico_oauth.requisicoes[0]
    assert rota == "/token"
    assert campos == {"grant_type": "refresh_token", "refresh_token": DURAVEL,
                      "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET}


@pytest.mark.parametrize("resposta, classe", [
    ("invalid_grant", servico.PERMANENTE),
    ("invalid_scope", servico.PERMANENTE),
    ("invalid_client", servico.CLIENTE),
    ("unauthorized_client", servico.CLIENTE),
    ("503", servico.TRANSITORIA),
    ("429", servico.TRANSITORIA),
    ("json-invalido", servico.TRANSITORIA),
    ("sem-access-token", servico.TRANSITORIA),
    ("lento", servico.TRANSITORIA),
])
def test_classificacao_das_falhas_com_tentativa_unica(servico_oauth, enderecos, resposta, classe):
    servico_oauth.programar_renovacao(DURAVEL, resposta, "ya29.nunca-entregue")
    with pytest.raises(ErroServico) as erro:
        servico.renovar(enderecos, CLIENTE, DURAVEL)
    assert erro.value.classe == classe
    assert servico_oauth.contagem("/token") == 1  # D-09: sem repetição dentro da execução


def test_autorizacao_desconhecida_e_invalid_grant(servico_oauth, enderecos):
    with pytest.raises(ErroServico) as erro:
        servico.renovar(enderecos, CLIENTE, "1//nunca-emitida")
    assert (erro.value.classe, erro.value.erro) == (servico.PERMANENTE, "invalid_grant")


def test_servico_inalcancavel_e_transitorio(servico_oauth, enderecos):
    servico_oauth.encerrar()
    with pytest.raises(ErroServico) as erro:
        servico.renovar(enderecos, CLIENTE, DURAVEL)
    assert erro.value.classe == servico.TRANSITORIA


def test_log_traz_o_estado_e_o_erro_sem_nenhum_segredo(servico_oauth, enderecos, caplog):
    servico_oauth.programar_renovacao(DURAVEL, "invalid_grant")
    with caplog.at_level(logging.INFO), pytest.raises(ErroServico):
        servico.renovar(enderecos, CLIENTE, DURAVEL, logger=logging.getLogger("teste-servico"))
    assert "400" in caplog.text and "invalid_grant" in caplog.text
    for segredo in (CLIENT_SECRET, DURAVEL):
        assert segredo not in caplog.text


def test_troca_do_codigo_envia_o_verificador_e_o_retorno(servico_oauth, enderecos):
    servico_oauth.programar_troca("codigo-1", email="a@empresa.example", refresh_token="1//nova")
    resposta = servico.trocar_codigo(enderecos, CLIENTE, code="codigo-1", code_verifier="verificador",
                                     redirect_uri="http://127.0.0.1:50123")
    assert resposta["refresh_token"] == "1//nova"
    assert servico_oauth.requisicoes[0][1] == {
        "grant_type": "authorization_code", "code": "codigo-1", "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET, "redirect_uri": "http://127.0.0.1:50123", "code_verifier": "verificador",
    }
    assert segredos.mascarar("1//nova ya29.troca") == "**** ****"


def test_troca_recusada_levanta_o_erro_classificado(servico_oauth, enderecos):
    with pytest.raises(ErroServico) as erro:
        servico.trocar_codigo(enderecos, CLIENTE, code="codigo-usado", code_verifier="v", redirect_uri="http://127.0.0.1:1")
    assert erro.value.erro == "invalid_grant"


def test_revogacao_devolve_o_desfecho_sem_excecao(servico_oauth, enderecos):
    assert servico.revogar(enderecos, "1//a-revogar") is True
    assert servico_oauth.revogados == ["1//a-revogar"]
    servico_oauth.revogacao_disponivel = False
    assert servico.revogar(enderecos, "1//outra") is False
    servico_oauth.encerrar()
    assert servico.revogar(enderecos, "1//outra") is False
