"""Arquivo de autorização por caixa (feature 002, D-05, data-delta.md §4, RF-05, RF-12)."""

from __future__ import annotations

import json
import os
import stat
from datetime import datetime, timezone

import pytest

from email_nf_onedrive import segredos
from email_nf_onedrive.autorizacao import arquivo
from email_nf_onedrive.autorizacao.arquivo import Autorizacao, ErroArquivoAutorizacao

ENDERECO = "Financeiro@Empresa.example"
CLIENTE = "id-do-cliente.apps.example"
ESCOPOS = ("https://mail.google.com/", "openid", "email")


def _autorizacao(**campos) -> Autorizacao:
    base = dict(endereco=ENDERECO, client_id=CLIENTE, refresh_token="1//autorizacao-duravel", escopos=ESCOPOS,
                autorizada_em=datetime(2026, 9, 21, 18, 40, 11, tzinfo=timezone.utc))
    return Autorizacao(**{**base, **campos})


def _modo(caminho) -> int:
    return stat.S_IMODE(os.stat(caminho).st_mode)


def _regravar(caminho, **campos) -> None:
    conteudo = json.loads(caminho.read_text(encoding="utf-8"))
    conteudo.update(campos)
    caminho.write_text(json.dumps(conteudo), encoding="utf-8")


def test_nome_do_arquivo_e_o_endereco_em_minusculas(tmp_path):
    assert arquivo.caminho(tmp_path, ENDERECO) == tmp_path / "financeiro@empresa.example.json"


@pytest.mark.parametrize("endereco", ["../a@b.example", "a/b@c.example", "a\\b@c.example", "a\0@b.example", ""])
def test_endereco_que_nao_pode_nomear_arquivo(endereco):
    assert not arquivo.nome_seguro(endereco)
    assert arquivo.nome_seguro(ENDERECO)


def test_grava_com_600_em_diretorio_700_criado_sob_demanda(tmp_path):
    diretorio = tmp_path / "autorizacoes"
    destino = arquivo.gravar(diretorio, _autorizacao())
    assert destino == diretorio / "financeiro@empresa.example.json"
    assert _modo(diretorio) == 0o700
    assert _modo(destino) == 0o600
    conteudo = json.loads(destino.read_text(encoding="utf-8"))
    assert conteudo == {
        "versao": 1, "endereco": ENDERECO, "client_id": CLIENTE, "refresh_token": "1//autorizacao-duravel",
        "escopos": list(ESCOPOS), "autorizada_em": "2026-09-21T18:40:11+00:00",
    }


def test_regravacao_substitui_sem_deixar_residuo(tmp_path):
    arquivo.gravar(tmp_path, _autorizacao())
    arquivo.gravar(tmp_path, _autorizacao(refresh_token="1//segunda"))
    assert [p.name for p in tmp_path.iterdir()] == ["financeiro@empresa.example.json"]
    assert arquivo.ler(tmp_path, ENDERECO, CLIENTE).refresh_token == "1//segunda"


def test_leitura_devolve_a_autorizacao_e_registra_o_segredo(tmp_path):
    arquivo.gravar(tmp_path, _autorizacao())
    segredos.limpar()
    lida = arquivo.ler(tmp_path, ENDERECO.upper(), CLIENTE)  # o endereço é comparado sem diferenciar maiúsculas
    assert lida.refresh_token == "1//autorizacao-duravel"
    assert lida.escopos == ESCOPOS
    assert "1//autorizacao-duravel" not in repr(lida)
    assert segredos.mascarar("x 1//autorizacao-duravel") == "x ****"


def test_arquivo_ausente(tmp_path):
    with pytest.raises(ErroArquivoAutorizacao) as erro:
        arquivo.ler(tmp_path / "nao-existe", ENDERECO, CLIENTE)
    assert erro.value.ausente
    assert erro.value.motivo == "sem autorização"


@pytest.mark.parametrize("campos, motivo", [
    ({"versao": 2}, "autorização ilegível"),
    ({"endereco": "outra@empresa.example"}, "autorização de outro endereço"),
    ({"client_id": "outro-cliente"}, "autorização emitida para outro cliente OAuth"),
    ({"refresh_token": ""}, "autorização ilegível"),
    ({"refresh_token": 123}, "autorização ilegível"),
    ({"escopos": ["openid", "email"]}, "autorização ilegível"),
    ({"escopos": "https://mail.google.com/"}, "autorização ilegível"),
])
def test_recusas_de_leitura(tmp_path, campos, motivo):
    destino = arquivo.gravar(tmp_path, _autorizacao())
    _regravar(destino, **campos)
    with pytest.raises(ErroArquivoAutorizacao) as erro:
        arquivo.ler(tmp_path, ENDERECO, CLIENTE)
    assert not erro.value.ausente
    assert erro.value.motivo == motivo


@pytest.mark.parametrize("conteudo", ["", "isto não é json", "[1, 2]", "null"])
def test_json_ilegivel(tmp_path, conteudo):
    arquivo.caminho(tmp_path, ENDERECO).write_text(conteudo, encoding="utf-8")
    with pytest.raises(ErroArquivoAutorizacao) as erro:
        arquivo.ler(tmp_path, ENDERECO, CLIENTE)
    assert erro.value.motivo == "autorização ilegível"


def test_data_informativa_invalida_nao_impede_a_leitura(tmp_path):
    destino = arquivo.gravar(tmp_path, _autorizacao())
    _regravar(destino, autorizada_em="ontem")
    assert arquivo.ler(tmp_path, ENDERECO, CLIENTE).autorizada_em is None


def test_estado_por_stat_sem_abrir_o_arquivo(tmp_path):
    assert not arquivo.existe_e_legivel(tmp_path, ENDERECO)
    arquivo.caminho(tmp_path, ENDERECO).write_text("lixo que ninguém lê", encoding="utf-8")
    assert arquivo.existe_e_legivel(tmp_path, ENDERECO)
    arquivo.caminho(tmp_path, "pasta@empresa.example").mkdir()
    assert not arquivo.existe_e_legivel(tmp_path, "pasta@empresa.example")
