"""Testes da nomeação provisória (EO RF-01, RF-02, RF-04, D-12, premissa P-L03)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from email_nf_onedrive.envio.nomeacao import LIMITE_NOME, caminho_destino, com_sufixo, nome_destino, sanear

RECEBIDO = datetime(2026, 9, 18, 15, 0, tzinfo=timezone.utc)


def test_exemplo_da_spec():
    nome = nome_destino(RECEBIDO, "cobranca@fornecedor.com.br", "Boleto Set.pdf")
    assert nome == "2026-09-18_cobranca_Boleto Set.pdf"


def test_data_no_fuso_de_brasilia():
    # 01:30 UTC de 19/09 ainda é 18/09 em Brasília.
    recebido = datetime(2026, 9, 19, 1, 30, tzinfo=timezone.utc)
    assert nome_destino(recebido, "a@b.example", "x.pdf").startswith("2026-09-18_")


def test_caminho_destino_junta_pasta_e_nome():
    caminho = caminho_destino(
        "Financeiro/CONTAS A PAGAR",
        data_mensagem=RECEBIDO,
        remetente="cobranca@fornecedor.com.br",
        nome_original="Boleto Set.pdf",
    )
    assert caminho == "Financeiro/CONTAS A PAGAR/2026-09-18_cobranca_Boleto Set.pdf"


def test_caminho_destino_tolera_barra_final():
    caminho = caminho_destino(
        "Financeiro/CONTAS A PAGAR/",
        data_mensagem=RECEBIDO,
        remetente="a@b.example",
        nome_original="x.pdf",
    )
    assert caminho == "Financeiro/CONTAS A PAGAR/2026-09-18_a_x.pdf"


@pytest.mark.parametrize(
    ("original", "saneado"),
    [
        ("NF: 123?.pdf", "NF 123.pdf"),
        ('a"b*c<d>e|f\\g/h.pdf', "abcdefgh.pdf"),
        ("  boleto.pdf  ", "boleto.pdf"),
        ("boleto.pdf...", "boleto.pdf"),
        ("NF  :  1.pdf", "NF 1.pdf"),
    ],
)
def test_sanear_caracteres_invalidos(original, saneado):
    assert sanear(original) == saneado


@pytest.mark.parametrize(
    ("original", "saneado"),
    [
        ("CON.pdf", "_CON.pdf"),
        ("lpt1.xml", "_lpt1.xml"),
        ("desktop.ini", "_desktop.ini"),
        (".lock", "_.lock"),
        ("arquivo_vti_x.pdf", "arquivo_vti-x.pdf"),
    ],
)
def test_sanear_nomes_reservados(original, saneado):
    assert sanear(original) == saneado


def test_nome_vazio_apos_saneamento():
    assert sanear("???") == "anexo"


def test_truncamento_preserva_extensao():
    nome = sanear("x" * 300 + ".pdf")
    assert len(nome) == LIMITE_NOME == 200
    assert nome.endswith(".pdf")


def test_nome_destino_nunca_passa_do_limite():
    nome = nome_destino(RECEBIDO, "cobranca@fornecedor.example", "y" * 300 + ".pdf")
    assert len(nome) == 200
    assert nome.startswith("2026-09-18_cobranca_")
    assert nome.endswith(".pdf")


def test_remetente_saneado():
    nome = nome_destino(RECEBIDO, 'nf"e*@fornecedor.example', "x.pdf")
    assert nome == "2026-09-18_nfe_x.pdf"


@pytest.mark.parametrize(
    ("nome", "n", "esperado"),
    [
        ("2026-09-18_cobranca_boleto.pdf", 2, "2026-09-18_cobranca_boleto_2.pdf"),
        ("2026-09-18_cobranca_boleto.pdf", 3, "2026-09-18_cobranca_boleto_3.pdf"),
        ("sem_extensao", 2, "sem_extensao_2"),
    ],
)
def test_sufixo_numerico(nome, n, esperado):
    assert com_sufixo(nome, n) == esperado


def test_sufixo_respeita_o_limite():
    nome = "z" * 196 + ".pdf"
    com = com_sufixo(nome, 12)
    assert len(com) == 200
    assert com.endswith("_12.pdf")
