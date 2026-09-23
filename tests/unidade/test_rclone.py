"""Limite de tempo por chamada ao Rclone (RNF-03, adendo 005) e sobrescrita restrita ao LEIAME (adendo 006)."""

from __future__ import annotations

import subprocess

import pytest

from email_nf_onedrive.envio.rclone import NOME_LEIAME, TEMPO, TIMEOUT_S, ErroRclone, Rclone, SubcomandoProibido


def test_limite_padrao_de_300_s_chega_ao_processo():
    chamadas = []

    def executor(comando, **opcoes):
        chamadas.append(opcoes["timeout"])
        return subprocess.CompletedProcess(comando, 0, stdout="", stderr="")

    Rclone("remoto", executor=executor).copiar("/tmp/a.pdf", "D/a.pdf")
    assert TIMEOUT_S == 300 and chamadas == [300]


def test_chamada_que_estoura_o_limite_vira_falha_de_tempo():
    def executor(comando, **opcoes):
        raise subprocess.TimeoutExpired(comando, opcoes["timeout"])

    with pytest.raises(ErroRclone) as erro:
        Rclone("remoto", executor=executor).copiar("/tmp/a.pdf", "D/a.pdf")
    assert erro.value.causa == TEMPO
    assert erro.value.detalhe == "rclone copyto passou de 300 s"


def test_so_o_leiame_e_publicado_sem_ignore_existing():
    chamadas = []

    def executor(comando, **_opcoes):
        chamadas.append(comando)
        return subprocess.CompletedProcess(comando, 0, stdout="", stderr="")

    rclone = Rclone("remoto", executor=executor)
    rclone.publicar_leiame("/tmp/l.xlsx", f"D/{NOME_LEIAME}")
    assert chamadas[0][1:4] == ["copyto", "/tmp/l.xlsx", f"remoto:D/{NOME_LEIAME}"]
    assert "--ignore-existing" not in chamadas[0]
    for invalido in ("D/ACME - FORNECEDOR - BOLETO.pdf", f"D/{NOME_LEIAME}.pdf", f"D/x{NOME_LEIAME}"):
        with pytest.raises(SubcomandoProibido):
            rclone.publicar_leiame("/tmp/l.xlsx", invalido)
    assert len(chamadas) == 1
