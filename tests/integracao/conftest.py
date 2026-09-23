"""Ambiente de ponta a ponta: `cli.main` com IMAP dublê, Rclone real em `:local` e Telegram dublê."""

from __future__ import annotations

import json
import logging
import os
import shutil
import sqlite3

import pytest

from email_nf_onedrive.cli import main
from email_nf_onedrive.coleta.imap import ClienteIMAP
from email_nf_onedrive.envio.rclone import NOME_LEIAME
from email_nf_onedrive.execucao.ciclo import Dependencias
from email_nf_onedrive.execucao.logs import NOME_LOGGER

from .dubles import ServicoAutorizacaoFalso, ServidorIMAPFalso, TransporteFalso

CAIXA_1 = "financeiro@empresa.example"
SENHA_1 = "app-senha-caixa-1"
TOKEN = "123456:token-falso-do-bot"
CLIENT_ID = "1234567890-abc.apps.googleusercontent.com"
CLIENT_SECRET = "GOCSPX-segredo-do-cliente-falso"
ESCOPO_CORREIO = "https://mail.google.com/"


def gravar_autorizacao(diretorio, endereco: str, refresh_token: str, client_id: str = CLIENT_ID, *,
                       modo_arquivo: int = 0o600, modo_diretorio: int = 0o700, **campos):
    """Grava um arquivo de autorização como o `autorizar-caixa` o deixa (data-delta.md §4)."""
    diretorio.mkdir(parents=True, exist_ok=True)
    os.chmod(diretorio, modo_diretorio)
    caminho = diretorio / f"{endereco.lower()}.json"
    conteudo = {"versao": 1, "endereco": endereco, "client_id": client_id, "refresh_token": refresh_token,
                "escopos": [ESCOPO_CORREIO, "openid", "email"], "autorizada_em": "2026-09-21T18:40:11+00:00"}
    conteudo.update(campos)
    caminho.write_text(json.dumps(conteudo), encoding="utf-8")
    os.chmod(caminho, modo_arquivo)
    return caminho


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
        self.servico: ServicoAutorizacaoFalso | None = None  # preenchido pela fixture `cenario_oauth`
        self.navegador = None  # chamado com o endereço de consentimento impresso pelo `autorizar-caixa`
        self.espera_consentimento_s = 5.0
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
        extras = {}
        if self.servico is not None:
            from email_nf_onedrive.autorizacao.servico import Enderecos
            extras["servico_autorizacao"] = Enderecos(
                consentimento=f"{self.servico.base}/auth", token=f"{self.servico.base}/token",
                revogacao=f"{self.servico.base}/revoke", tempo_limite_s=0.4,
                espera_consentimento_s=self.espera_consentimento_s)
            extras["ao_exibir_endereco"] = lambda endereco: self.navegador and self.navegador(endereco)
        return Dependencias(
            fabrica_imap=lambda c: ClienteIMAP(c.imap_host, c.imap_porta, fabrica=self.servidor.fabrica),
            criar_transporte=self._criar_transporte,
            agora=self.relogio.agora,
            **extras,
        )

    @property
    def dir_autorizacoes(self):
        return self.home / "autorizacoes"

    def caixa_oauth(self, n: int, endereco: str, *, refresh_token: str | None = None, access_token: str | None = None,
                    resposta: str = "ok", autorizada: bool = True) -> None:
        """Acrescenta a caixa `n` em modo oauth: `.env`, IMAP dublê, renovação programada e arquivo."""
        refresh_token = refresh_token or f"1//duravel-da-caixa-{n}"
        access_token = access_token or f"ya29.temporaria-da-caixa-{n}"
        self.env.update({f"EMAIL{n}": endereco, f"AUTH_EMAIL{n}": "oauth", f"IMAP_HOST_EMAIL{n}": f"imap{n}.example",
                         "OAUTH_CLIENT_ID": CLIENT_ID, "OAUTH_CLIENT_SECRET": CLIENT_SECRET})
        self.servidor.adicionar_caixa_oauth(endereco, access_token)
        self.servico.programar_renovacao(refresh_token, resposta, access_token)
        if autorizada:
            gravar_autorizacao(self.dir_autorizacoes, endereco, refresh_token)

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
        """Documentos no destino, sem o sumário LEIAME, coberto à parte em `test_leiame`."""
        return sorted(p.name for p in self.destino.iterdir() if p.name != NOME_LEIAME)

    def estados(self) -> list[str]:
        with sqlite3.connect(self.home / "var" / "registro.sqlite3") as con:
            return [linha[0] for linha in con.execute("SELECT estado FROM anexos ORDER BY id")]


@pytest.fixture
def servico_oauth():
    servico = ServicoAutorizacaoFalso()
    yield servico
    servico.encerrar()


@pytest.fixture
def cenario_oauth(cenario, servico_oauth):
    """O `cenario` com o serviço de autorização dublê injetado; a caixa 1 segue em modo senha."""
    cenario.servico = servico_oauth
    return cenario


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
