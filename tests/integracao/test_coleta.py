"""Integração da coleta com servidor IMAP dublê (T033, CE RF-01 a RF-11, RN-01, RN-03, RN-09)."""

from __future__ import annotations

import logging
from datetime import date

import pytest

from email_nf_onedrive.coleta.coleta import coletar
from email_nf_onedrive.coleta.imap import ClienteIMAP
from email_nf_onedrive.configuracao.modelo import Caixa
from email_nf_onedrive.registro.banco import Registro

from .dubles import ServidorIMAPFalso

pytestmark = pytest.mark.integracao

COMANDOS_PERMITIDOS = {"CONNECT", "LOGIN", "LIST", "EXAMINE", "SEARCH", "FETCH", "LOGOUT"}


def _caixa(indice=1, endereco="financeiro@empresa.example", senha="app-1", pasta="INBOX"):
    return Caixa(indice=indice, endereco=endereco, senha=senha, pasta=pasta,
                 imap_host=f"imap{indice}.example", destino="Destino")


@pytest.fixture
def servidor(dados):
    servidor = ServidorIMAPFalso()
    servidor.adicionar_caixa("financeiro@empresa.example", "app-1")
    return servidor


@pytest.fixture
def ambiente(home, servidor):
    """Executa a coleta com o servidor dublê; devolve (resultados, registro aberto)."""
    abertos = []

    def _coletar(*caixas, data_inicial=date(2026, 9, 1)):
        registro = Registro.abrir(home / "var" / "registro.sqlite3")
        abertos.append(registro)
        fabrica = lambda c: ClienteIMAP(c.imap_host, c.imap_porta, fabrica=servidor.fabrica)
        resultados = coletar(caixas or (_caixa(),), registro, home / "var" / "trabalho" / "x",
                             data_inicial, logging.getLogger("teste-coleta"), fabrica)
        registro.commit()
        return resultados, registro

    yield _coletar
    for registro in abertos:
        registro.fechar()


def _entregar(servidor, dados, *nomes, caixa="financeiro@empresa.example", pasta="INBOX"):
    for nome in nomes:
        servidor.entregar(caixa, (dados / nome).read_bytes(), pasta)


def test_so_comandos_de_leitura_e_body_peek(servidor, dados, ambiente):
    _entregar(servidor, dados, "boleto_simples.eml", "pdf_e_png.eml", "proposta_contrato.eml")
    ambiente()
    assert servidor.nomes_de_comandos() <= COMANDOS_PERMITIDOS
    assert "SELECT" not in servidor.nomes_de_comandos()
    fetches = [c for c in servidor.comandos if c[0] == "FETCH"]
    assert fetches and all(c[2] == "(BODY.PEEK[])" for c in fetches)
    assert servidor.lidas == set()


def test_extrai_classifica_e_grava_na_pasta_de_trabalho(servidor, dados, ambiente):
    _entregar(servidor, dados, "boleto_simples.eml", "nfe_xml.eml", "encaminhada.eml")
    (resultado,), _registro = ambiente()
    assert resultado.falha is None
    nomes = sorted(item.nome_original for item in resultado.para_envio)
    assert nomes == ["Boleto Set.pdf", "arquivo.xml", "boleto_encaminhado.pdf"]
    assert resultado.classes["nfe-xml"] == 1
    for item in resultado.para_envio:
        assert item.caminho_local.exists()
        assert oct(item.caminho_local.stat().st_mode & 0o777) == oct(0o600)


def test_sem_classificacao_e_retido_e_nao_vai_para_envio(servidor, dados, ambiente, caplog):
    _entregar(servidor, dados, "proposta_contrato.eml")
    with caplog.at_level(logging.INFO, logger="teste-coleta"):
        (resultado,), registro = ambiente()
    assert resultado.para_envio == []
    assert resultado.retidos == 1
    assert sum("retido para revisão" in r.getMessage() for r in caplog.records) == 1


def test_segunda_execucao_nao_entrega_nada_nem_repete_retido(servidor, dados, ambiente, caplog):
    _entregar(servidor, dados, "boleto_simples.eml", "proposta_contrato.eml")
    (primeira,), registro = ambiente()
    registro.marcar_enviado(primeira.para_envio[0].anexo_id, "Destino/x.pdf")
    registro.commit()
    registro.fechar()
    caplog.clear()
    with caplog.at_level(logging.INFO, logger="teste-coleta"):
        (segunda,), _ = ambiente()
    assert segunda.para_envio == []
    assert segunda.retidos == 0
    assert not any("retido para revisão" in r.getMessage() for r in caplog.records)
    assert any("nenhum anexo novo" in r.getMessage() for r in caplog.records)


def test_anexo_pendente_e_reentregue_sem_duplicar_registro(servidor, dados, ambiente):
    _entregar(servidor, dados, "boleto_simples.eml")
    (primeira,), registro = ambiente()
    registro.marcar_falha_envio(primeira.para_envio[0].anexo_id, "timeout")
    registro.commit()
    registro.fechar()
    (segunda,), registro = ambiente()
    assert [i.anexo_id for i in segunda.para_envio] == [primeira.para_envio[0].anexo_id]
    assert len(registro.pendentes("financeiro@empresa.example")) == 1


def test_sem_anexo_e_compactado_registrados_uma_vez(servidor, dados, ambiente, caplog):
    _entregar(servidor, dados, "nfse_link.eml", "compactado.eml")
    with caplog.at_level(logging.INFO, logger="teste-coleta"):
        (resultado,), registro = ambiente()
        registro.fechar()
        ambiente()
    mensagens = [r.getMessage() for r in caplog.records]
    assert sum("possível documento sem anexo" in m for m in mensagens) == 1
    assert sum("anexo compactado ignorado" in m for m in mensagens) == 1
    assert resultado.para_envio == []


def test_janela_respeita_data_inicial(servidor, dados, ambiente):
    _entregar(servidor, dados, "boleto_simples.eml")  # mensagem de 18/09/2026
    (resultado,), _ = ambiente(data_inicial=date(2026, 9, 20))
    assert resultado.para_envio == []
    assert ("SEARCH", "SINCE", "20-Sep-2026") in servidor.comandos


def test_falha_da_caixa_1_nao_impede_a_caixa_2(servidor, dados, ambiente):
    servidor.adicionar_caixa("outra@empresa.example", "app-2")
    _entregar(servidor, dados, "boleto_simples.eml", caixa="outra@empresa.example")
    r1, r2 = ambiente(
        _caixa(1, senha="senha-errada"),
        _caixa(2, endereco="outra@empresa.example", senha="app-2"),
    )[0]
    assert r1.falha.causa == "caixa1:autenticacao"
    assert "verifique a senha de app" in r1.falha.mensagem
    assert r2.falha is None
    assert len(r2.para_envio) == 1


def test_pasta_inexistente_lista_as_pastas(servidor, dados, ambiente, caplog):
    servidor.caixas["financeiro@empresa.example"][1]["Notas Fiscais/Março"] = []
    with caplog.at_level(logging.INFO, logger="teste-coleta"):
        (resultado,), _ = ambiente(_caixa(pasta="Notas"))
    assert resultado.falha.causa == "caixa1:pasta"
    assert any("Notas Fiscais/Março" in r.getMessage() for r in caplog.records)


def test_pasta_com_acento_e_codificada(servidor, dados, ambiente):
    servidor.caixas["financeiro@empresa.example"][1]["Notas Fiscais/Março"] = []
    _entregar(servidor, dados, "boleto_simples.eml", pasta="Notas Fiscais/Março")
    (resultado,), _ = ambiente(_caixa(pasta="Notas Fiscais/Março"))
    assert resultado.falha is None
    assert ("EXAMINE", '"Notas Fiscais/Mar&AOc-o"') in servidor.comandos
    assert len(resultado.para_envio) == 1


def test_servidor_fora_do_ar(servidor, ambiente):
    servidor.fora_do_ar.add("imap1.example")
    (resultado,), _ = ambiente()
    assert resultado.falha.causa == "caixa1:conexao"
