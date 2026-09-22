"""Testes da extração MIME (CE RF-04, EC-05, EC-06, EC-08, fluxo alternativo B)."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from email.message import EmailMessage

import pytest

from email_nf_onedrive.coleta.mime import analisar_mensagem


def _analisar(dados, nome):
    return analisar_mensagem((dados / nome).read_bytes())


def test_metadados_da_mensagem(dados):
    msg = _analisar(dados, "boleto_simples.eml")
    assert msg.message_id == "<boleto-simples@fornecedor.example>"
    assert msg.remetente == "cobranca@fornecedor.example"
    assert msg.assunto == "Boleto referente a setembro"
    assert msg.data == datetime(2026, 9, 18, 15, 0, tzinfo=timezone.utc)


def test_anexo_pdf_simples(dados):
    msg = _analisar(dados, "boleto_simples.eml")
    assert [a.nome for a in msg.anexos] == ["Boleto Set.pdf"]
    anexo = msg.anexos[0]
    assert anexo.conteudo.startswith(b"%PDF")
    assert anexo.sha256 == hashlib.sha256(anexo.conteudo).hexdigest()


def test_ignora_imagem_e_reconhece_extensao_maiuscula(dados):
    msg = _analisar(dados, "pdf_e_png.eml")
    assert [a.nome for a in msg.anexos] == ["NF123.PDF"]


def test_xml_reconhecido_pelo_tipo(dados):
    msg = _analisar(dados, "nfe_xml.eml")
    assert [a.nome for a in msg.anexos] == ["arquivo.xml"]
    assert b"nfeProc" in msg.anexos[0].conteudo


def test_nome_codificado_rfc2047(dados):
    msg = _analisar(dados, "nome_codificado.eml")
    assert [a.nome for a in msg.anexos] == ["Nota Fiscal nº 45.pdf"]


def test_anexo_sem_nome_recebe_nome_gerado(dados):
    msg = _analisar(dados, "sem_nome.eml")
    assert [a.nome for a in msg.anexos] == ["anexo-1.pdf"]


def test_mensagem_encaminhada(dados):
    msg = _analisar(dados, "encaminhada.eml")
    assert [a.nome for a in msg.anexos] == ["boleto_encaminhado.pdf"]
    assert msg.remetente == "colega@empresa.example"
    assert msg.assunto == "Fwd: Boleto original"


def test_compactado_sinalizado_e_nao_extraido(dados):
    msg = _analisar(dados, "compactado.eml")
    assert msg.anexos == ()
    assert msg.compactados == ("notas.zip",)


def test_mensagem_sem_anexo(dados):
    msg = _analisar(dados, "nfse_link.eml")
    assert msg.anexos == ()
    assert msg.compactados == ()
    assert msg.assunto == "Sua NFS-e está disponível"


def test_identificador_substituto_sem_message_id(dados):
    bruto = (dados / "sem_message_id.eml").read_bytes()
    msg1 = analisar_mensagem(bruto)
    msg2 = analisar_mensagem(bruto)
    assert msg1.message_id.startswith("sem-id:")
    assert msg1.message_id == msg2.message_id
    assert len(msg1.message_id) == len("sem-id:") + 64


def test_mensagem_sem_data():
    bruto = (
        b"From: a@fornecedor.example\r\nSubject: sem data\r\nMessage-ID: <x@y>\r\n\r\ncorpo\r\n"
    )
    msg = analisar_mensagem(bruto)
    assert msg.data is None
    assert msg.anexos == ()


# --- Remetente original de encaminhamentos (BUG-20260922-VBJD) --------------------------------


def _com_corpo(corpo: str) -> bytes:
    mensagem = EmailMessage()
    mensagem["From"] = "Colega <colega@empresa.example>"
    mensagem["Subject"] = "Fwd: Boleto"
    mensagem["Message-ID"] = "<corpo@empresa.example>"
    mensagem.set_content(corpo)
    mensagem.add_attachment(b"%PDF-1.4\n", maintype="application", subtype="pdf", filename="boleto.pdf")
    return mensagem.as_bytes()


def test_encaminhada_como_anexo_expoe_o_remetente_original(dados):
    msg = _analisar(dados, "encaminhada.eml")
    assert msg.remetente == "colega@empresa.example"
    assert msg.remetentes_encaminhados == ("cobranca@fornecedor.example",)


def test_encaminhada_em_linha_expoe_o_remetente_original(dados):
    msg = _analisar(dados, "encaminhada_em_linha.eml")
    assert msg.remetente == "colega@empresa.example"
    assert [a.nome for a in msg.anexos] == ["boleto_setembro.pdf"]
    assert msg.remetentes_encaminhados == ("cobranca@fornecedor.example",)


def test_mensagem_direta_nao_tem_remetente_encaminhado(dados):
    assert _analisar(dados, "boleto_simples.eml").remetentes_encaminhados == ()


@pytest.mark.parametrize(
    ("corpo", "esperado"),
    [
        ("---------- Forwarded message ---------\nFrom: Cobranca <cobranca@fornecedor.example>\nDate: Thu\n",
         ("cobranca@fornecedor.example",)),
        ("-----Mensagem original-----\nDe: Cobranca [mailto:Cobranca@Fornecedor.example]\nEnviada em: quinta\n",
         ("cobranca@fornecedor.example",)),
        ("Veja abaixo.\n\n> De: nf@fornecedor.example\n> Assunto: NF\n", ("nf@fornecedor.example",)),
        ("*From:* Cobranca <cobranca@fornecedor.example>\n", ("cobranca@fornecedor.example",)),
        ("---------- Forwarded message ---------\nFrom: Colega B <b@empresa.example>\n\n"
         "---------- Forwarded message ---------\nFrom: <nf@fornecedor.example>\n",
         ("nf@fornecedor.example", "b@empresa.example")),
        ("Período de cobrança\nDe: 01/09 a 30/09\n", ()),
        ("Segue o boleto, de acordo com a nota.\n", ()),
    ],
)
def test_remetentes_citados_no_corpo(corpo, esperado):
    assert analisar_mensagem(_com_corpo(corpo)).remetentes_encaminhados == esperado
