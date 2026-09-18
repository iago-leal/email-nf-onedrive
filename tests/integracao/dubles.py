"""Dublês de teste: servidor IMAP em memória e transporte de avisos."""

from __future__ import annotations

import imaplib
from datetime import date
from email.utils import parsedate_to_datetime

from email_nf_onedrive.coleta import utf7

_MESES = {m: i for i, m in enumerate(
    ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"), start=1)}


def _data_da_mensagem(bruto: bytes) -> date | None:
    for linha in bruto.split(b"\r\n\r\n", 1)[0].replace(b"\r\n", b"\n").split(b"\n"):
        if linha.lower().startswith(b"date:"):
            return parsedate_to_datetime(linha[5:].decode().strip()).date()
    return None


class ServidorIMAPFalso:
    """Caixas em memória, com registro de todos os comandos recebidos.

    `caixas` mapeia endereço -> (senha, {pasta: [mensagens brutas]}).
    `fora_do_ar` faz a conexão falhar com timeout.
    """

    def __init__(self) -> None:
        self.caixas: dict[str, tuple[str, dict[str, list[bytes]]]] = {}
        self.comandos: list[tuple] = []
        self.fora_do_ar: set[str] = set()
        self.lidas: set[tuple[str, int]] = set()

    def adicionar_caixa(self, endereco: str, senha: str, pastas: dict[str, list[bytes]] | None = None) -> None:
        self.caixas[endereco] = (senha, pastas or {"INBOX": []})

    def entregar(self, endereco: str, bruto: bytes, pasta: str = "INBOX") -> None:
        self.caixas[endereco][1].setdefault(pasta, []).append(bruto)

    def fabrica(self, host: str, porta: int, timeout: float | None = None) -> "ConexaoFalsa":
        self.comandos.append(("CONNECT", host, porta, timeout))
        if host in self.fora_do_ar:
            raise TimeoutError("timed out")
        return ConexaoFalsa(self)

    def nomes_de_comandos(self) -> set[str]:
        return {c[0] for c in self.comandos}


class ConexaoFalsa:
    def __init__(self, servidor: ServidorIMAPFalso) -> None:
        self.servidor = servidor
        self.usuario: str | None = None
        self.pasta: list[bytes] | None = None

    def _registrar(self, *comando) -> None:
        self.servidor.comandos.append(comando)

    def login(self, usuario: str, senha: str):
        self._registrar("LOGIN", usuario)
        caixa = self.servidor.caixas.get(usuario)
        if caixa is None or caixa[0] != senha:
            raise imaplib.IMAP4.error("[AUTHENTICATIONFAILED] Invalid credentials (Failure)")
        self.usuario = usuario
        return "OK", [b"LOGIN completed"]

    def list(self):
        self._registrar("LIST")
        pastas = self.servidor.caixas[self.usuario][1]
        return "OK", [f'(\\HasNoChildren) "/" "{utf7.codificar(p)}"'.encode() for p in pastas]

    def select(self, mailbox: str, readonly: bool = False):
        self._registrar("EXAMINE" if readonly else "SELECT", mailbox)
        nome = utf7.decodificar(mailbox.strip('"'))
        pastas = self.servidor.caixas[self.usuario][1]
        if nome not in pastas:
            return "NO", [b"[NONEXISTENT] Unknown Mailbox"]
        self.pasta = pastas[nome]
        return "OK", [str(len(self.pasta)).encode()]

    def search(self, charset, *criterios):
        self._registrar("SEARCH", *criterios)
        assert criterios[0] == "SINCE"
        dia, mes, ano = criterios[1].split("-")
        desde = date(int(ano), _MESES[mes], int(dia))
        numeros = [
            str(i).encode() for i, bruto in enumerate(self.pasta, start=1)
            if (_data_da_mensagem(bruto) or desde) >= desde
        ]
        return "OK", [b" ".join(numeros)]

    def fetch(self, numero: bytes, partes: str):
        self._registrar("FETCH", numero, partes)
        bruto = self.pasta[int(numero) - 1]
        if "PEEK" not in partes:
            self.servidor.lidas.add((self.usuario, int(numero)))
        return "OK", [(numero + b" (BODY[] {%d}" % len(bruto), bruto), b")"]

    def logout(self):
        self._registrar("LOGOUT")
        return "BYE", [b"LOGOUT"]

    def __getattr__(self, nome: str):
        # Qualquer comando fora da lista (store, copy, expunge...) é registrado e falha.
        def proibido(*args):
            self._registrar(nome.upper(), *args)
            raise AssertionError(f"comando IMAP proibido: {nome}")
        return proibido


class TransporteFalso:
    """Substitui o Telegram: guarda as mensagens e pode simular indisponibilidade."""

    def __init__(self) -> None:
        self.enviadas: list[str] = []
        self.disponivel = True

    def __call__(self, texto: str) -> tuple[bool, str | None]:
        if not self.disponivel:
            return False, "timeout"
        self.enviadas.append(texto)
        return True, None
