"""Testes da janela de busca (CE RF-03, data-delta.md §2)."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from email_nf_onedrive.coleta.janela import data_de_corte, formatar_since

INICIAL = date(2026, 9, 1)


def _dt(dia: int, mes: int = 9) -> datetime:
    return datetime(2026, mes, dia, 10, 0, tzinfo=timezone.utc)


def test_caixa_sem_historico_usa_data_inicial():
    assert data_de_corte(INICIAL, ultima_mensagem=None, pendente_mais_antiga=None) == INICIAL


def test_caixa_com_historico_recua_dois_dias():
    assert data_de_corte(INICIAL, ultima_mensagem=_dt(10), pendente_mais_antiga=None) == date(2026, 9, 8)


def test_pendente_mais_antigo_recua_a_janela():
    corte = data_de_corte(INICIAL, ultima_mensagem=_dt(10), pendente_mais_antiga=_dt(3))
    assert corte == date(2026, 9, 3)


def test_pendente_recente_nao_altera_a_janela():
    corte = data_de_corte(INICIAL, ultima_mensagem=_dt(10), pendente_mais_antiga=_dt(9))
    assert corte == date(2026, 9, 8)


def test_janela_nunca_antecede_a_data_inicial():
    assert data_de_corte(INICIAL, ultima_mensagem=_dt(2), pendente_mais_antiga=None) == INICIAL


@pytest.mark.parametrize(
    ("dia", "esperado"),
    [
        (date(2026, 9, 8), "08-Sep-2026"),
        (date(2026, 2, 1), "01-Feb-2026"),
        (date(2026, 12, 31), "31-Dec-2026"),
    ],
)
def test_formato_since_independe_do_locale(dia, esperado):
    assert formatar_since(dia) == esperado
