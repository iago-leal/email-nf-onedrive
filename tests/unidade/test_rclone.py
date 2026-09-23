"""Limite de tempo por chamada ao Rclone (RNF-03, adendo 005)."""

from __future__ import annotations

import subprocess

import pytest

from email_nf_onedrive.envio.rclone import TEMPO, TIMEOUT_S, ErroRclone, Rclone


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
