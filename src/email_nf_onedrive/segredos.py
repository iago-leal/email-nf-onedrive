"""Registro de valores sensíveis e mascaramento em textos e logs (D-04).

Toda senha e todo token carregados do .env são registrados aqui. O filtro de log
e a montagem de avisos passam o texto por `mascarar`, de modo que um segredo
ecoado por uma biblioteca nunca chegue ao log nem ao Telegram.
"""

from __future__ import annotations

import logging

MASCARA = "****"

_valores: set[str] = set()


def registrar(valor: str | None) -> None:
    """Passa a mascarar `valor` em toda saída. Valores vazios são ignorados."""
    if valor:
        _valores.add(valor)


def limpar() -> None:
    """Esquece todos os segredos registrados."""
    _valores.clear()


def mascarar(texto: str) -> str:
    """Substitui cada segredo registrado por `****`, do mais longo ao mais curto."""
    for valor in sorted(_valores, key=len, reverse=True):
        texto = texto.replace(valor, MASCARA)
    return texto


class FiltroSegredos(logging.Filter):
    """Filtro de log que mascara segredos na mensagem e no texto de exceção."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = mascarar(record.getMessage())
        record.args = None
        if record.exc_info and not record.exc_text:
            record.exc_text = logging.Formatter().formatException(record.exc_info)
        if record.exc_text:
            record.exc_text = mascarar(record.exc_text)
        return True
