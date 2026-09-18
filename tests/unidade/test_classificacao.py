"""Testes de UTF-7 modificado e da classificação de anexos (D-05, D-07, CE RF-05, RF-06, EC-07)."""

from __future__ import annotations

import pytest

from email_nf_onedrive.coleta import classificacao, utf7
from email_nf_onedrive.coleta.classificacao import classificar, contem_palavra_chave, eh_nfe_xml

PDF = b"%PDF-1.4\n%%EOF\n"


# --- UTF-7 modificado (RFC 3501, seção 5.1.3) ------------------------------


@pytest.mark.parametrize(
    ("nome", "codificado"),
    [
        ("INBOX", "INBOX"),
        ("[Gmail]/Todos os e-mails", "[Gmail]/Todos os e-mails"),
        ("Notas Fiscais/Março", "Notas Fiscais/Mar&AOc-o"),
        ("Financeiro & Fiscal", "Financeiro &- Fiscal"),
        ("Cobranças/Até hoje", "Cobran&AOc-as/At&AOk- hoje"),
    ],
)
def test_utf7_ida_e_volta(nome, codificado):
    assert utf7.codificar(nome) == codificado
    assert utf7.decodificar(codificado) == nome


# --- NF-e em XML ------------------------------------------------------------


def test_nfe_com_protocolo(dados):
    assert eh_nfe_xml((dados / "nfe_proc.xml").read_bytes())


def test_nfe_sem_protocolo(dados):
    assert eh_nfe_xml((dados / "nfe_sem_protocolo.xml").read_bytes())


def test_xml_malformado_nao_e_nfe(dados):
    assert not eh_nfe_xml((dados / "xml_malformado.xml").read_bytes())


def test_xml_de_outro_namespace_nao_e_nfe():
    assert not eh_nfe_xml(b'<?xml version="1.0"?><NFe xmlns="urn:outro"><x/></NFe>')


def test_pdf_nao_e_nfe():
    assert not eh_nfe_xml(PDF)


def test_xml_acima_do_limite_nao_e_lido(dados, monkeypatch):
    monkeypatch.setattr(classificacao, "LIMITE_XML_BYTES", 100)
    assert not eh_nfe_xml((dados / "nfe_proc.xml").read_bytes())


# --- Palavras-chave -----------------------------------------------------------


@pytest.mark.parametrize(
    "texto",
    [
        "boleto_set.pdf",
        "Cobrança referente a setembro",
        "NF-e_123.pdf",
        "NF123.pdf",
        "nfe 4567",
        "NFSe_2026.pdf",
        "nfs-e.pdf",
        "Nota Fiscal de serviço",
        "nota_fiscal.pdf",
        "DANFE.pdf",
        "Fatura setembro",
        "DUPLICATA 88",
    ],
)
def test_palavra_chave_reconhecida(texto):
    assert contem_palavra_chave(texto)


@pytest.mark.parametrize(
    "texto",
    ["info.pdf", "conforme combinado", "Relatório mensal", "contrato.pdf", "confidencial", ""],
)
def test_palavra_chave_respeita_fronteira(texto):
    assert not contem_palavra_chave(texto)


# --- Classificação -------------------------------------------------------------


def test_nfe_xml_pelo_conteudo_mesmo_com_nome_generico(dados):
    conteudo = (dados / "nfe_proc.xml").read_bytes()
    assert classificar("arquivo.xml", "Documento", conteudo) == "nfe-xml"


def test_palavra_chave_no_nome(dados):
    assert classificar("boleto_set.pdf", "Documento", PDF) == "palavra-chave"


def test_palavra_chave_no_assunto():
    assert classificar("documento.pdf", "Cobrança referente a setembro", PDF) == "palavra-chave"


def test_sem_classificacao():
    assert classificar("contrato.pdf", "Proposta comercial", PDF) == "sem-classificacao"


def test_xml_malformado_cai_nas_regras_de_texto(dados):
    conteudo = (dados / "xml_malformado.xml").read_bytes()
    assert classificar("nota fiscal.xml", "Documento", conteudo) == "palavra-chave"
    assert classificar("dados.xml", "Relatório", conteudo) == "sem-classificacao"


def test_lista_padrao_de_palavras_chave():
    assert set(classificacao.PALAVRAS_CHAVE) == {
        "nf", "nfe", "nf-e", "nfs-e", "nota fiscal", "danfe", "boleto", "fatura", "cobranca", "duplicata",
    }
