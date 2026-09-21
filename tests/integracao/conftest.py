"""Ambiente de ponta a ponta: `cli.main` com IMAP dublê, Rclone real em `:local` e Telegram dublê."""

from __future__ import annotations

import logging
import shutil
import sqlite3

import pytest

from email_nf_onedrive.cli import main
from email_nf_onedrive.coleta.imap import ClienteIMAP
from email_nf_onedrive.execucao.ciclo import Dependencias
from email_nf_onedrive.execucao.logs import NOME_LOGGER

from .dubles import ServidorIMAPFalso, TransporteFalso

CAIXA_1 = "financeiro@empresa.example"
SENHA_1 = "app-senha-caixa-1"
TOKEN = "123456:token-falso-do-bot"


class Cenario:
    def __init__(self, home, destino, dados, escrever_env, relogio) -> None:
        self.home = home
        self.destino = destino
        self.dados = dados
        self.relogio = relogio
        self._escrever_env = escrever_env
        self.servidor = ServidorIMAPFalso()
        self.servidor.adicionar_caixa(CAIXA_1, SENHA_1)
        self.transporte = TransporteFalso()
        self.transportes_criados: list[tuple[str, str]] = []
        self.env = {
            "EMAIL1": CAIXA_1,
            "EMPRESA_EMAIL1": "ACME",
            "SENHA_EMAIL1": SENHA_1,
            "IMAP_HOST_EMAIL1": "imap1.example",
            "RCLONE_REMOTE": ":local",
            "DESTINO_ONEDRIVE": str(destino),
            "DATA_INICIAL": "2026-09-01",
            "TELEGRAM_BOT_TOKEN": TOKEN,
            "TELEGRAM_CHAT_ID": "42",
        }

    def _criar_transporte(self, token, chat_id):
        self.transportes_criados.append((token, chat_id))
        return self.transporte

    def deps(self) -> Dependencias:
        return Dependencias(
            fabrica_imap=lambda c: ClienteIMAP(c.imap_host, c.imap_porta, fabrica=self.servidor.fabrica),
            criar_transporte=self._criar_transporte,
            agora=self.relogio.agora,
        )

    def entregar(self, *nomes: str, caixa: str = CAIXA_1) -> None:
        for nome in nomes:
            self.servidor.entregar(caixa, (self.dados / nome).read_bytes())

    def executar(self, *argumentos: str, deps: Dependencias | None = None) -> int:
        self._escrever_env(self.env)
        return main(["--home", str(self.home), *argumentos], deps=deps or self.deps())

    def log(self) -> str:
        caminho = self.home / "var" / "log" / "email-nf-onedrive.log"
        return caminho.read_text(encoding="utf-8") if caminho.exists() else ""

    def arquivos_no_destino(self) -> list[str]:
        return sorted(p.name for p in self.destino.iterdir())

    def estados(self) -> list[str]:
        with sqlite3.connect(self.home / "var" / "registro.sqlite3") as con:
            return [linha[0] for linha in con.execute("SELECT estado FROM anexos ORDER BY id")]


@pytest.fixture
def cenario(home, dados, escrever_env, relogio):
    if shutil.which("rclone") is None:
        pytest.skip("rclone não instalado")
    destino = home / "onedrive" / "CONTAS A PAGAR"
    destino.mkdir(parents=True)
    yield Cenario(home, destino, dados, escrever_env, relogio)
    for handler in list(logging.getLogger(NOME_LOGGER).handlers):
        logging.getLogger(NOME_LOGGER).removeHandler(handler)
        handler.close()
