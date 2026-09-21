"""Modelo da configuração lida do .env (spec configuracao-caixas, seção 9)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

PORTA_IMAP = 993

MODO_SENHA = "senha"
MODO_OAUTH = "oauth"
DIR_AUTORIZACOES_PADRAO = "autorizacoes"


class ErroConfiguracao(Exception):
    """Erro global de configuração: a execução é abortada com código 2."""

    def __init__(self, erros: list[str]) -> None:
        super().__init__("; ".join(erros))
        self.erros = erros


@dataclass(frozen=True)
class Caixa:
    indice: int
    endereco: str
    senha: str = field(repr=False)
    pasta: str
    imap_host: str
    destino: str
    imap_porta: int = PORTA_IMAP
    empresa: str = ""  # rótulo no nome dos arquivos; vazio usa o domínio do endereço
    modo: str = MODO_SENHA  # "senha" (LOGIN) ou "oauth" (AUTHENTICATE XOAUTH2); em oauth a senha fica vazia


@dataclass(frozen=True)
class ClienteOAuth:
    """Credenciais do cliente OAuth criado no Google Cloud (feature 002, data-delta §3)."""

    client_id: str
    client_secret: str = field(repr=False)


@dataclass(frozen=True)
class CaixaInvalida:
    indice: int
    motivo: str


@dataclass(frozen=True)
class Configuracao:
    caixas: tuple[Caixa, ...]
    caixas_invalidas: tuple[CaixaInvalida, ...]
    rclone_remote: str
    data_inicial: date
    telegram_bot_token: str | None = field(default=None, repr=False)
    telegram_chat_id: str | None = None
    alertas: tuple[str, ...] = ()
    cliente_oauth: ClienteOAuth | None = None
    dir_autorizacoes: Path = Path(DIR_AUTORIZACOES_PADRAO)

    @property
    def telegram_ativo(self) -> bool:
        return bool(self.telegram_bot_token and self.telegram_chat_id)
