"""Integração do envio com o Rclone real contra diretório local (T036, EO RF-01 a RF-10)."""

from __future__ import annotations

import logging
import shutil
from datetime import datetime, timezone

import pytest

from email_nf_onedrive.coleta.coleta import AnexoParaEnvio
from email_nf_onedrive.configuracao.modelo import Caixa
from email_nf_onedrive.envio.envio import TENTATIVAS_PARA_AVISO, enviar_anexos
from email_nf_onedrive.envio.rclone import Rclone
from email_nf_onedrive.envio import teste_onedrive
from email_nf_onedrive.registro.banco import Registro

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

    def _novo(conteudo: bytes, nome="boleto.pdf", remetente="cobranca@fornecedor.example", pasta_destino=None):
        n = next(contador)
        caixa = Caixa(1, "financeiro@empresa.example", "s", "INBOX", "imap", str(pasta_destino or destino))
        anexo = registro.registrar_anexo(
            caixa_endereco=caixa.endereco, caixa_indice=1, message_id=f"<m{n}>", sha256=f"{n:064d}",
            nome_original=nome, remetente=remetente, assunto="Boleto", data_mensagem=RECEBIDO,
            classe="palavra-chave",
        )
        local = trabalho / f"{anexo.id}.pdf"
        local.write_bytes(conteudo)
        return AnexoParaEnvio(anexo.id, local, caixa, nome, remetente, RECEBIDO, anexo.sha256)

    return _novo


def _estado(registro, item):
    return registro.buscar(item.caixa.endereco, f"<m{item.anexo_id}>", item.sha256)


def test_envio_novo_confirma_registra_e_apaga_copia_local(registro, destino, novo_item):
    item = novo_item(b"%PDF conteudo A")
    resultado = enviar_anexos([item], registro, Rclone(":local"), LOG)
    final = destino / "2026-09-18_cobranca_boleto.pdf"
    assert final.read_bytes() == b"%PDF conteudo A"
    anexo = _estado(registro, item)
    assert anexo.estado == "enviado"
    assert anexo.caminho_destino == f"{destino}/2026-09-18_cobranca_boleto.pdf"
    assert not item.caminho_local.exists()
    assert resultado.enviados == 1 and resultado.falhas == []


def test_arquivo_identico_ja_presente_nao_e_reenviado(registro, destino, novo_item):
    final = destino / "2026-09-18_cobranca_boleto.pdf"
    final.write_bytes(b"%PDF conteudo A")
    item = novo_item(b"%PDF conteudo A")
    enviar_anexos([item], registro, Rclone(":local"), LOG)
    assert sorted(p.name for p in destino.iterdir()) == ["2026-09-18_cobranca_boleto.pdf"]
    assert _estado(registro, item).estado == "enviado"


def test_conteudo_diferente_recebe_sufixo_e_preserva_o_original(registro, destino, novo_item):
    original = destino / "2026-09-18_cobranca_boleto.pdf"
    original.write_bytes(b"%PDF original da equipe")
    item = novo_item(b"%PDF outro boleto")
    enviar_anexos([item], registro, Rclone(":local"), LOG)
    assert original.read_bytes() == b"%PDF original da equipe"
    assert (destino / "2026-09-18_cobranca_boleto_2.pdf").read_bytes() == b"%PDF outro boleto"


def test_dois_anexos_de_mesmo_nome_na_mesma_execucao(registro, destino, novo_item):
    a, b = novo_item(b"%PDF A"), novo_item(b"%PDF B")
    enviar_anexos([a, b], registro, Rclone(":local"), LOG)
    assert sorted(p.name for p in destino.iterdir()) == [
        "2026-09-18_cobranca_boleto.pdf", "2026-09-18_cobranca_boleto_2.pdf",
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


def test_testar_onedrive(destino):
    ok, mensagem = teste_onedrive.testar_onedrive(Rclone(":local"), str(destino))
    assert ok, mensagem
    assert mensagem == f"OneDrive: escrita confirmada em {destino}"
    assert list(destino.iterdir()) == []


def test_testar_onedrive_destino_ausente(tmp_path):
    ok, mensagem = teste_onedrive.testar_onedrive(Rclone(":local"), str(tmp_path / "nao-existe"))
    assert not ok
    assert "destino não encontrado" in mensagem
