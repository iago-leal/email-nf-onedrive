"""Peças puras do fluxo de consentimento (feature 002, D-02, D-04, interfaces/google-oauth.md §1)."""

from __future__ import annotations

import base64
import hashlib
import json
import re
from urllib.parse import parse_qs, urlsplit

import pytest

from email_nf_onedrive.autorizacao import fluxo
from email_nf_onedrive.autorizacao.servico import Enderecos

B64URL = re.compile(r"^[A-Za-z0-9_-]+$")


def _jwt(corpo, preenchimento=False) -> str:
    segmento = base64.urlsafe_b64encode(json.dumps(corpo).encode()).decode()
    return "cabecalho." + (segmento if preenchimento else segmento.rstrip("=")) + ".assinatura"


def test_pkce_s256_em_base64_url_sem_preenchimento():
    verificador, desafio = fluxo.gerar_pkce()
    assert 43 <= len(verificador) <= 128 and B64URL.match(verificador)
    esperado = base64.urlsafe_b64encode(hashlib.sha256(verificador.encode("ascii")).digest()).rstrip(b"=").decode()
    assert desafio == esperado
    assert B64URL.match(desafio)


def test_pkce_e_state_nao_se_repetem():
    assert fluxo.gerar_pkce()[0] != fluxo.gerar_pkce()[0]
    assert fluxo.gerar_state() != fluxo.gerar_state()


def test_state_tem_32_bytes_em_base64_url():
    state = fluxo.gerar_state()
    assert B64URL.match(state)
    assert len(base64.urlsafe_b64decode(state + "=" * (-len(state) % 4))) == 32


def test_endereco_de_consentimento_traz_todos_os_parametros():
    endereco = fluxo.montar_endereco(Enderecos(), client_id="id-do-cliente", redirect_uri="http://127.0.0.1:50123",
                                     login_hint="financeiro@empresa.example", state="estado", desafio="desafio")
    partes = urlsplit(endereco)
    assert f"{partes.scheme}://{partes.netloc}{partes.path}" == "https://accounts.google.com/o/oauth2/v2/auth"
    assert {k: v[0] for k, v in parse_qs(partes.query).items()} == {
        "client_id": "id-do-cliente",
        "redirect_uri": "http://127.0.0.1:50123",
        "response_type": "code",
        "scope": "https://mail.google.com/ openid email",
        "access_type": "offline",
        "prompt": "consent",
        "login_hint": "financeiro@empresa.example",
        "state": "estado",
        "code_challenge": "desafio",
        "code_challenge_method": "S256",
    }


def test_enderecos_padrao_sao_os_do_google():
    padrao = Enderecos()
    assert padrao.token == "https://oauth2.googleapis.com/token"
    assert padrao.revogacao == "https://oauth2.googleapis.com/revoke"
    assert (padrao.tempo_limite_s, padrao.espera_consentimento_s) == (60, 300)


@pytest.mark.parametrize("preenchimento", [False, True])
def test_id_token_lido_sem_validar_a_assinatura(preenchimento):
    token = _jwt({"email": "Financeiro@Empresa.example", "email_verified": True}, preenchimento)
    assert fluxo.ler_id_token(token) == ("Financeiro@Empresa.example", True)


def test_id_token_com_email_nao_verificado():
    assert fluxo.ler_id_token(_jwt({"email": "a@b.example", "email_verified": False})) == ("a@b.example", False)
    assert fluxo.ler_id_token(_jwt({"email": "a@b.example"})) == ("a@b.example", False)
    assert fluxo.ler_id_token(_jwt({"email": "a@b.example", "email_verified": "true"})) == ("a@b.example", True)


@pytest.mark.parametrize("token", [None, "", "um-segmento-so", "a.###.c", "a." + "e30" + ".c", _jwt([1, 2]), _jwt({"email": 7})])
def test_id_token_malformado_ou_sem_email(token):
    assert fluxo.ler_id_token(token) == (None, False)
