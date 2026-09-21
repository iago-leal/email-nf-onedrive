"""Subcomando `autorizar-caixa` com navegador simulado (feature 002, RF-04 a RF-06, D-02 a D-04, D-12)."""

from __future__ import annotations

import json
import os
import stat
import threading
import urllib.error
import urllib.request
from urllib.parse import parse_qs, urlencode, urlsplit

import pytest

from .conftest import CLIENT_ID, CLIENT_SECRET, gravar_autorizacao

pytestmark = pytest.mark.integracao

CAIXA_2 = "fiscal@cliente.example"
DURAVEL = "1//autorizacao-duravel-nova"


class Navegador:
    """Faz o papel do operador: recebe o endereço impresso e devolve o retorno ao endereço de laço local."""

    def __init__(self, **retorno: str) -> None:
        self.retorno = retorno  # parâmetros do retorno; `state` é preenchido com o recebido, salvo se informado
        self.parametros: dict[str, str] = {}
        self.antes: list[str] = []  # caminhos pedidos antes do retorno (ex.: /favicon.ico)
        self.pagina = ""
        self.linha: threading.Thread | None = None

    def __call__(self, endereco: str) -> None:
        self.parametros = {k: v[0] for k, v in parse_qs(urlsplit(endereco).query).items()}
        self.linha = threading.Thread(target=self._visitar, daemon=True)
        self.linha.start()

    def _visitar(self) -> None:
        base = self.parametros["redirect_uri"]
        for caminho in self.antes:
            try:
                urllib.request.urlopen(base + caminho, timeout=5).read()
            except urllib.error.HTTPError:
                pass
        consulta = {"state": self.parametros["state"], **self.retorno}
        with urllib.request.urlopen(f"{base}/?{urlencode(consulta)}", timeout=5) as resposta:
            self.pagina = resposta.read().decode()


@pytest.fixture
def cenario(cenario_oauth):
    cenario_oauth.caixa_oauth(2, CAIXA_2, autorizada=False)
    return cenario_oauth


def _arquivo(cenario):
    return cenario.dir_autorizacoes / f"{CAIXA_2}.json"


def _nada_gravado(cenario) -> bool:
    return not cenario.dir_autorizacoes.exists() or list(cenario.dir_autorizacoes.iterdir()) == []


def test_sucesso_grava_a_autorizacao_e_sai_com_0(cenario, capsys):
    cenario.servico.programar_troca("codigo-1", email=CAIXA_2, refresh_token=DURAVEL)
    cenario.navegador = Navegador(code="codigo-1")

    assert cenario.executar("autorizar-caixa", "2") == 0

    conteudo = json.loads(_arquivo(cenario).read_text(encoding="utf-8"))
    assert conteudo["versao"] == 1
    assert (conteudo["endereco"], conteudo["client_id"], conteudo["refresh_token"]) == (CAIXA_2, CLIENT_ID, DURAVEL)
    assert "https://mail.google.com/" in conteudo["escopos"]
    assert stat.S_IMODE(os.stat(_arquivo(cenario)).st_mode) == 0o600
    assert stat.S_IMODE(os.stat(cenario.dir_autorizacoes).st_mode) == 0o700

    saida = capsys.readouterr().out
    assert f"caixa 2: abra o endereço abaixo numa janela anônima e entre com {CAIXA_2}" in saida
    assert f"{cenario.servico.base}/auth?" in saida
    assert "aguardando o consentimento" in saida
    assert f"caixa 2: autorizada · {CAIXA_2}" in saida
    assert f"arquivo: {_arquivo(cenario)} (permissão 600)" in saida
    for segredo in (CLIENT_SECRET, DURAVEL, "codigo-1", "ya29.troca"):
        assert segredo not in saida


def test_pedido_de_consentimento_e_troca_seguem_o_contrato(cenario):
    cenario.servico.programar_troca("codigo-1", email=CAIXA_2)
    cenario.navegador = Navegador(code="codigo-1")
    assert cenario.executar("autorizar-caixa", "2") == 0
    pedido = cenario.navegador.parametros
    assert pedido["redirect_uri"].startswith("http://127.0.0.1:")
    assert (pedido["login_hint"], pedido["access_type"], pedido["prompt"]) == (CAIXA_2, "offline", "consent")
    assert pedido["code_challenge_method"] == "S256"
    rota, troca = cenario.servico.requisicoes[0]
    assert rota == "/token" and troca["redirect_uri"] == pedido["redirect_uri"]
    assert troca["code_verifier"] and troca["code_verifier"] != pedido["code_challenge"]


def test_pagina_de_retorno_e_estatica_e_favicon_nao_consome_o_retorno(cenario):
    cenario.servico.programar_troca("codigo-<script>", email=CAIXA_2)
    cenario.navegador = Navegador(code="codigo-<script>")
    cenario.navegador.antes = ["/favicon.ico"]
    assert cenario.executar("autorizar-caixa", "2") == 0
    cenario.navegador.linha.join(5)
    assert "pode fechar esta janela" in cenario.navegador.pagina
    assert "script" not in cenario.navegador.pagina


def test_nao_usa_trava_registro_nem_aviso(cenario):
    cenario.servico.programar_troca("codigo-1", email=CAIXA_2)
    cenario.navegador = Navegador(code="codigo-1")
    assert cenario.executar("autorizar-caixa", "2") == 0
    assert not (cenario.home / "var" / "registro.sqlite3").exists()
    assert not (cenario.home / "var" / "execucao.lock").exists()
    assert cenario.transporte.enviadas == []
    assert cenario.servidor.comandos == []  # o comando não fala com o IMAP


def test_conta_com_maiusculas_diferentes_e_a_mesma_conta(cenario):
    cenario.servico.programar_troca("codigo-1", email=CAIXA_2.upper())
    cenario.navegador = Navegador(code="codigo-1")
    assert cenario.executar("autorizar-caixa", "2") == 0
    assert cenario.servico.revogados == []


def test_reautorizacao_substitui_a_anterior(cenario):
    gravar_autorizacao(cenario.dir_autorizacoes, CAIXA_2, "1//antiga")
    cenario.servico.programar_troca("codigo-1", email=CAIXA_2, refresh_token=DURAVEL)
    cenario.navegador = Navegador(code="codigo-1")
    assert cenario.executar("autorizar-caixa", "2") == 0
    assert json.loads(_arquivo(cenario).read_text(encoding="utf-8"))["refresh_token"] == DURAVEL
    assert [p.name for p in cenario.dir_autorizacoes.iterdir()] == [f"{CAIXA_2}.json"]


# --- recusas: código 2 e nada gravado ----------------------------------------------------------

def test_caixa_inexistente(cenario, capsys):
    assert cenario.executar("autorizar-caixa", "7") == 2
    assert "caixa 7 não existe no .env" in capsys.readouterr().err
    assert cenario.servico.requisicoes == []


def test_caixa_em_modo_senha(cenario, capsys):
    assert cenario.executar("autorizar-caixa", "1") == 2
    assert "caixa 1 não está em modo oauth (defina AUTH_EMAIL1=oauth)" in capsys.readouterr().err


def test_credenciais_do_cliente_ausentes(cenario, capsys):
    del cenario.env["OAUTH_CLIENT_ID"]
    assert cenario.executar("autorizar-caixa", "2") == 2
    assert "credenciais do cliente OAuth ausentes" in capsys.readouterr().err
    assert cenario.servico.requisicoes == []


def test_erro_global_de_configuracao(cenario, capsys):
    del cenario.env["RCLONE_REMOTE"]
    assert cenario.executar("autorizar-caixa", "2") == 2
    assert "RCLONE_REMOTE ausente" in capsys.readouterr().err


def test_consentimento_negado(cenario, capsys):
    cenario.navegador = Navegador(error="access_denied")
    assert cenario.executar("autorizar-caixa", "2") == 2
    assert "caixa 2: consentimento negado" in capsys.readouterr().err
    assert cenario.servico.requisicoes == [] and _nada_gravado(cenario)


def test_state_divergente(cenario, capsys):
    cenario.navegador = Navegador(code="codigo-1", state="forjado")
    assert cenario.executar("autorizar-caixa", "2") == 2
    assert "caixa 2: retorno inválido (state)" in capsys.readouterr().err
    assert cenario.servico.requisicoes == [] and _nada_gravado(cenario)


def test_tempo_esgotado(cenario, capsys):
    cenario.espera_consentimento_s = 0.3
    assert cenario.executar("autorizar-caixa", "2") == 2
    assert "caixa 2: tempo esgotado à espera do consentimento" in capsys.readouterr().err
    assert _nada_gravado(cenario)


def test_sem_autorizacao_duravel(cenario, capsys):
    cenario.servico.programar_troca("codigo-1", email=CAIXA_2, refresh_token=None)
    cenario.navegador = Navegador(code="codigo-1")
    assert cenario.executar("autorizar-caixa", "2") == 2
    assert "caixa 2: o Google não devolveu autorização durável" in capsys.readouterr().err
    assert _nada_gravado(cenario)


def test_acesso_ao_correio_nao_concedido(cenario, capsys):
    cenario.servico.programar_troca("codigo-1", email=CAIXA_2, scope="openid email")
    cenario.navegador = Navegador(code="codigo-1")
    assert cenario.executar("autorizar-caixa", "2") == 2
    assert "caixa 2: acesso ao correio não concedido" in capsys.readouterr().err
    assert _nada_gravado(cenario)


@pytest.mark.parametrize("email, verificado", [(None, True), (CAIXA_2, False)])
def test_conta_nao_identificada(cenario, capsys, email, verificado):
    cenario.servico.programar_troca("codigo-1", email=email, verificado=verificado, refresh_token=DURAVEL)
    cenario.navegador = Navegador(code="codigo-1")
    assert cenario.executar("autorizar-caixa", "2") == 2
    assert "caixa 2: o Google não informou a conta que consentiu" in capsys.readouterr().err
    assert cenario.servico.revogados == [DURAVEL] and _nada_gravado(cenario)


def test_conta_divergente_revoga_e_nada_grava(cenario, capsys):
    gravar_autorizacao(cenario.dir_autorizacoes, CAIXA_2, "1//antiga")
    cenario.servico.programar_troca("codigo-1", email="operador@pessoal.example", refresh_token=DURAVEL)
    cenario.navegador = Navegador(code="codigo-1")
    assert cenario.executar("autorizar-caixa", "2") == 2
    erro = capsys.readouterr().err
    assert "conta autorizada difere de EMAIL2" in erro
    assert "não foi possível revogar" not in erro
    assert cenario.servico.revogados == [DURAVEL]
    assert json.loads(_arquivo(cenario).read_text(encoding="utf-8"))["refresh_token"] == "1//antiga"


def test_conta_divergente_com_revogacao_indisponivel(cenario, capsys):
    cenario.servico.revogacao_disponivel = False
    cenario.servico.programar_troca("codigo-1", email="operador@pessoal.example", refresh_token=DURAVEL)
    cenario.navegador = Navegador(code="codigo-1")
    assert cenario.executar("autorizar-caixa", "2") == 2
    erro = capsys.readouterr().err
    assert "conta autorizada difere de EMAIL2" in erro
    assert "não foi possível revogar; revogue em myaccount.google.com/permissions" in erro
    assert DURAVEL not in erro and _nada_gravado(cenario)


def test_troca_do_codigo_recusada(cenario, capsys):
    cenario.navegador = Navegador(code="codigo-que-o-servico-desconhece")
    assert cenario.executar("autorizar-caixa", "2") == 2
    assert "caixa 2: troca do código recusada (invalid_grant)" in capsys.readouterr().err
    assert _nada_gravado(cenario)


def test_diretorio_de_autorizacoes_configuravel(cenario, tmp_path_factory):
    destino = tmp_path_factory.mktemp("cofre") / "oauth"
    cenario.env["DIR_AUTORIZACOES"] = str(destino)
    cenario.servico.programar_troca("codigo-1", email=CAIXA_2, refresh_token=DURAVEL)
    cenario.navegador = Navegador(code="codigo-1")
    assert cenario.executar("autorizar-caixa", "2") == 0
    assert (destino / f"{CAIXA_2}.json").is_file()
    assert _nada_gravado(cenario)  # nada no diretório padrão
