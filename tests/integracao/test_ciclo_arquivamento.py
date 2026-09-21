"""Cenários de arquivamento de ponta a ponta (T040, requirements.md §7)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.integracao

BOLETO = "ACME - FORNECEDOR - BOLETO.pdf"
NFE = "ACME - FORNECEDOR FICTICIO LTDA - REF.xml"


def test_boleto_arquivado(cenario):
    cenario.entregar("boleto_simples.eml")
    assert cenario.executar("executar") == 0
    assert cenario.arquivos_no_destino() == [BOLETO]
    assert cenario.estados() == ["enviado"]
    assert "resumo: 1 caixa, 1 extraídos, 1 enviados, 0 falhas" in cenario.log()
    assert list((cenario.home / "var" / "trabalho").iterdir()) == []
    assert cenario.transporte.enviadas == []
    assert cenario.servidor.lidas == set()


def test_reexecucao_nao_duplica(cenario):
    cenario.entregar("boleto_simples.eml", "nfe_xml.eml")
    assert cenario.executar("executar") == 0
    cenario.relogio.avancar(minutes=30)
    assert cenario.executar("executar") == 0
    assert cenario.arquivos_no_destino() == [BOLETO, NFE]
    assert cenario.estados() == ["enviado", "enviado"]
    assert "resumo: 1 caixa, 0 extraídos, 0 enviados, 0 falhas" in cenario.log()
    assert "(desde a execução anterior: 30 min)" in cenario.log()


def test_nome_repetido_recebe_sufixo_e_preserva_o_original(cenario):
    (cenario.destino / BOLETO).write_bytes(b"%PDF arquivo da equipe")
    cenario.entregar("boleto_simples.eml")
    assert cenario.executar("executar") == 0
    assert (cenario.destino / BOLETO).read_bytes() == b"%PDF arquivo da equipe"
    assert cenario.arquivos_no_destino() == [BOLETO, "ACME - FORNECEDOR - BOLETO_2.pdf"]


def test_retomada_apos_falha_de_envio(cenario):
    cenario.entregar("boleto_simples.eml")
    cenario.destino.rename(cenario.destino.with_name("RENOMEADA"))
    assert cenario.executar("executar") == 1
    assert cenario.estados() == ["falha-envio"]
    assert "destino não encontrado" in cenario.transporte.enviadas[0]
    assert not cenario.destino.exists()  # a pasta não é criada automaticamente

    cenario.destino.with_name("RENOMEADA").rename(cenario.destino)
    cenario.relogio.avancar(minutes=30)
    assert cenario.executar("executar") == 0
    assert cenario.arquivos_no_destino() == [BOLETO]
    assert cenario.estados() == ["enviado"]
    assert "recuperado: envio ao OneDrive voltou a funcionar" in cenario.transporte.enviadas[-1]


def test_documento_sem_classificacao_fica_retido(cenario):
    cenario.entregar("proposta_contrato.eml")
    assert cenario.executar("executar") == 0
    assert cenario.arquivos_no_destino() == []
    assert cenario.estados() == ["retido"]
    log = cenario.log()
    assert "retido para revisão" in log
    assert "1 retidos" in log


def test_sem_anexo_e_compactado_registrados_uma_vez(cenario):
    cenario.entregar("nfse_link.eml", "compactado.eml")
    assert cenario.executar("executar") == 0
    assert cenario.executar("executar") == 0
    log = cenario.log()
    assert log.count("possível documento sem anexo") == 1
    assert log.count("anexo compactado ignorado (notas.zip)") == 1
    assert cenario.arquivos_no_destino() == []


def test_simulacao_nao_envia_nao_registra_nem_avisa(cenario):
    cenario.entregar("boleto_simples.eml")
    assert cenario.executar("executar", "--simular") == 0
    assert cenario.arquivos_no_destino() == []
    assert not (cenario.home / "var" / "registro.sqlite3").exists()
    assert "simulação: enviaria" in cenario.log()
    assert cenario.transporte.enviadas == []


def test_simulacao_com_registro_existente_nao_o_altera(cenario):
    cenario.entregar("proposta_contrato.eml")
    assert cenario.executar("executar") == 0
    cenario.entregar("boleto_simples.eml")
    assert cenario.executar("executar", "--simular") == 0
    assert cenario.estados() == ["retido"]
    assert cenario.arquivos_no_destino() == []
