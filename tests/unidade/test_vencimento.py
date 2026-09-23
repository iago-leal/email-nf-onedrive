"""Testes do vencimento e da subpasta por vencimento (feature 003, cartão 2)."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from email_nf_onedrive.envio.vencimento import (
    MOTIVO_A_VISTA, MOTIVO_DANFE, MOTIVO_FORMATO, MOTIVO_ILEGIVEL, MOTIVO_NAO_LOCALIZADO, MOTIVO_SEM_FATURA,
    MOTIVO_SERVICO, Leitura, ler,
    PASTA_VENCIMENTOS, _dv_modulo10, data_do_fator, pasta_vencimento, texto_pdf, vencimento, vencimento_boleto, vencimento_da_mensagem,
    vencimento_nfe, vencimento_texto,
)
from tests.conftest import nfe_com_vencimentos, pdf_com_texto

REFERENCIA = date(2026, 9, 18)


def linha_digitavel(vence: date, *, valida: bool = True) -> str:
    """Linha digitável sintética do banco 001 com o fator de vencimento de `vence` (ciclo de 2025)."""
    fator = 1000 + (vence - date(2025, 2, 22)).days
    campos = ["001900000", "0000000000", "0000000000"]
    dvs = [_dv_modulo10(c) for c in campos]
    if not valida:
        dvs[0] = (dvs[0] + 1) % 10
    c1, c2, c3 = (f"{c}{dv}" for c, dv in zip(campos, dvs))
    return f"{c1[:5]}.{c1[5:]} {c2[:5]}.{c2[5:]} {c3[:5]}.{c3[5:]} 1 {fator:04d}0000012345"


def test_nfe_devolve_o_primeiro_vencimento_das_parcelas():
    assert vencimento_nfe(nfe_com_vencimentos("2026-11-10", "2026-10-10", "2026-12-10")) == date(2026, 10, 10)


def test_nfe_sem_cobranca_nao_tem_vencimento(dados):
    assert vencimento_nfe(nfe_com_vencimentos()) is None
    assert vencimento_nfe((dados / "nfe_proc.xml").read_bytes()) is None
    assert vencimento_nfe(b"%PDF nao e xml") is None


@pytest.mark.parametrize("fator, esperado", [
    (1000, date(2025, 2, 22)),          # recomeço do ciclo em 2025
    (1669, date(2026, 12, 23)),
    (9999, date(2025, 2, 21)),          # último dia do ciclo antigo
])
def test_fator_de_vencimento_escolhe_o_ciclo_mais_proximo(fator, esperado):
    assert data_do_fator(fator, REFERENCIA) == esperado


def test_fator_zero_e_boleto_sem_vencimento():
    assert data_do_fator(0, REFERENCIA) is None


def test_fator_do_ciclo_antigo_vale_para_documento_antigo():
    assert data_do_fator(1000, date(2000, 7, 1)) == date(2000, 7, 3)


def test_boleto_pela_linha_digitavel():
    texto = f"Banco do Brasil\nLinha digitável: {linha_digitavel(date(2026, 10, 15))}\n"
    assert vencimento_boleto(texto, REFERENCIA) == date(2026, 10, 15)


def test_linha_digitavel_sem_separadores():
    linha = linha_digitavel(date(2026, 10, 15)).replace(".", "").replace(" ", "")
    assert vencimento_boleto(linha, REFERENCIA) == date(2026, 10, 15)


def test_linha_digitavel_com_digitos_colados_ao_fim():
    assert vencimento_boleto(linha_digitavel(date(2026, 10, 15)) + "745", REFERENCIA) == date(2026, 10, 15)


def test_sequencia_com_digito_verificador_errado_nao_e_linha_digitavel():
    assert vencimento_boleto(linha_digitavel(date(2026, 10, 15), valida=False), REFERENCIA) is None


@pytest.mark.parametrize("texto, esperado", [
    ("Data de Vencimento: 05/11/2026", date(2026, 11, 5)),
    ("VENCIMENTO\n05.11.2026", date(2026, 11, 5)),
    ("Vencto 30-01-2027 Valor R$ 10,00", date(2027, 1, 30)),
    ("Vencimentos: [109143-1(1) 30/09/2026 2.377,83]", date(2026, 9, 30)),
    ("Data Emissão Data Vencimento\n5750-9 12345-7 10/09/2026 02/10/2026", date(2026, 10, 2)),
    ("Venc. 31/02/2026", None),
    ("Emissão 01/09/2026", None),
    ("Vencimento 01/01/2026", None),   # antes do recebimento: não é o vencimento deste documento
    ("Vencimento\nBeneficiário X\nData de Emissão\n18/09/2026", None),   # a emissão, no dia do recebimento
    ("VENCIMENTO: 18/09/2026", date(2026, 9, 18)),   # colada ao rótulo, vale no dia do recebimento
    ("Vencimento: 17/09/2026", None),                # colada, mas já vencida
    ("DUPLICATAS\n001\n18/10/2026 1.200,00", date(2026, 10, 18)),
    ("Duplicata 002 - 05/11/2026", date(2026, 11, 5)),
])
def test_vencimento_no_texto(texto, esperado):
    assert vencimento_texto(texto, REFERENCIA) == esperado


def test_texto_de_pdf_e_pdf_ilegivel(tmp_path):
    bom = tmp_path / "a.pdf"
    bom.write_bytes(pdf_com_texto("Vencimento: 05/11/2026"))
    assert "05/11/2026" in texto_pdf(bom)
    ruim = tmp_path / "b.pdf"
    ruim.write_bytes(b"%PDF-1.4 corrompido")
    assert texto_pdf(ruim) == ""


def test_ordem_das_fontes_para_pdf(tmp_path):
    boleto = tmp_path / "boleto.pdf"
    boleto.write_bytes(pdf_com_texto("Vencimento 01/01/2027", linha_digitavel(date(2026, 11, 10))))
    da_mensagem = date(2026, 10, 10)
    # a linha digitável do próprio boleto vence o XML da mensagem, que vence o texto
    assert vencimento(boleto, xml=False, vencimento_mensagem=da_mensagem, referencia=REFERENCIA) == date(2026, 11, 10)
    danfe = tmp_path / "danfe.pdf"
    danfe.write_bytes(pdf_com_texto("Vencimento 01/01/2027"))
    assert vencimento(danfe, xml=False, vencimento_mensagem=da_mensagem, referencia=REFERENCIA) == da_mensagem
    assert vencimento(danfe, xml=False, vencimento_mensagem=None, referencia=REFERENCIA) == date(2027, 1, 1)


def test_ordem_das_fontes_para_xml(tmp_path):
    xml = tmp_path / "nota.xml"
    xml.write_bytes(nfe_com_vencimentos("2026-10-20"))
    assert vencimento(xml, xml=True, vencimento_mensagem=date(2026, 10, 10), referencia=REFERENCIA) == date(2026, 10, 20)
    xml.write_bytes(nfe_com_vencimentos())
    assert vencimento(xml, xml=True, vencimento_mensagem=None, referencia=REFERENCIA) is None


def test_imagem_so_tem_o_vencimento_da_mensagem(tmp_path):
    foto = tmp_path / "boleto.jpg"
    foto.write_bytes(b"\xff\xd8\xff")
    assert vencimento(foto, xml=False, vencimento_mensagem=None, referencia=REFERENCIA) is None
    assert vencimento(foto, xml=False, vencimento_mensagem=date(2026, 10, 10), referencia=REFERENCIA) == date(2026, 10, 10)


def test_pasta_por_vencimento():
    assert pasta_vencimento("AFLA Financeiro/CONTAS A PAGAR/", date(2026, 3, 5)) == (
        f"AFLA Financeiro/CONTAS A PAGAR/{PASTA_VENCIMENTOS}/DIA 5/202X-03")
    assert pasta_vencimento("X", date(2027, 12, 31)).endswith("/DIA 31/202X-12")


def test_sem_vencimento_fica_na_raiz_do_destino():
    assert pasta_vencimento("AFLA Financeiro/CONTAS A PAGAR/", None) == "AFLA Financeiro/CONTAS A PAGAR"



def test_vencimento_da_mensagem_prefere_o_xml_e_cai_no_boleto():
    boleto = ("boleto.pdf", pdf_com_texto(linha_digitavel(date(2026, 11, 10))))
    xml = ("nota.xml", nfe_com_vencimentos("2026-11-20", "2026-10-20"))
    danfe = ("danfe.pdf", pdf_com_texto("DANFE"))
    assert vencimento_da_mensagem([danfe, boleto, xml], REFERENCIA) == date(2026, 10, 20)
    assert vencimento_da_mensagem([danfe, boleto, ("nota.xml", nfe_com_vencimentos())], REFERENCIA) == date(2026, 11, 10)
    assert vencimento_da_mensagem([danfe], REFERENCIA) is None


# --- motivo de ir à raiz (feature 006) ------------------------------------------------

def _ler(tmp_path, conteudo: bytes, nome: str, vencimento_mensagem=None):
    arquivo = tmp_path / nome
    arquivo.write_bytes(conteudo)
    return ler(arquivo, xml=nome.endswith(".xml"), vencimento_mensagem=vencimento_mensagem, referencia=REFERENCIA)


PALAVRAS = "Prefeitura Municipal emitiu este documento para o tomador indicado abaixo conforme contrato vigente"


@pytest.mark.parametrize("conteudo, nome, motivo", [
    (nfe_com_vencimentos(a_vista=True), "nota.xml", MOTIVO_A_VISTA),
    (nfe_com_vencimentos(), "nota.xml", MOTIVO_SEM_FATURA),
    (pdf_com_texto("NFS-e Nota Fiscal de Servico Eletronica", PALAVRAS), "nfse.pdf", MOTIVO_SERVICO),
    (pdf_com_texto("DANF-E Documento Auxiliar da Nota Fiscal Eletronica", PALAVRAS), "danfe.pdf", MOTIVO_DANFE),
    (pdf_com_texto("/0/1 /2 /3 /4 /5 /6 /3 /7"), "fonte.pdf", MOTIVO_ILEGIVEL),
    (b"nao e pdf", "digitalizado.pdf", MOTIVO_ILEGIVEL),
    (b"\x89PNG", "foto.png", MOTIVO_FORMATO),
    (pdf_com_texto("Proposta comercial", PALAVRAS), "proposta.pdf", MOTIVO_NAO_LOCALIZADO),
    (pdf_com_texto("Boleto", "Vencimento: 10/09/2026", PALAVRAS), "boleto.pdf", "já chegou vencido: venceu em 10/09/2026"),
    (pdf_com_texto("DANFE", "DUPLICATAS", "001", "10/09/2026", PALAVRAS), "danfe.pdf",
     "já chegou vencido: venceu em 10/09/2026"),
])
def test_motivo_de_ficar_na_raiz(tmp_path, conteudo, nome, motivo):
    assert _ler(tmp_path, conteudo, nome) == Leitura(None, motivo)


def test_data_solta_anterior_nao_e_tomada_como_vencida(tmp_path):
    leitura = _ler(tmp_path, pdf_com_texto("DANFE", "Vencimento Valor", "Emissao 10/09/2026", PALAVRAS), "danfe.pdf")
    assert leitura == Leitura(None, MOTIVO_DANFE)


def test_com_vencimento_nao_ha_motivo(tmp_path):
    assert _ler(tmp_path, nfe_com_vencimentos("2026-10-05"), "nota.xml") == Leitura(date(2026, 10, 5))
    assert _ler(tmp_path, b"\x89PNG", "foto.png", date(2026, 10, 5)) == Leitura(date(2026, 10, 5))
