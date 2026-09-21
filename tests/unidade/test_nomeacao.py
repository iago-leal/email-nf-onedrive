"""Testes da convenção de nomes da pasta CONTAS A PAGAR (EO RF-01, RF-02, RF-04, D-12, L-03)."""

from __future__ import annotations

from pathlib import Path

import pytest

from email_nf_onedrive.envio.nomeacao import (
    LIMITE_NOME, DadosNome, caminho_destino, com_sufixo, dados_nfe, nome_destino, rotulo_do_endereco, sanear,
)

DADOS = Path(__file__).resolve().parents[1] / "dados"


def _dados(**campos) -> DadosNome:
    base = dict(empresa="ACME", remetente="cobranca@fornecedor.com.br", nome_original="Boleto Set.pdf",
                assunto="Boleto", classe="palavra-chave")
    return DadosNome(**{**base, **campos})


def test_exemplo_da_spec_boleto():
    assert nome_destino(_dados()) == "ACME - FORNECEDOR - BOLETO.pdf"


def test_nota_em_pdf_com_numero_no_nome():
    dados = _dados(nome_original="NF 109652 Fornecedor.PDF", assunto="Sua nota fiscal", remetente="nfe@fornecedor.com.br")
    assert nome_destino(dados) == "ACME - FORNECEDOR NF 109652 - REF.pdf"


@pytest.mark.parametrize(
    ("nome", "assunto", "numero"),
    [
        ("NFS-e 202600.pdf", "", "202600"),
        ("danfe_000000123.pdf", "", "123"),
        ("documento.pdf", "NF-e nº 789 emitida", "789"),
        ("nota fiscal n. 55.pdf", "", "55"),
        ("documento.pdf", "Fatura de setembro", ""),
    ],
)
def test_numero_da_nota_no_nome_ou_no_assunto(nome, assunto, numero):
    nome_final = nome_destino(_dados(nome_original=nome, assunto=assunto))
    esperado = f" NF {numero} - " if numero else " - "
    assert esperado in nome_final


def test_boleto_reconhecido_pelo_assunto():
    dados = _dados(nome_original="documento.pdf", assunto="Segue boleto da NF 12")
    assert nome_destino(dados) == "ACME - FORNECEDOR NF 12 - BOLETO.pdf"


def test_nfe_xml_usa_emitente_e_numero_do_xml():
    conteudo = (DADOS / "nfe_proc.xml").read_bytes()
    dados = _dados(nome_original="arquivo.xml", assunto="", classe="nfe-xml", conteudo=conteudo)
    assert nome_destino(dados) == "ACME - FORNECEDOR FICTICIO LTDA - REF.xml"


def test_nfe_xml_com_numero():
    conteudo = (
        b'<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe"><NFe><infNFe>'
        b"<ide><nNF>000123</nNF></ide><emit><xNome>Fornecedor &amp; Cia</xNome></emit>"
        b"</infNFe></NFe></nfeProc>"
    )
    assert dados_nfe(conteudo) == ("Fornecedor & Cia", "000123")
    dados = _dados(nome_original="nfe.XML", classe="nfe-xml", conteudo=conteudo)
    assert nome_destino(dados) == "ACME - FORNECEDOR & CIA NF 123 - REF.xml"


def test_xml_truncado_recorre_ao_remetente():
    dados = _dados(nome_original="nfe.xml", classe="nfe-xml", conteudo=b"<nfeProc><NFe>")
    assert nome_destino(dados) == "ACME - FORNECEDOR - REF.xml"


def test_empresa_vazia_usa_dominio_do_remetente():
    assert nome_destino(_dados(empresa="")) == "FORNECEDOR - FORNECEDOR - BOLETO.pdf"


@pytest.mark.parametrize(
    ("endereco", "rotulo"),
    [
        ("cobranca@fornecedor.com.br", "FORNECEDOR"),
        ("fulano.silva@empresa-a.example", "EMPRESA A"),
        ("empresaadm@gmail.com", "EMPRESAADM"),
        ("joao.silva@outlook.com", "JOAO SILVA"),
        ("x@açaí-mineração.com.br", "ACAI MINERACAO"),
        ("sem-arroba", "SEM ARROBA"),
        ("", "REMETENTE"),
    ],
)
def test_rotulo_do_endereco(endereco, rotulo):
    assert rotulo_do_endereco(endereco) == rotulo


def test_caminho_destino_junta_pasta_e_nome():
    caminho = caminho_destino("ACME Financeiro/CONTAS A PAGAR", _dados())
    assert caminho == "ACME Financeiro/CONTAS A PAGAR/ACME - FORNECEDOR - BOLETO.pdf"


def test_caminho_destino_tolera_barra_final():
    caminho = caminho_destino("ACME Financeiro/CONTAS A PAGAR/", _dados())
    assert caminho == "ACME Financeiro/CONTAS A PAGAR/ACME - FORNECEDOR - BOLETO.pdf"


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
    nome = nome_destino(_dados(empresa="E" * 300))
    assert len(nome) == 200
    assert nome.startswith("EEEE")
    assert nome.endswith(".pdf")


def test_caracteres_invalidos_no_remetente_e_na_empresa():
    dados = _dados(empresa='AC*ME', remetente='nf"e*@forne<cedor>.example')
    assert nome_destino(dados) == "ACME - FORNECEDOR - BOLETO.pdf"


def test_anexo_sem_extensao():
    assert nome_destino(_dados(nome_original="boleto")) == "ACME - FORNECEDOR - BOLETO"


@pytest.mark.parametrize(
    ("nome", "n", "esperado"),
    [
        ("ACME - FORNECEDOR - BOLETO.pdf", 2, "ACME - FORNECEDOR - BOLETO_2.pdf"),
        ("ACME - FORNECEDOR - BOLETO.pdf", 3, "ACME - FORNECEDOR - BOLETO_3.pdf"),
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
