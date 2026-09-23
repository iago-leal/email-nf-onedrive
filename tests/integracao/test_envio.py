"""Integração do envio com o Rclone real contra diretório local (T036, EO RF-01 a RF-10)."""

from __future__ import annotations

import logging
import shutil
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from email_nf_onedrive.coleta.coleta import AnexoParaEnvio
from email_nf_onedrive.configuracao.modelo import Caixa
from email_nf_onedrive.envio.envio import TENTATIVAS_PARA_AVISO, ResultadoEnvio, enviar_anexos
from email_nf_onedrive.envio.rclone import Rclone
from email_nf_onedrive.envio import teste_onedrive
from email_nf_onedrive.envio.vencimento import PASTA_VENCIMENTOS
from email_nf_onedrive.registro.banco import Registro
from tests.conftest import nfe_com_vencimentos, pdf_com_texto
from tests.unidade.test_vencimento import linha_digitavel

pytestmark = [
    pytest.mark.integracao,
    pytest.mark.skipif(shutil.which("rclone") is None, reason="rclone não instalado"),
]

RECEBIDO = datetime(2026, 9, 18, 15, 0, tzinfo=timezone.utc)
LOG = logging.getLogger("teste-envio")


@pytest.fixture
def destino(tmp_path):
    pasta = tmp_path / "onedrive" / "CONTAS A PAGAR"
    pasta.mkdir(parents=True)
    return pasta


@pytest.fixture
def registro(home):
    reg = Registro.abrir(home / "var" / "registro.sqlite3")
    yield reg
    reg.fechar()


@pytest.fixture
def novo_item(home, registro, destino):
    trabalho = home / "var" / "trabalho"
    trabalho.mkdir(parents=True)
    contador = iter(range(1, 1000))

    def _novo(conteudo: bytes, nome="boleto.pdf", remetente="cobranca@fornecedor.example", pasta_destino=None,
              classe="palavra-chave", vencimento_mensagem=None):
        n = next(contador)
        caixa = Caixa(1, "financeiro@empresa.example", "s", "INBOX", "imap", str(pasta_destino or destino), empresa="ACME")
        anexo = registro.registrar_anexo(
            caixa_endereco=caixa.endereco, caixa_indice=1, message_id=f"<m{n}>", sha256=f"{n:064d}",
            nome_original=nome, remetente=remetente, assunto="Boleto", data_mensagem=RECEBIDO,
            classe=classe,
        )
        local = trabalho / f"{anexo.id}{Path(nome).suffix.lower()}"
        local.write_bytes(conteudo)
        return AnexoParaEnvio(anexo.id, local, caixa, nome, remetente, RECEBIDO, anexo.sha256, assunto="Boleto",
                              classe=classe, vencimento_mensagem=vencimento_mensagem)

    return _novo


def _estado(registro, item):
    return registro.buscar(item.caixa.endereco, f"<m{item.anexo_id}>", item.sha256)


def test_envio_novo_confirma_registra_e_apaga_copia_local(registro, destino, novo_item):
    item = novo_item(b"%PDF conteudo A")
    resultado = enviar_anexos([item], registro, Rclone(":local"), LOG)
    final = destino / "ACME - FORNECEDOR - BOLETO.pdf"
    assert final.read_bytes() == b"%PDF conteudo A"
    anexo = _estado(registro, item)
    assert anexo.estado == "enviado"
    assert anexo.caminho_destino == f"{destino}/ACME - FORNECEDOR - BOLETO.pdf"
    assert not item.caminho_local.exists()
    assert resultado.enviados == 1 and resultado.falhas == []


def test_arquivo_identico_ja_presente_nao_e_reenviado(registro, destino, novo_item):
    final = destino / "ACME - FORNECEDOR - BOLETO.pdf"
    final.write_bytes(b"%PDF conteudo A")
    item = novo_item(b"%PDF conteudo A")
    enviar_anexos([item], registro, Rclone(":local"), LOG)
    assert sorted(p.name for p in destino.iterdir()) == ["ACME - FORNECEDOR - BOLETO.pdf"]
    assert _estado(registro, item).estado == "enviado"


def test_conteudo_diferente_recebe_sufixo_e_preserva_o_original(registro, destino, novo_item):
    original = destino / "ACME - FORNECEDOR - BOLETO.pdf"
    original.write_bytes(b"%PDF original da equipe")
    item = novo_item(b"%PDF outro boleto")
    enviar_anexos([item], registro, Rclone(":local"), LOG)
    assert original.read_bytes() == b"%PDF original da equipe"
    assert (destino / "ACME - FORNECEDOR - BOLETO_2.pdf").read_bytes() == b"%PDF outro boleto"


def test_dois_anexos_de_mesmo_nome_na_mesma_execucao(registro, destino, novo_item):
    a, b = novo_item(b"%PDF A"), novo_item(b"%PDF B")
    enviar_anexos([a, b], registro, Rclone(":local"), LOG)
    assert sorted(p.name for p in destino.iterdir()) == [
        "ACME - FORNECEDOR - BOLETO.pdf", "ACME - FORNECEDOR - BOLETO_2.pdf",
    ]


def test_destino_inexistente_nao_e_criado(registro, destino, novo_item, tmp_path):
    ausente = tmp_path / "onedrive" / "PASTA RENOMEADA"
    item = novo_item(b"%PDF A", pasta_destino=ausente)
    resultado = enviar_anexos([item], registro, Rclone(":local"), LOG)
    assert not ausente.exists()
    assert _estado(registro, item).estado == "falha-envio"
    assert [f.causa for f in resultado.falhas] == ["onedrive:destino"]


def test_remote_invalido_suspende_os_demais_envios(registro, novo_item):
    itens = [novo_item(b"%PDF A"), novo_item(b"%PDF B")]
    resultado = enviar_anexos(itens, registro, Rclone("remote-inexistente-teste"), LOG)
    assert [f.causa for f in resultado.falhas] == ["config:RCLONE_REMOTE"]
    assert all(_estado(registro, i).estado == "falha-envio" for i in itens)


def test_aviso_apos_cinco_tentativas(registro, novo_item, tmp_path):
    item = novo_item(b"%PDF A", pasta_destino=tmp_path / "nao-existe")
    for _ in range(TENTATIVAS_PARA_AVISO - 1):
        resultado = enviar_anexos([item], registro, Rclone(":local"), LOG)
        assert not any(f.causa.startswith("anexo:") for f in resultado.falhas)
    resultado = enviar_anexos([item], registro, Rclone(":local"), LOG)
    assert any(f.causa == f"anexo:{item.sha256}:tentativas" for f in resultado.falhas)


def test_simulacao_nao_envia_nem_altera_registro(registro, destino, novo_item):
    item = novo_item(b"%PDF A")
    resultado = enviar_anexos([item], registro, Rclone(":local"), LOG, simulacao=True)
    assert list(destino.iterdir()) == []
    assert _estado(registro, item).estado == "extraido"
    assert resultado.simulados == 1


def test_resultado_de_quem_chama_e_preenchido_a_cada_envio(registro, destino, novo_item):
    """BUG-20260922-RWDA: o chamador mantém a referência ao acumulador, e não só o retorno."""
    meu = ResultadoEnvio()
    devolvido = enviar_anexos([novo_item(b"%PDF A"), novo_item(b"%PDF B")], registro, Rclone(":local"), LOG,
                              resultado=meu)
    assert devolvido is meu
    assert meu.enviados == 2


def test_testar_onedrive(destino):
    ok, mensagem = teste_onedrive.testar_onedrive(Rclone(":local"), str(destino))
    assert ok, mensagem
    assert mensagem == f"OneDrive: escrita confirmada em {destino}"
    assert list(destino.iterdir()) == []


def test_testar_onedrive_destino_ausente(tmp_path):
    ok, mensagem = teste_onedrive.testar_onedrive(Rclone(":local"), str(tmp_path / "nao-existe"))
    assert not ok
    assert "destino não encontrado" in mensagem


# Destino por vencimento (feature 003, cartão 2)

def _grade(destino, *folhas: tuple[int, int]):
    for dia, mes in folhas:
        (destino / PASTA_VENCIMENTOS / f"DIA {dia}" / f"202X-{mes:02d}").mkdir(parents=True)


def test_nota_em_xml_vai_para_a_pasta_do_vencimento(registro, destino, novo_item):
    _grade(destino, (10, 10))
    item = novo_item(nfe_com_vencimentos("2026-10-10"), nome="nota.xml", classe="nfe-xml")
    enviar_anexos([item], registro, Rclone(":local"), LOG)
    pasta = destino / PASTA_VENCIMENTOS / "DIA 10" / "202X-10"
    assert [p.name for p in pasta.iterdir()] == ["ACME - FORNECEDOR FICTICIO LTDA NF 1234 - REF.xml"]
    assert _estado(registro, item).caminho_destino.startswith(f"{pasta}/")


def test_nota_parcelada_vai_so_para_o_primeiro_vencimento(registro, destino, novo_item):
    _grade(destino, (10, 10), (10, 11), (10, 12))
    item = novo_item(nfe_com_vencimentos("2026-11-10", "2026-10-10", "2026-12-10"), nome="nota.xml", classe="nfe-xml")
    enviar_anexos([item], registro, Rclone(":local"), LOG)
    arquivos = sorted(p.relative_to(destino).as_posix() for p in destino.rglob("*") if p.is_file())
    assert arquivos == [f"{PASTA_VENCIMENTOS}/DIA 10/202X-10/ACME - FORNECEDOR FICTICIO LTDA NF 1234 - REF.xml"]


def test_danfe_herda_o_vencimento_do_xml_da_mensagem_e_boleto_usa_o_proprio(registro, destino, novo_item):
    _grade(destino, (10, 10), (10, 11))
    danfe = novo_item(pdf_com_texto("DANFE"), nome="danfe.pdf", vencimento_mensagem=date(2026, 10, 10))
    boleto = novo_item(pdf_com_texto(linha_digitavel(date(2026, 11, 10))), nome="boleto parcela 2.pdf",
                       vencimento_mensagem=date(2026, 10, 10))
    enviar_anexos([danfe, boleto], registro, Rclone(":local"), LOG)
    assert _estado(registro, danfe).caminho_destino.startswith(f"{destino}/{PASTA_VENCIMENTOS}/DIA 10/202X-10/")
    assert _estado(registro, boleto).caminho_destino.startswith(f"{destino}/{PASTA_VENCIMENTOS}/DIA 10/202X-11/")


def test_pdf_sem_vencimento_fica_na_raiz(registro, destino, novo_item):
    _grade(destino, (10, 10))
    item = novo_item(pdf_com_texto("Nota de servico sem data"), nome="nota.pdf")
    enviar_anexos([item], registro, Rclone(":local"), LOG)
    assert _estado(registro, item).caminho_destino == f"{destino}/ACME - FORNECEDOR - BOLETO.pdf"


def test_pasta_do_vencimento_ausente_nao_e_criada(registro, destino, novo_item):
    item = novo_item(pdf_com_texto("Vencimento: 05/11/2026"), nome="boleto.pdf")
    resultado = enviar_anexos([item], registro, Rclone(":local"), LOG)
    assert not (destino / PASTA_VENCIMENTOS).exists()
    assert _estado(registro, item).estado != "enviado"
    assert [f.causa for f in resultado.falhas] == ["onedrive:destino"]
