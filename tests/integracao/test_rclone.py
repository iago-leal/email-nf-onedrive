"""Integração da fachada com o Rclone real, contra um diretório local (D-18, T034)."""

from __future__ import annotations

import shutil
import uuid

import pytest

from email_nf_onedrive.envio.rclone import ErroRclone, Rclone, SubcomandoProibido

pytestmark = [
    pytest.mark.integracao,
    pytest.mark.skipif(shutil.which("rclone") is None, reason="rclone não instalado"),
]


@pytest.fixture
def destino(tmp_path):
    pasta = tmp_path / "onedrive" / "CONTAS A PAGAR"
    pasta.mkdir(parents=True)
    return pasta


@pytest.fixture
def rclone():
    return Rclone(":local")


@pytest.fixture
def arquivo(tmp_path):
    caminho = tmp_path / "local.pdf"
    caminho.write_bytes(b"%PDF-1.4 conteudo A\n")
    return caminho


def test_estatistica_de_arquivo_ausente(rclone, destino):
    assert rclone.estatistica(f"{destino}/nao-existe.pdf") is None


def test_estatistica_em_pasta_ausente(rclone, destino):
    assert rclone.estatistica(f"{destino}/sub/nao-existe.pdf") is None


def test_copiar_e_consultar(rclone, destino, arquivo):
    rclone.copiar(arquivo, f"{destino}/novo.pdf")
    objeto = rclone.estatistica(f"{destino}/novo.pdf")
    assert objeto.tamanho == arquivo.stat().st_size
    assert objeto.quickxor == rclone.hash_local(arquivo)
    assert (destino / "novo.pdf").read_bytes() == arquivo.read_bytes()


def test_nome_com_espaco_e_acento(rclone, destino, arquivo):
    rclone.copiar(arquivo, f"{destino}/2026-09-18_cobranca_Boleto Setembro nº 1.pdf")
    assert (destino / "2026-09-18_cobranca_Boleto Setembro nº 1.pdf").exists()


def test_copiar_nunca_sobrescreve(rclone, destino, arquivo, tmp_path):
    existente = destino / "boleto.pdf"
    existente.write_bytes(b"conteudo original que nao pode sumir")
    rclone.copiar(arquivo, f"{destino}/boleto.pdf")
    assert existente.read_bytes() == b"conteudo original que nao pode sumir"


def test_hash_local_distingue_conteudos(rclone, arquivo, tmp_path):
    outro = tmp_path / "outro.pdf"
    outro.write_bytes(b"%PDF-1.4 conteudo B\n")
    assert rclone.hash_local(arquivo) != rclone.hash_local(outro)


def test_listar_e_pasta_existe(rclone, destino, arquivo):
    rclone.copiar(arquivo, f"{destino}/a.pdf")
    assert rclone.listar(str(destino)) == ["a.pdf"]
    assert rclone.pasta_existe(str(destino))
    assert not rclone.pasta_existe(f"{destino}/nao-existe")


@pytest.mark.parametrize("subcomando", ["sync", "delete", "purge", "move", "moveto", "rmdir", "copy"])
def test_subcomandos_fora_da_lista_sao_recusados(rclone, subcomando):
    with pytest.raises(SubcomandoProibido):
        rclone._executar(subcomando, "a", "b")


def test_deletefile_so_no_arquivo_de_teste(rclone, destino, arquivo):
    rclone.copiar(arquivo, f"{destino}/boleto.pdf")
    with pytest.raises(SubcomandoProibido):
        rclone.apagar_arquivo_de_teste(f"{destino}/boleto.pdf")
    assert (destino / "boleto.pdf").exists()

    nome_teste = f".email-nf-onedrive-teste-{uuid.uuid4()}.txt"
    rclone.copiar(arquivo, f"{destino}/{nome_teste}")
    rclone.apagar_arquivo_de_teste(f"{destino}/{nome_teste}")
    assert not (destino / nome_teste).exists()


def test_remote_inexistente_vira_erro_de_config(arquivo, destino):
    rclone = Rclone("remote-que-nao-existe-no-rclone-conf")
    with pytest.raises(ErroRclone) as erro:
        rclone.copiar(arquivo, "CONTAS A PAGAR/x.pdf")
    assert erro.value.causa == "config"


def test_executavel_ausente(arquivo):
    rclone = Rclone(":local", binario="/caminho/que/nao/existe/rclone")
    with pytest.raises(ErroRclone) as erro:
        rclone.hash_local(arquivo)
    assert erro.value.causa == "config"
