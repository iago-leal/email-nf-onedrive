"""Testes da trava de execução e do limite de duração (EM RF-03, RF-04, D-14)."""

from __future__ import annotations

import os
import time

import pytest

from email_nf_onedrive.execucao.trava import TempoEsgotado, Trava, TravaOcupada, limite_duracao

PID_INEXISTENTE = 2**22 + 12345


@pytest.fixture
def caminho(home):
    return home / "var" / "execucao.lock"


def _gravar_trava(caminho, pid: int, instante: float) -> None:
    caminho.write_text(f"{pid}\n{instante}\n", encoding="utf-8")


def test_adquire_e_libera(caminho):
    trava = Trava(caminho)
    assert trava.adquirir() is False  # não havia trava abandonada
    conteudo = caminho.read_text().split()
    assert int(conteudo[0]) == os.getpid()
    trava.liberar()
    assert not caminho.exists()


def test_segunda_aquisicao_e_recusada(caminho):
    with Trava(caminho):
        with pytest.raises(TravaOcupada):
            Trava(caminho).adquirir()


def test_trava_antiga_e_considerada_abandonada(caminho):
    agora = time.time()
    _gravar_trava(caminho, os.getpid(), agora - 30 * 60)
    trava = Trava(caminho, agora=lambda: agora)
    assert trava.adquirir() is True
    assert int(caminho.read_text().split()[0]) == os.getpid()
    trava.liberar()


def test_trava_recente_de_processo_vivo_e_respeitada(caminho):
    agora = time.time()
    _gravar_trava(caminho, os.getpid(), agora - 10 * 60)
    with pytest.raises(TravaOcupada):
        Trava(caminho, agora=lambda: agora).adquirir()


def test_trava_de_processo_morto_e_retomada(caminho):
    agora = time.time()
    _gravar_trava(caminho, PID_INEXISTENTE, agora - 60)
    trava = Trava(caminho, agora=lambda: agora)
    assert trava.adquirir() is True
    trava.liberar()


def test_trava_ilegivel_e_considerada_abandonada(caminho):
    caminho.write_text("lixo", encoding="utf-8")
    trava = Trava(caminho)
    assert trava.adquirir() is True
    trava.liberar()


def test_contexto_libera_mesmo_com_excecao(caminho):
    with pytest.raises(RuntimeError):
        with Trava(caminho):
            raise RuntimeError("falha")
    assert not caminho.exists()


def test_trava_com_permissao_600(caminho):
    with Trava(caminho):
        assert oct(os.stat(caminho).st_mode & 0o777) == oct(0o600)


def test_limite_de_duracao_interrompe():
    with pytest.raises(TempoEsgotado):
        with limite_duracao(1):
            time.sleep(3)


def test_limite_de_duracao_nao_interfere_quando_cumprido():
    with limite_duracao(5):
        pass
    time.sleep(0.1)  # o alarme foi cancelado; nada deve disparar depois
