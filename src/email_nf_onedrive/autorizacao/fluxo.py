"""Fluxo de consentimento do `autorizar-caixa` (feature 002, D-02 a D-04, D-12).

Código de autorização com PKCE (`S256`) e retorno por endereço de laço local, o
fluxo que o Google aceita para aplicativo de computador. O endereço de
consentimento é impresso, nunca aberto: o operador o cola numa janela anônima,
porque o navegador padrão dele está com a conta errada (RN-09). A conta que
consentiu é lida do `id_token` e comparada com `EMAIL<n>`; em divergência, a
autorização recém-emitida é revogada e nada é gravado (RF-06).
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import logging
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qs, urlencode, urlsplit

from email_nf_onedrive import segredos
from email_nf_onedrive.autorizacao import arquivo, servico
from email_nf_onedrive.configuracao.modelo import Caixa, ClienteOAuth

ESCOPOS = (arquivo.ESCOPO_CORREIO, "openid", "email")

PAGINA_DE_RETORNO = (
    "<!doctype html><html lang=\"pt-BR\"><meta charset=\"utf-8\"><title>email-nf-onedrive</title>"
    "<p>Retorno recebido. Você pode fechar esta janela e voltar ao terminal.</p></html>"
).encode("utf-8")

CODIGO = "codigo"
NEGADO = "negado"
STATE_INVALIDO = "state"
TEMPO_ESGOTADO = "tempo"


# --- peças puras ----------------------------------------------------------------------------------

def _b64url(dados: bytes) -> str:
    return base64.urlsafe_b64encode(dados).rstrip(b"=").decode("ascii")


def gerar_pkce() -> tuple[str, str]:
    """(verificador, desafio): o desafio é o SHA-256 do verificador em base64 URL sem preenchimento."""
    verificador = _b64url(secrets.token_bytes(64))
    return verificador, _b64url(hashlib.sha256(verificador.encode("ascii")).digest())


def gerar_state() -> str:
    return _b64url(secrets.token_bytes(32))


def montar_endereco(enderecos: servico.Enderecos, *, client_id: str, redirect_uri: str, login_hint: str,
                    state: str, desafio: str) -> str:
    """Endereço de consentimento. Não contém segredo: só o identificador do cliente, o desafio e o `state`."""
    return enderecos.consentimento + "?" + urlencode({
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(ESCOPOS),
        "access_type": "offline",
        "prompt": "consent",  # garante a emissão de autorização durável também numa reautorização
        "login_hint": login_hint,
        "state": state,
        "code_challenge": desafio,
        "code_challenge_method": "S256",
    })


def ler_id_token(id_token: str | None) -> tuple[str | None, bool]:
    """(email, verificado) do `id_token`. A assinatura não é validada: o token chega direto do serviço por TLS."""
    try:
        segmento = id_token.split(".")[1]
        corpo = json.loads(base64.urlsafe_b64decode(segmento + "=" * (-len(segmento) % 4)))
    except (AttributeError, IndexError, ValueError, binascii.Error):
        return None, False
    if not isinstance(corpo, dict) or not isinstance(corpo.get("email"), str) or not corpo["email"]:
        return None, False
    return corpo["email"], corpo.get("email_verified") in (True, "true")


# --- retorno local --------------------------------------------------------------------------------

@dataclass(frozen=True)
class Retorno:
    tipo: str
    code: str = ""


class RetornoLocal:
    """Servidor em `127.0.0.1`, porta efêmera, que atende o retorno do consentimento e encerra.

    Pedidos a outros caminhos (o `/favicon.ico` do navegador) recebem 404 e não contam como retorno.
    A página devolvida é estática e não reflete nenhum parâmetro recebido.
    """

    def __init__(self) -> None:
        self._consulta: dict[str, str] | None = None
        retorno = self

        class Manipulador(BaseHTTPRequestHandler):
            def log_message(self, *_args) -> None:  # nada do retorno vai ao terminal: a consulta traz o código
                pass

            def do_GET(self) -> None:
                partes = urlsplit(self.path)
                if partes.path != "/":
                    self.send_error(404)
                    return
                retorno._consulta = {k: v[0] for k, v in parse_qs(partes.query).items()}
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(PAGINA_DE_RETORNO)))
                self.end_headers()
                self.wfile.write(PAGINA_DE_RETORNO)

        self._servidor = HTTPServer(("127.0.0.1", 0), Manipulador)  # OSError se a porta não puder ser aberta

    @property
    def redirect_uri(self) -> str:
        return f"http://127.0.0.1:{self._servidor.server_address[1]}"

    def esperar(self, state: str, limite_s: float) -> Retorno:
        prazo = time.monotonic() + limite_s
        while self._consulta is None:
            restante = prazo - time.monotonic()
            if restante <= 0:
                return Retorno(TEMPO_ESGOTADO)
            self._servidor.timeout = restante
            self._servidor.handle_request()
        consulta = self._consulta
        if consulta.get("error"):
            return Retorno(NEGADO)
        if not secrets.compare_digest(consulta.get("state", ""), state) or not consulta.get("code"):
            return Retorno(STATE_INVALIDO)
        return Retorno(CODIGO, consulta["code"])

    def encerrar(self) -> None:
        self._servidor.server_close()


# --- orquestração ---------------------------------------------------------------------------------

@dataclass(frozen=True)
class Desfecho:
    ok: bool
    mensagens: tuple[str, ...]


def _recusa(*mensagens: str) -> Desfecho:
    return Desfecho(False, tuple(mensagens))


def autorizar(caixa: Caixa, cliente: ClienteOAuth, dir_autorizacoes: Path, enderecos: servico.Enderecos, *,
              saida: Callable[[str], None] = print,
              ao_exibir_endereco: Callable[[str], None] | None = None,
              logger: logging.Logger | None = None) -> Desfecho:
    """Conduz o consentimento da caixa. Só grava o arquivo no sucesso; nenhuma recusa deixa resíduo."""
    n = caixa.indice
    try:
        retorno_local = RetornoLocal()
    except OSError as erro:
        return _recusa(f"caixa {n}: não foi possível abrir a porta local de retorno ({type(erro).__name__})")
    try:
        verificador, desafio = gerar_pkce()
        state = gerar_state()
        segredos.registrar(verificador)
        endereco = montar_endereco(enderecos, client_id=cliente.client_id, redirect_uri=retorno_local.redirect_uri,
                                   login_hint=caixa.endereco, state=state, desafio=desafio)
        saida(f"caixa {n}: abra o endereço abaixo numa janela anônima e entre com {caixa.endereco}")
        saida(endereco)
        saida(f"aguardando o consentimento (até {round(enderecos.espera_consentimento_s / 60)} min)...")
        if ao_exibir_endereco is not None:
            ao_exibir_endereco(endereco)
        retorno = retorno_local.esperar(state, enderecos.espera_consentimento_s)
        redirect_uri = retorno_local.redirect_uri
    finally:
        retorno_local.encerrar()

    if retorno.tipo == NEGADO:
        return _recusa(f"caixa {n}: consentimento negado")
    if retorno.tipo == STATE_INVALIDO:
        return _recusa(f"caixa {n}: retorno inválido (state)")
    if retorno.tipo == TEMPO_ESGOTADO:
        return _recusa(f"caixa {n}: tempo esgotado à espera do consentimento")

    try:
        resposta = servico.trocar_codigo(enderecos, cliente, code=retorno.code, code_verifier=verificador,
                                         redirect_uri=redirect_uri, logger=logger)
    except servico.ErroServico as erro:
        if erro.classe == servico.CLIENTE:
            return _recusa("credenciais do cliente OAuth recusadas pelo Google; "
                           "confira OAUTH_CLIENT_ID e OAUTH_CLIENT_SECRET no .env")
        if erro.classe == servico.TRANSITORIA:
            return _recusa(f"caixa {n}: serviço de autorização do Google indisponível; tente de novo")
        return _recusa(f"caixa {n}: troca do código recusada ({erro.erro})")

    refresh_token = resposta.get("refresh_token")
    if not isinstance(refresh_token, str) or not refresh_token:
        return _recusa(f"caixa {n}: o Google não devolveu autorização durável")

    def revogando(*mensagens: str) -> Desfecho:
        if servico.revogar(enderecos, refresh_token, logger):
            return _recusa(*mensagens)
        return _recusa(*mensagens, "não foi possível revogar; revogue em myaccount.google.com/permissions")

    escopos = tuple(str(resposta.get("scope") or "").split())
    if arquivo.ESCOPO_CORREIO not in escopos:  # o titular desmarcou a permissão: a concessão não dá acesso ao correio
        return _recusa(f"caixa {n}: acesso ao correio não concedido")
    email, verificado = ler_id_token(resposta.get("id_token"))
    if email is None or not verificado:  # conta não identificada vale como conta divergente (RF-06)
        return revogando(f"caixa {n}: o Google não informou a conta que consentiu")
    if email.lower() != caixa.endereco.lower():
        return revogando(f"conta autorizada difere de EMAIL{n}")

    destino = arquivo.gravar(dir_autorizacoes, arquivo.Autorizacao(
        endereco=caixa.endereco, client_id=cliente.client_id, refresh_token=refresh_token, escopos=escopos,
        autorizada_em=datetime.now(timezone.utc),
    ))
    return Desfecho(True, (f"caixa {n}: autorizada · {caixa.endereco}", f"arquivo: {destino} (permissão 600)"))
