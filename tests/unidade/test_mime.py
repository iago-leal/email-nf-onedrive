"""Testes da extração MIME (CE RF-04, EC-05, EC-06, EC-08, fluxo alternativo B)."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

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
