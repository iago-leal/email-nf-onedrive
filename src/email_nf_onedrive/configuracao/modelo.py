"""Modelo da configuração lida do .env (spec configuracao-caixas, seção 9)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

PORTA_IMAP = 993


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

    @property
    def telegram_ativo(self) -> bool:
        return bool(self.telegram_bot_token and self.telegram_chat_id)
