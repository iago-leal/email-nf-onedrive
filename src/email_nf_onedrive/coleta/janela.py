"""Janela de busca de mensagens (CE RF-03).

Caixa sem histórico: `DATA_INICIAL`. Com histórico: a menor data entre a
mensagem mais recente registrada menos 2 dias e a mensagem mais antiga com anexo
pendente. A janela nunca recua além de `DATA_INICIAL`; a sobreposição de 2 dias
absorve atrasos e fusos, e a deduplicação elimina o excesso.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

SOBREPOSICAO = timedelta(days=2)
_MESES = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def data_de_corte(data_inicial: date, *, ultima_mensagem: datetime | None,
                  pendente_mais_antiga: datetime | None) -> date:
    if ultima_mensagem is None:
        return data_inicial
    corte = ultima_mensagem.date() - SOBREPOSICAO
    if pendente_mais_antiga is not None:
        corte = min(corte, pendente_mais_antiga.date())
    return max(corte, data_inicial)


def formatar_since(dia: date) -> str:
    """Data no formato do `SEARCH SINCE` do IMAP, sem depender do locale."""
    return f"{dia.day:02d}-{_MESES[dia.month - 1]}-{dia.year}"
