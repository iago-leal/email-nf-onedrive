"""Subcomandos `testar-caixa` e `verificar-config` (feature 002, RF-10, RF-11, D-11)."""

from __future__ import annotations

import pytest

from .conftest import CAIXA_1, CLIENT_SECRET

pytestmark = pytest.mark.integracao

CAIXA_2 = "fiscal@cliente.example"
CAIXA_3 = "compras@cliente.example"
CAIXA_4 = "rh@cliente.example"


def _sem_efeitos_colaterais(cenario) -> bool:
    return (not (cenario.home / "var" / "registro.sqlite3").exists()
            and not (cenario.home / "var" / "execucao.lock").exists()
            and cenario.transporte.enviadas == [])


# --- testar-caixa -------------------------------------------------------------------------------

def test_todas_as_caixas_confirmadas(cenario_oauth, capsys):
    cenario = cenario_oauth
    cenario.caixa_oauth(2, CAIXA_2)
    cenario.entregar("boleto_simples.eml")
    assert cenario.executar("testar-caixa") == 0
    assert capsys.readouterr().out.splitlines() == ["caixa 1: acesso confirmado (senha)",
                                                    "caixa 2: acesso confirmado (oauth)"]
    nomes = [c[0] for c in cenario.servidor.comandos]
    assert nomes == ["CONNECT", "LOGIN", "EXAMINE", "LOGOUT", "CONNECT", "AUTHENTICATE", "EXAMINE", "LOGOUT"]
    assert _sem_efeitos_colaterais(cenario)


def test_uma_linha_por_desfecho_e_codigo_1(cenario_oauth, capsys):
    cenario = cenario_oauth
    cenario.caixa_oauth(2, CAIXA_2, autorizada=False)
    cenario.caixa_oauth(3, CAIXA_3, resposta="invalid_grant")
    cenario.caixa_oauth(4, CAIXA_4, resposta="503")
    cenario.servidor.adicionar_caixa("senha@cliente.example", "certa")
    cenario.env.update({"EMAIL5": "senha@cliente.example", "SENHA_EMAIL5": "errada", "IMAP_HOST_EMAIL5": "imap5.example",
                        "EMAIL6": "sem-senha@cliente.example"})
    assert cenario.executar("testar-caixa") == 1
    saida = capsys.readouterr()
    assert (saida.out + saida.err).splitlines() == [
        "caixa 1: acesso confirmado (senha)",
        "caixa 2: falhou (sem autorização)",
        "caixa 3: falhou (autorização recusada; rode autorizar-caixa 3)",
        "caixa 4: falhou (serviço de autorização indisponível)",
        "caixa 5: falhou (autenticação recusada)",
        "caixa 6: falhou (SENHA_EMAIL6 ausente)",
    ]
    assert cenario.servico.contagem("/token") == 2  # uma tentativa por caixa com arquivo
    assert [c for c in cenario.servidor.comandos if c[0] == "LOGIN"] == [("LOGIN", CAIXA_1), ("LOGIN", "senha@cliente.example")]
    assert _sem_efeitos_colaterais(cenario)


def test_so_a_caixa_pedida(cenario_oauth, capsys):
    cenario = cenario_oauth
    cenario.caixa_oauth(2, CAIXA_2)
    assert cenario.executar("testar-caixa", "2") == 0
    assert capsys.readouterr().out.splitlines() == ["caixa 2: acesso confirmado (oauth)"]
    assert "LOGIN" not in cenario.servidor.nomes_de_comandos()


def test_pasta_inexistente_e_falha(cenario_oauth, capsys):
    cenario = cenario_oauth
    cenario.env["PASTA_EMAIL1"] = "Fiscal"
    assert cenario.executar("testar-caixa") == 1
    saida = capsys.readouterr()
    assert "caixa 1: falhou (pasta 'Fiscal' inexistente)" in saida.out + saida.err


def test_authenticate_recusado_e_servidor_fora_do_ar(cenario_oauth, capsys):
    cenario = cenario_oauth
    cenario.caixa_oauth(2, CAIXA_2)
    cenario.servidor.credenciais_oauth[CAIXA_2] = "ya29.outra"
    cenario.servidor.fora_do_ar.add("imap1.example")
    assert cenario.executar("testar-caixa") == 1
    saida = capsys.readouterr()
    linhas = (saida.out + saida.err).splitlines()
    assert linhas[0].startswith("caixa 1: falhou (servidor IMAP inacessível")
    assert linhas[1] == "caixa 2: falhou (autorização recusada; rode autorizar-caixa 2)"


def test_cliente_recusado_pelo_google(cenario_oauth, capsys):
    cenario = cenario_oauth
    cenario.caixa_oauth(2, CAIXA_2, resposta="invalid_client")
    cenario.caixa_oauth(3, CAIXA_3)
    assert cenario.executar("testar-caixa") == 1
    saida = capsys.readouterr()
    assert (saida.out + saida.err).splitlines()[1:] == [
        "caixa 2: falhou (credenciais do cliente OAuth recusadas pelo Google)",
        "caixa 3: falhou (credenciais do cliente OAuth recusadas pelo Google)",
    ]
    assert cenario.servico.contagem("/token") == 1
    assert CLIENT_SECRET not in saida.out + saida.err


@pytest.mark.parametrize("argumentos, mensagem", [
    (("testar-caixa", "9"), "caixa 9 não existe no .env"),
])
def test_indice_inexistente_sai_com_2(cenario_oauth, capsys, argumentos, mensagem):
    assert cenario_oauth.executar(*argumentos) == 2
    assert mensagem in capsys.readouterr().err
    assert cenario_oauth.servidor.comandos == []


def test_configuracao_invalida_e_nenhuma_caixa_valida_saem_com_2(cenario_oauth, capsys):
    cenario = cenario_oauth
    del cenario.env["SENHA_EMAIL1"]
    assert cenario.executar("testar-caixa") == 2
    assert "nenhuma caixa válida no .env" in capsys.readouterr().err
    del cenario.env["DATA_INICIAL"]
    assert cenario.executar("testar-caixa") == 2
    assert "DATA_INICIAL ausente" in capsys.readouterr().err


# --- verificar-config ---------------------------------------------------------------------------

def test_verificar_config_mostra_o_modo_e_o_estado_da_autorizacao(cenario_oauth, capsys):
    cenario = cenario_oauth
    cenario.caixa_oauth(2, CAIXA_2)
    cenario.caixa_oauth(3, CAIXA_3, autorizada=False)
    assert cenario.executar("verificar-config") == 0
    linhas = capsys.readouterr().out.splitlines()
    assert linhas[0] == f"1 · {CAIXA_1} · INBOX · {cenario.destino} · empresa ACME · senha ****"
    assert linhas[1] == f"2 · {CAIXA_2} · INBOX · {cenario.destino} · empresa CLIENTE · oauth (autorizada)"
    assert linhas[2] == f"3 · {CAIXA_3} · INBOX · {cenario.destino} · empresa CLIENTE · oauth (sem autorização)"
    assert "cliente OAuth: configurado" in linhas
    assert f"diretório de autorizações: {cenario.dir_autorizacoes}" in linhas
    assert cenario.servico.requisicoes == [] and cenario.servidor.comandos == []  # RF-10: sem rede


def test_verificar_config_sem_oauth_fica_como_antes(cenario_oauth, capsys):
    cenario = cenario_oauth
    cenario.env.update({"OAUTH_CLIENT_ID": "id", "OAUTH_CLIENT_SECRET": "segredo-sem-uso"})
    assert cenario.executar("verificar-config") == 0
    saida = capsys.readouterr().out
    assert saida.splitlines()[0].endswith("· senha ****")
    assert "OAuth" not in saida and "autorizações" not in saida
