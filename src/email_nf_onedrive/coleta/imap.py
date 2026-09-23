"""Cliente IMAP restrito à leitura (D-05, interfaces/imap-gmail.md).

Só expõe LOGIN ou AUTHENTICATE XOAUTH2 (feature 002, D-07), LIST, EXAMINE,
SEARCH SINCE, FETCH BODY.PEEK[] (e BODY.PEEK[HEADER.FIELDS (MESSAGE-ID)]) e LOGOUT.
A pasta é aberta com `select(readonly=True)`, que emite EXAMINE, e as mensagens são
lidas com BODY.PEEK[], que não altera a flag \\Seen (RN-01).
"""

from __future__ import annotations

import imaplib
import re
from email import message_from_bytes, policy
from datetime import date
from typing import Callable

from email_nf_onedrive import segredos
from email_nf_onedrive.coleta import utf7
from email_nf_onedrive.coleta.janela import formatar_since

TIMEOUT_S = 60

AUTENTICACAO = "autenticacao"
AUTORIZACAO = "autorizacao"  # AUTHENTICATE XOAUTH2 recusado: causa distinta da senha recusada (RF-08)
LIMITE_DESAFIO = 200
PASTA = "pasta"
CONEXAO = "conexao"

IDENTIFICADORES_POR_FETCH = 200
_NUMERO_NO_FETCH = re.compile(rb"^(\d+) ")
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

    def _abrir(self) -> None:
        try:
            self._imap = self._fabrica(self.host, self.porta, timeout=self.timeout)
        except OSError as erro:
            raise ErroIMAP(CONEXAO, f"{type(erro).__name__}: {erro}") from erro

    def conectar(self, usuario: str, senha: str) -> None:
        self._abrir()
        self._chamar(self._imap.login, usuario, senha, causa_no=AUTENTICACAO)

    def conectar_oauth(self, usuario: str, credencial: str) -> None:
        """AUTHENTICATE XOAUTH2 com a credencial temporária; o `imaplib` cuida do base64.

        Na recusa, o servidor devolve um desafio com o erro em JSON e espera uma linha
        vazia antes do NO. O desafio vai ao detalhe do erro, mascarado e truncado.
        """
        self._abrir()
        segredos.registrar(credencial)
        desafios: list[bytes] = []

        def responder(desafio: bytes) -> bytes:
            desafios.append(desafio)
            if len(desafios) == 1:
                return f"user={usuario}\x01auth=Bearer {credencial}\x01\x01".encode()
            return b""

        try:
            self._chamar(self._imap.authenticate, "XOAUTH2", responder, causa_no=AUTORIZACAO)
        except ErroIMAP as erro:
            if erro.causa != AUTORIZACAO:
                raise
            motivo = b" ".join(d for d in desafios[1:] if d).decode(errors="replace")
            detalhe = segredos.mascarar(f"{erro.detalhe} {motivo}".strip())[:LIMITE_DESAFIO]
            raise ErroIMAP(AUTORIZACAO, detalhe) from erro

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

    def identificadores(self, numeros: list[bytes]) -> dict[bytes, str]:
        """`Message-ID` de cada mensagem, em lotes, sem baixar o corpo; vazio se a mensagem não o tiver."""
        achados: dict[bytes, str] = {}
        for inicio in range(0, len(numeros), IDENTIFICADORES_POR_FETCH):
            lote = b",".join(numeros[inicio: inicio + IDENTIFICADORES_POR_FETCH])
            dados = self._chamar(self._imap.fetch, lote, "(BODY.PEEK[HEADER.FIELDS (MESSAGE-ID)])")
            for item in dados or []:
                if isinstance(item, tuple) and len(item) == 2 and (numero := _NUMERO_NO_FETCH.match(item[0])):
                    cabecalho = message_from_bytes(item[1], policy=policy.default)
                    achados[numero.group(1)] = str(cabecalho.get("Message-ID", "")).strip()
        return achados

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
