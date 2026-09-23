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

# W014: a lista é fechada. A feature 002 acrescentou AUTHENTICATE (XOAUTH2) e nada mais.
COMANDOS_PERMITIDOS = {"CONNECT", "LOGIN", "AUTHENTICATE", "LIST", "EXAMINE", "SEARCH", "FETCH", "LOGOUT"}


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

    def _coletar(*caixas, data_inicial=date(2026, 9, 1), provedor=None):
        registro = Registro.abrir(home / "var" / "registro.sqlite3")
        abertos.append(registro)
        fabrica = lambda c: ClienteIMAP(c.imap_host, c.imap_porta, fabrica=servidor.fabrica)
        resultados = coletar(caixas or (_caixa(),), registro, home / "var" / "trabalho" / "x",
                             data_inicial, logging.getLogger("teste-coleta"), fabrica, provedor)
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
    assert fetches and all(c[2] in ("(BODY.PEEK[])", "(BODY.PEEK[HEADER.FIELDS (MESSAGE-ID)])") for c in fetches)
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


def test_coleta_entrega_ao_envio_as_fontes_do_fornecedor(servidor, dados, ambiente):
    """BUG-20260922-VBJD: emitente do XML irmão e remetente original, também no reenvio de pendente."""
    _entregar(servidor, dados, "interna_nfe_e_danfe.eml", "encaminhada_em_linha.eml", "encaminhada.eml")
    for _ in range(2):  # a 2ª rodada reentrega os pendentes, que ainda não foram enviados
        (resultado,), registro = ambiente()
        por_nome = {item.nome_original: item for item in resultado.para_envio}
        assert sorted(por_nome) == ["boleto_encaminhado.pdf", "boleto_setembro.pdf", "danfe.pdf", "nfe.xml"]
        assert por_nome["danfe.pdf"].emitente_mensagem == "FORNECEDOR FICTICIO LTDA"
        assert por_nome["nfe.xml"].emitente_mensagem == "FORNECEDOR FICTICIO LTDA"
        assert por_nome["boleto_setembro.pdf"].remetentes_encaminhados == ("cobranca@fornecedor.example",)
        assert por_nome["boleto_setembro.pdf"].emitente_mensagem == ""
        assert por_nome["boleto_encaminhado.pdf"].remetentes_encaminhados == ("cobranca@fornecedor.example",)
        assert {item.remetente for item in resultado.para_envio} == {"colega@empresa.example"}
        registrados = registro.pendentes("financeiro@empresa.example")
        assert {a.remetente for a in registrados} == {"colega@empresa.example"}  # o registro guarda o From de topo
        registro.fechar()


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


# --- Feature 002: caixa em modo oauth (D-07, D-08, interfaces/imap-gmail-xoauth2.md) ---------

CAIXA_OAUTH = "fiscal@cliente.example"


class _ProvedorFixo:
    """Faz o papel de `autorizacao.credencial.ProvedorCredencial`: devolve a credencial temporária."""

    def __init__(self, credencial: str) -> None:
        self.credencial = credencial
        self.pedidos: list[int] = []

    def obter(self, caixa) -> str:
        self.pedidos.append(caixa.indice)
        return self.credencial


def _caixa_oauth(indice=2):
    return Caixa(indice=indice, endereco=CAIXA_OAUTH, senha="", pasta="INBOX", imap_host=f"imap{indice}.example",
                 destino="Destino", modo="oauth")


def test_caixa_oauth_conecta_por_xoauth2_sem_login(servidor, dados, ambiente, caplog):
    servidor.adicionar_caixa_oauth(CAIXA_OAUTH, "ya29.valida")
    _entregar(servidor, dados, "boleto_simples.eml", caixa=CAIXA_OAUTH)
    provedor = _ProvedorFixo("ya29.valida")
    with caplog.at_level(logging.INFO):
        (resultado,), _registro = ambiente(_caixa_oauth(), provedor=provedor)
    assert resultado.falha is None
    assert [item.nome_original for item in resultado.para_envio] == ["Boleto Set.pdf"]
    assert provedor.pedidos == [2]
    assert ("AUTHENTICATE", "XOAUTH2") in servidor.comandos
    assert "LOGIN" not in servidor.nomes_de_comandos()
    assert servidor.nomes_de_comandos() <= COMANDOS_PERMITIDOS
    assert "caixa 2: conectada (oauth)" in caplog.text


def test_caixa_senha_nao_consulta_o_provedor_e_registra_o_modo(servidor, ambiente, caplog):
    provedor = _ProvedorFixo("ya29.valida")
    with caplog.at_level(logging.INFO):
        ambiente(provedor=provedor)
    assert provedor.pedidos == []
    assert "AUTHENTICATE" not in servidor.nomes_de_comandos()
    assert "caixa 1: conectada (senha)" in caplog.text


def test_xoauth2_recusado_responde_ao_desafio_e_falha_por_autorizacao(servidor, dados, ambiente, caplog):
    servidor.adicionar_caixa_oauth(CAIXA_OAUTH, "ya29.valida")
    _entregar(servidor, dados, "boleto_simples.eml")
    with caplog.at_level(logging.INFO):
        r1, r2 = ambiente(_caixa(), _caixa_oauth(), provedor=_ProvedorFixo("ya29.recusada"))[0]
    assert r1.falha is None and len(r1.para_envio) == 1  # RN-09: a falha de uma caixa não para as outras
    assert r2.falha.causa == "caixa2:autorizacao"
    assert r2.falha.mensagem == ("caixa 2: autorização OAuth recusada pelo servidor de e-mail. "
                                 "Ação: rode autorizar-caixa 2 e confira se o IMAP está ativo na conta.")
    assert '"status": "400"' in caplog.text  # o desafio decodificado vai ao log
    assert "ya29.recusada" not in caplog.text


def test_mensagem_resolvida_nao_e_baixada_de_novo(servidor, dados, ambiente):
    """Só o Message-ID das mensagens resolvidas é lido; o corpo, nunca mais (coleta sem download repetido)."""
    _entregar(servidor, dados, "boleto_simples.eml", "proposta_contrato.eml", "sem_message_id.eml")
    (primeira,), registro = ambiente()
    boleto = next(i for i in primeira.para_envio if i.nome_original == "Boleto Set.pdf")
    registro.marcar_enviado(boleto.anexo_id, "Destino/ACME - FORNECEDOR - BOLETO.pdf")
    registro.commit()
    servidor.comandos.clear()

    (segunda,), _ = ambiente()
    corpos = [c[1] for c in servidor.comandos if c[0] == "FETCH" and c[2] == "(BODY.PEEK[])"]
    assert corpos == [b"3"]  # boleto enviado e proposta retida ficam de fora; sem Message-ID, não há como saber
    assert [i.anexo_id for i in segunda.para_envio] == [i.anexo_id for i in primeira.para_envio if i is not boleto]


def test_mensagem_com_pendente_continua_sendo_baixada(servidor, dados, ambiente):
    _entregar(servidor, dados, "boleto_simples.eml", "proposta_contrato.eml")
    ambiente()
    servidor.comandos.clear()
    (segunda,), _ = ambiente()
    corpos = [c[1] for c in servidor.comandos if c[0] == "FETCH" and c[2] == "(BODY.PEEK[])"]
    assert corpos == [b"1"]
    assert [i.nome_original for i in segunda.para_envio] == ["Boleto Set.pdf"]
