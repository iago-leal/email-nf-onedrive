"""Cliente do serviço de autorização do Google (feature 002, interfaces/google-oauth.md).

Três operações, todas `POST` de formulário com a biblioteca padrão (D-01): troca
do código, renovação e revogação. Uma tentativa por chamada, com tempo limite de
60 s (D-09). Os endereços são constantes do código e só mudam por injeção de
`Enderecos` nos testes, nunca pelo `.env` (D-14): uma variável que redirecionasse
o envio do segredo do cliente seria um vetor de vazamento.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

from email_nf_onedrive import segredos
from email_nf_onedrive.configuracao.modelo import ClienteOAuth

PERMANENTE = "permanente"    # revogada, caducada, senha trocada: refazer a autorização
CLIENTE = "cliente"          # OAUTH_CLIENT_ID ou OAUTH_CLIENT_SECRET recusados: corrigir o .env
TRANSITORIA = "transitoria"  # serviço fora do ar ou resposta inaproveitável: a próxima execução repete

_ERROS_DO_CLIENTE = ("invalid_client", "unauthorized_client")
_SEGREDOS_DA_RESPOSTA = ("access_token", "refresh_token", "id_token")


@dataclass(frozen=True)
class Enderecos:
    consentimento: str = "https://accounts.google.com/o/oauth2/v2/auth"
    token: str = "https://oauth2.googleapis.com/token"
    revogacao: str = "https://oauth2.googleapis.com/revoke"
    tempo_limite_s: float = 60
    espera_consentimento_s: float = 300


@dataclass(frozen=True)
class CredencialTemporaria:
    access_token: str = field(repr=False)
    expira_em_s: int = 0


class ErroServico(Exception):
    def __init__(self, classe: str, erro: str) -> None:
        super().__init__(erro)
        self.classe = classe
        self.erro = erro


def _json(bruto: bytes) -> dict | None:
    try:
        dados = json.loads(bruto.decode("utf-8", errors="replace"))
    except ValueError:
        return None
    return dados if isinstance(dados, dict) else None


def _postar(endereco: str, campos: dict[str, str], tempo_limite_s: float, logger: logging.Logger | None,
            operacao: str) -> dict:
    """Devolve o JSON de uma resposta 200; qualquer outro desfecho vira `ErroServico` classificado."""
    requisicao = urllib.request.Request(
        endereco, data=urllib.parse.urlencode(campos).encode("ascii"), method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(requisicao, timeout=tempo_limite_s) as resposta:
            dados = _json(resposta.read())
    except urllib.error.HTTPError as erro:
        corpo = _json(erro.read()) or {}
        nome = str(corpo.get("error") or f"http-{erro.code}")
        if logger is not None:  # só o estado e o campo `error`; a descrição passa pelo mascaramento
            descricao = segredos.mascarar(str(corpo.get("error_description", "")))[:200]
            logger.warning("serviço de autorização: %s respondeu %d %s %s", operacao, erro.code, nome, descricao)
        if erro.code == 429 or erro.code >= 500:
            raise ErroServico(TRANSITORIA, nome) from erro
        raise ErroServico(CLIENTE if nome in _ERROS_DO_CLIENTE else PERMANENTE, nome) from erro
    except (OSError, ValueError) as erro:  # sem resposta em 60 s, DNS, TLS, conexão recusada
        if logger is not None:
            logger.warning("serviço de autorização: %s sem resposta (%s)", operacao, type(erro).__name__)
        raise ErroServico(TRANSITORIA, type(erro).__name__) from erro
    if dados is None:
        if logger is not None:
            logger.warning("serviço de autorização: %s devolveu resposta que não é JSON", operacao)
        raise ErroServico(TRANSITORIA, "resposta-invalida")
    for chave in _SEGREDOS_DA_RESPOSTA:
        if isinstance(dados.get(chave), str):
            segredos.registrar(dados[chave])
    return dados


def renovar(enderecos: Enderecos, cliente: ClienteOAuth, refresh_token: str,
            logger: logging.Logger | None = None) -> CredencialTemporaria:
    """Troca a autorização durável por uma credencial temporária, que vive só em memória (D-06)."""
    dados = _postar(enderecos.token, {
        "grant_type": "refresh_token", "refresh_token": refresh_token,
        "client_id": cliente.client_id, "client_secret": cliente.client_secret,
    }, enderecos.tempo_limite_s, logger, "renovação")
    access_token = dados.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        if logger is not None:
            logger.warning("serviço de autorização: renovação sem credencial na resposta")
        raise ErroServico(TRANSITORIA, "resposta-invalida")
    try:
        expira_em_s = int(dados.get("expires_in") or 0)
    except (TypeError, ValueError):
        expira_em_s = 0
    return CredencialTemporaria(access_token, expira_em_s)


def trocar_codigo(enderecos: Enderecos, cliente: ClienteOAuth, *, code: str, code_verifier: str, redirect_uri: str,
                  logger: logging.Logger | None = None) -> dict:
    """Troca o código de autorização pela resposta completa; o código vale uma vez e não é repetido."""
    for segredo in (code, code_verifier):
        segredos.registrar(segredo)
    return _postar(enderecos.token, {
        "grant_type": "authorization_code", "code": code,
        "client_id": cliente.client_id, "client_secret": cliente.client_secret,
        "redirect_uri": redirect_uri, "code_verifier": code_verifier,
    }, enderecos.tempo_limite_s, logger, "troca do código")


def revogar(enderecos: Enderecos, token: str, logger: logging.Logger | None = None) -> bool:
    """Falha na revogação não levanta exceção: o chamador só acrescenta a orientação de revogar à mão."""
    try:
        _postar(enderecos.revogacao, {"token": token}, enderecos.tempo_limite_s, logger, "revogação")
    except ErroServico:
        return False
    return True
