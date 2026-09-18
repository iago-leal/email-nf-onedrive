"""Cliente IMAP restrito à leitura (D-05, interfaces/imap-gmail.md).

Só expõe LOGIN, LIST, EXAMINE, SEARCH SINCE, FETCH BODY.PEEK[] e LOGOUT. A pasta
é aberta com `select(readonly=True)`, que emite EXAMINE, e as mensagens são
lidas com BODY.PEEK[], que não altera a flag \\Seen (RN-01).
"""

from __future__ import annotations

import imaplib
import re
from datetime import date
from typing import Callable

from email_nf_onedrive.coleta import utf7
from email_nf_onedrive.coleta.janela import formatar_since

TIMEOUT_S = 60

AUTENTICACAO = "autenticacao"
PASTA = "pasta"
CONEXAO = "conexao"

_NOME_NA_LISTA = re.compile(rb'(?:"((?:[^"\\]|\\.)*)"|(\S+))\s*$')


class ErroIMAP(Exception):
    """Falha de uma caixa, com a causa usada na chave dos avisos."""

    def __init__(self, causa: str, detalhe: str) -> None:
        super().__init__(detalhe)
        self.causa = causa
        self.detalhe = detalhe


def _citar(nome: str) -> str:
    codificado = utf7.codificar(nome).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{codificado}"'


def _texto(dados) -> str:
    partes = [d.decode(errors="replace") if isinstance(d, bytes) else str(d) for d in (dados or [])]
    return " ".join(partes)


class ClienteIMAP:
    def __init__(self, host: str, porta: int, *, timeout: float = TIMEOUT_S,
                 fabrica: Callable[..., imaplib.IMAP4] = imaplib.IMAP4_SSL) -> None:
        self.host = host
        self.porta = porta
        self.timeout = timeout
        self._fabrica = fabrica
        self._imap: imaplib.IMAP4 | None = None

    def _chamar(self, operacao: Callable, *args, causa_no: str = CONEXAO):
        try:
            tipo, dados = operacao(*args)
        except imaplib.IMAP4.abort as erro:
            raise ErroIMAP(CONEXAO, f"conexão interrompida: {erro}") from erro
        except imaplib.IMAP4.error as erro:
            raise ErroIMAP(causa_no, str(erro)) from erro
        except OSError as erro:
            raise ErroIMAP(CONEXAO, f"{type(erro).__name__}: {erro}") from erro
        if tipo != "OK":
            raise ErroIMAP(causa_no, _texto(dados))
        return dados

    def conectar(self, usuario: str, senha: str) -> None:
        try:
            self._imap = self._fabrica(self.host, self.porta, timeout=self.timeout)
        except OSError as erro:
            raise ErroIMAP(CONEXAO, f"{type(erro).__name__}: {erro}") from erro
        self._chamar(self._imap.login, usuario, senha, causa_no=AUTENTICACAO)

    def listar_pastas(self) -> list[str]:
        pastas = []
        for linha in self._chamar(self._imap.list) or []:
            if not isinstance(linha, bytes) or not (m := _NOME_NA_LISTA.search(linha)):
                continue
            bruto = (m.group(1) or m.group(2)).decode("ascii", errors="replace").replace('\\"', '"')
            pastas.append(utf7.decodificar(bruto))
        return pastas

    def examinar(self, pasta: str) -> None:
        """Abre a pasta em somente leitura (EXAMINE)."""
        self._chamar(self._imap.select, _citar(pasta), True, causa_no=PASTA)

    def buscar_desde(self, dia: date) -> list[bytes]:
        dados = self._chamar(self._imap.search, None, "SINCE", formatar_since(dia))
        return (dados[0] or b"").split() if dados else []

    def obter(self, numero: bytes) -> bytes:
        """Mensagem completa, sem marcar como lida (BODY.PEEK[])."""
        dados = self._chamar(self._imap.fetch, numero, "(BODY.PEEK[])")
        for item in dados:
            if isinstance(item, tuple) and len(item) == 2:
                return item[1]
        raise ErroIMAP(CONEXAO, f"resposta de FETCH sem corpo para a mensagem {numero!r}")

    def encerrar(self) -> None:
        if self._imap is None:
            return
        try:
            self._imap.logout()
        except (imaplib.IMAP4.error, OSError):
            pass
        self._imap = None

    def __enter__(self) -> "ClienteIMAP":
        return self

    def __exit__(self, *_exc) -> None:
        self.encerrar()
