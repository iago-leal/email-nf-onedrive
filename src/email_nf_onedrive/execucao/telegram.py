"""Transporte de avisos pela API de bots do Telegram (interfaces/telegram-sendmessage.md).

A URL contém o token e nunca é registrada; qualquer texto de erro passa pelo
mascaramento de segredos antes de sair daqui.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Callable

from email_nf_onedrive import segredos

TIMEOUT_S = 15
API = "https://api.telegram.org"


def criar_transporte(token: str, chat_id: str, *, timeout: float = TIMEOUT_S,
                     abrir: Callable = urllib.request.urlopen) -> Callable[[str], tuple[bool, str | None]]:
    segredos.registrar(token)
    url = f"{API}/bot{token}/sendMessage"

    def enviar(texto: str) -> tuple[bool, str | None]:
        corpo = urllib.parse.urlencode(
            {"chat_id": chat_id, "text": texto, "disable_web_page_preview": "true"}
        ).encode()
        requisicao = urllib.request.Request(url, data=corpo, method="POST")
        try:
            with abrir(requisicao, timeout=timeout) as resposta:
                dados = json.loads(resposta.read().decode("utf-8"))
        except urllib.error.HTTPError as erro:
            try:
                descricao = json.loads(erro.read().decode("utf-8")).get("description", "")
            except (ValueError, OSError):
                descricao = ""
            return False, segredos.mascarar(f"HTTP {erro.code} {descricao}".strip())
        except (urllib.error.URLError, OSError, ValueError) as erro:
            return False, segredos.mascarar(f"{type(erro).__name__}: {erro}")
        if not dados.get("ok"):
            return False, segredos.mascarar(str(dados.get("description", "resposta sem ok")))
        return True, None

    return enviar
