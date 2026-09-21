"""Testes de configuracao-caixas (CC RF-01 a RF-11, EC-01 a EC-08)."""

from __future__ import annotations

import os
from datetime import date

import pytest

from email_nf_onedrive import segredos
from email_nf_onedrive.configuracao.carregar import carregar_configuracao
from email_nf_onedrive.configuracao.modelo import ErroConfiguracao

GLOBAIS = {
    "RCLONE_REMOTE": "onedrive-financeiro",
    "DESTINO_ONEDRIVE": "Financeiro/CONTAS A PAGAR",
    "DATA_INICIAL": "2026-09-01",
    "TELEGRAM_BOT_TOKEN": "123:token-secreto",
    "TELEGRAM_CHAT_ID": "999",
}


def _env(**extras: str) -> dict[str, str]:
    return {**GLOBAIS, **extras}


def test_env_atual_so_com_email1_funciona(home, escrever_env):
    escrever_env(_env(EMAIL1="financeiro@empresa.example", SENHA_EMAIL1="app-pass-1"))
    config = carregar_configuracao(home)

    assert [c.indice for c in config.caixas] == [1]
    caixa = config.caixas[0]
    assert caixa.endereco == "financeiro@empresa.example"
    assert caixa.pasta == "INBOX"
    assert caixa.imap_host == "imap.gmail.com"
    assert caixa.imap_porta == 993
    assert caixa.destino == "Financeiro/CONTAS A PAGAR"
    assert config.rclone_remote == "onedrive-financeiro"
    assert config.data_inicial == date(2026, 9, 1)
    assert config.caixas_invalidas == ()


def test_numeracao_com_lacuna(home, escrever_env):
    escrever_env(_env(
        EMAIL1="a@empresa.example", SENHA_EMAIL1="s1",
        EMAIL3="c@empresa.example", SENHA_EMAIL3="s3",
    ))
    config = carregar_configuracao(home)
    assert [c.indice for c in config.caixas] == [1, 3]


def test_caixas_ordenadas_por_indice(home, escrever_env):
    escrever_env(_env(
        EMAIL10="j@empresa.example", SENHA_EMAIL10="s10",
        EMAIL2="b@empresa.example", SENHA_EMAIL2="s2",
    ))
    config = carregar_configuracao(home)
    assert [c.indice for c in config.caixas] == [2, 10]


def test_variaveis_parecidas_nao_viram_caixa(home, escrever_env):
    escrever_env(_env(
        EMAIL1="a@empresa.example", SENHA_EMAIL1="s1",
        EMAIL0="zero@empresa.example", EMAIL_EXTRA="x@empresa.example",
    ))
    config = carregar_configuracao(home)
    assert [c.indice for c in config.caixas] == [1]


def test_pasta_servidor_e_destino_por_caixa(home, escrever_env):
    escrever_env(_env(
        EMAIL1="a@empresa.example", SENHA_EMAIL1="s1",
        EMAIL2="b@empresa.example", SENHA_EMAIL2="s2",
        PASTA_EMAIL2="Fornecedores/Notas",
        IMAP_HOST_EMAIL2="imap.outro.example",
        DESTINO_ONEDRIVE2="Outra Empresa/CONTAS A PAGAR",
    ))
    config = carregar_configuracao(home)
    caixa1, caixa2 = config.caixas
    assert caixa1.destino == "Financeiro/CONTAS A PAGAR"
    assert caixa2.pasta == "Fornecedores/Notas"
    assert caixa2.imap_host == "imap.outro.example"
    assert caixa2.destino == "Outra Empresa/CONTAS A PAGAR"


def test_empresa_por_caixa_com_padrao_pelo_dominio(home, escrever_env):
    escrever_env(_env(
        EMAIL1="financeiro@acme.example", SENHA_EMAIL1="s1", EMPRESA_EMAIL1="ACME",
        EMAIL2="fulano@mineradora-b.example", SENHA_EMAIL2="s2",
    ))
    caixa1, caixa2 = carregar_configuracao(home).caixas
    assert caixa1.empresa == "ACME"
    assert caixa2.empresa == "MINERADORA B"


def test_senha_ausente_invalida_so_a_caixa(home, escrever_env):
    escrever_env(_env(
        EMAIL1="a@empresa.example", SENHA_EMAIL1="s1",
        EMAIL2="b@empresa.example",
    ))
    config = carregar_configuracao(home)
    assert [c.indice for c in config.caixas] == [1]
    assert [(i.indice, i.motivo) for i in config.caixas_invalidas] == [
        (2, "caixa 2: SENHA_EMAIL2 ausente")
    ]


def test_senha_vazia_conta_como_ausente(home, escrever_env):
    escrever_env(_env(EMAIL1="a@empresa.example", SENHA_EMAIL1=""))
    config = carregar_configuracao(home)
    assert config.caixas == ()
    assert config.caixas_invalidas[0].motivo == "caixa 1: SENHA_EMAIL1 ausente"


def test_endereco_invalido(home, escrever_env):
    escrever_env(_env(EMAIL1="sem-arroba", SENHA_EMAIL1="s1"))
    config = carregar_configuracao(home)
    assert config.caixas_invalidas[0].motivo == "caixa 1: EMAIL1 inválido"


def test_senha_orfa_gera_alerta(home, escrever_env):
    escrever_env(_env(EMAIL1="a@empresa.example", SENHA_EMAIL1="s1", SENHA_EMAIL4="s4"))
    config = carregar_configuracao(home)
    assert [c.indice for c in config.caixas] == [1]
    assert "SENHA_EMAIL4 sem EMAIL4" in config.alertas


def test_endereco_duplicado_na_mesma_pasta(home, escrever_env):
    escrever_env(_env(
        EMAIL1="financeiro@empresa.example", SENHA_EMAIL1="s1",
        EMAIL2="Financeiro@Empresa.example", SENHA_EMAIL2="s2",
    ))
    config = carregar_configuracao(home)
    assert [c.indice for c in config.caixas] == [1]
    assert config.caixas_invalidas[0].motivo == "caixa 2: duplicada da caixa 1"


def test_mesmo_endereco_em_pastas_diferentes_e_valido(home, escrever_env):
    escrever_env(_env(
        EMAIL1="financeiro@empresa.example", SENHA_EMAIL1="s1",
        EMAIL2="financeiro@empresa.example", SENHA_EMAIL2="s1", PASTA_EMAIL2="Notas",
    ))
    config = carregar_configuracao(home)
    assert [c.indice for c in config.caixas] == [1, 2]


@pytest.mark.parametrize("variavel", ["RCLONE_REMOTE", "DESTINO_ONEDRIVE", "DATA_INICIAL"])
def test_variavel_global_ausente_aborta(home, escrever_env, variavel):
    variaveis = _env(EMAIL1="a@empresa.example", SENHA_EMAIL1="s1")
    del variaveis[variavel]
    escrever_env(variaveis)
    with pytest.raises(ErroConfiguracao) as erro:
        carregar_configuracao(home)
    assert f"{variavel} ausente" in erro.value.erros


def test_variavel_global_vazia_aborta(home, escrever_env):
    escrever_env(_env(EMAIL1="a@empresa.example", SENHA_EMAIL1="s1", RCLONE_REMOTE=""))
    with pytest.raises(ErroConfiguracao) as erro:
        carregar_configuracao(home)
    assert "RCLONE_REMOTE ausente" in erro.value.erros


def test_erros_globais_sao_reunidos(home, escrever_env):
    escrever_env({"EMAIL1": "a@empresa.example", "SENHA_EMAIL1": "s1"})
    with pytest.raises(ErroConfiguracao) as erro:
        carregar_configuracao(home)
    assert {"RCLONE_REMOTE ausente", "DESTINO_ONEDRIVE ausente", "DATA_INICIAL ausente"} <= set(
        erro.value.erros
    )


def test_data_inicial_fora_do_formato(home, escrever_env):
    escrever_env(_env(EMAIL1="a@empresa.example", SENHA_EMAIL1="s1", DATA_INICIAL="18/09/2026"))
    with pytest.raises(ErroConfiguracao) as erro:
        carregar_configuracao(home)
    assert "DATA_INICIAL fora do formato AAAA-MM-DD" in erro.value.erros


def test_telegram_completo_ativa_o_canal(home, escrever_env):
    escrever_env(_env(EMAIL1="a@empresa.example", SENHA_EMAIL1="s1"))
    config = carregar_configuracao(home)
    assert config.telegram_ativo
    assert config.telegram_chat_id == "999"


def test_telegram_incompleto_gera_alerta_e_desativa(home, escrever_env):
    variaveis = _env(EMAIL1="a@empresa.example", SENHA_EMAIL1="s1")
    del variaveis["TELEGRAM_CHAT_ID"]
    escrever_env(variaveis)
    config = carregar_configuracao(home)
    assert not config.telegram_ativo
    assert any("TELEGRAM" in alerta and "não serão notificadas" in alerta for alerta in config.alertas)


def test_sem_telegram_nao_e_erro(home, escrever_env):
    variaveis = _env(EMAIL1="a@empresa.example", SENHA_EMAIL1="s1")
    del variaveis["TELEGRAM_CHAT_ID"], variaveis["TELEGRAM_BOT_TOKEN"]
    escrever_env(variaveis)
    config = carregar_configuracao(home)
    assert not config.telegram_ativo


def test_nenhuma_caixa_configurada(home, escrever_env):
    escrever_env(_env())
    config = carregar_configuracao(home)
    assert config.caixas == ()
    assert config.caixas_invalidas == ()


def test_env_ausente_aborta(home):
    with pytest.raises(ErroConfiguracao) as erro:
        carregar_configuracao(home)
    assert "arquivo .env não encontrado" in erro.value.erros


@pytest.mark.skipif(os.geteuid() == 0, reason="root lê arquivos sem permissão")
def test_env_ilegivel_aborta(home, escrever_env):
    escrever_env(_env(EMAIL1="a@empresa.example", SENHA_EMAIL1="s1"), modo=0o000)
    with pytest.raises(ErroConfiguracao) as erro:
        carregar_configuracao(home)
    assert "arquivo .env ilegível" in erro.value.erros


def test_permissao_aberta_gera_alerta(home, escrever_env):
    escrever_env(_env(EMAIL1="a@empresa.example", SENHA_EMAIL1="s1"), modo=0o644)
    config = carregar_configuracao(home)
    assert "permissão do .env mais aberta que 600" in config.alertas


def test_permissao_600_nao_gera_alerta(home, escrever_env):
    escrever_env(_env(EMAIL1="a@empresa.example", SENHA_EMAIL1="s1"))
    config = carregar_configuracao(home)
    assert not any("permissão" in alerta for alerta in config.alertas)


def test_nao_injeta_variaveis_no_ambiente(home, escrever_env):
    escrever_env(_env(EMAIL1="a@empresa.example", SENHA_EMAIL1="s1"))
    carregar_configuracao(home)
    assert "SENHA_EMAIL1" not in os.environ


def test_segredos_ficam_registrados_para_mascaramento(home, escrever_env):
    escrever_env(_env(EMAIL1="a@empresa.example", SENHA_EMAIL1="app-pass-1"))
    carregar_configuracao(home)
    assert segredos.mascarar("senha app-pass-1 e token 123:token-secreto") == (
        "senha **** e token ****"
    )


def test_repr_nao_expoe_segredos(home, escrever_env):
    escrever_env(_env(EMAIL1="a@empresa.example", SENHA_EMAIL1="app-pass-1"))
    config = carregar_configuracao(home)
    texto = repr(config)
    assert "app-pass-1" not in texto
    assert "token-secreto" not in texto


# --- Feature 002: modo de autenticação por caixa (D-10, RF-01 a RF-03, RF-12) -----------------

OAUTH = {"OAUTH_CLIENT_ID": "id-do-cliente.apps.example", "OAUTH_CLIENT_SECRET": "segredo-do-cliente"}


def _autorizacao(home, endereco="a@empresa.example", modo_arquivo=0o600, modo_diretorio=0o700, diretorio="autorizacoes"):
    pasta = home / diretorio
    pasta.mkdir(parents=True, exist_ok=True)
    os.chmod(pasta, modo_diretorio)
    caminho = pasta / f"{endereco}.json"
    caminho.write_text("{}", encoding="utf-8")
    os.chmod(caminho, modo_arquivo)
    return caminho


def test_auth_ausente_vale_senha_e_nada_muda(home, escrever_env):
    escrever_env(_env(EMAIL1="a@empresa.example", SENHA_EMAIL1="s1"))
    config = carregar_configuracao(home)
    assert config.caixas[0].modo == "senha"
    assert config.cliente_oauth is None
    assert config.dir_autorizacoes == home / "autorizacoes"
    assert config.alertas == ()


def test_auth_aceita_maiusculas(home, escrever_env):
    escrever_env(_env(EMAIL1="a@empresa.example", AUTH_EMAIL1="OAuth", **OAUTH))
    assert carregar_configuracao(home).caixas[0].modo == "oauth"


def test_auth_invalido_invalida_so_a_caixa(home, escrever_env):
    escrever_env(_env(EMAIL1="a@empresa.example", SENHA_EMAIL1="s1", AUTH_EMAIL1="token",
                      EMAIL2="b@empresa.example", SENHA_EMAIL2="s2"))
    config = carregar_configuracao(home)
    assert [c.indice for c in config.caixas] == [2]
    assert config.caixas_invalidas[0].motivo == "caixa 1: AUTH_EMAIL1 inválido (use senha ou oauth)"


def test_caixa_oauth_dispensa_a_senha_e_e_valida_sem_autorizacao(home, escrever_env):
    escrever_env(_env(EMAIL1="a@empresa.example", AUTH_EMAIL1="oauth", **OAUTH))
    config = carregar_configuracao(home)
    caixa = config.caixas[0]
    assert (caixa.modo, caixa.senha) == ("oauth", "")
    assert config.caixas_invalidas == ()
    assert config.cliente_oauth.client_id == OAUTH["OAUTH_CLIENT_ID"]
    assert not (home / "autorizacoes").exists()  # carregar a configuração não cria nada


def test_senha_presente_em_caixa_oauth_e_ignorada_com_alerta(home, escrever_env):
    escrever_env(_env(EMAIL1="a@empresa.example", AUTH_EMAIL1="oauth", SENHA_EMAIL1="senha-velha", **OAUTH))
    config = carregar_configuracao(home)
    assert config.caixas[0].senha == ""
    assert "SENHA_EMAIL1 presente em caixa oauth; retire-a do .env" in config.alertas
    assert segredos.mascarar("senha-velha") == "****"


@pytest.mark.parametrize("faltante", ["OAUTH_CLIENT_ID", "OAUTH_CLIENT_SECRET"])
def test_credenciais_do_cliente_ausentes_invalidam_so_as_caixas_oauth(home, escrever_env, faltante):
    oauth = {chave: valor for chave, valor in OAUTH.items() if chave != faltante}
    escrever_env(_env(EMAIL1="a@empresa.example", SENHA_EMAIL1="s1",
                      EMAIL2="b@empresa.example", AUTH_EMAIL2="oauth", **oauth))
    config = carregar_configuracao(home)
    assert [c.indice for c in config.caixas] == [1]
    assert config.cliente_oauth is None
    assert config.caixas_invalidas[0].motivo == "caixa 2: credenciais do cliente OAuth ausentes"


def test_credenciais_do_cliente_sem_caixa_oauth_nao_geram_alerta(home, escrever_env):
    escrever_env(_env(EMAIL1="a@empresa.example", SENHA_EMAIL1="s1", **OAUTH))
    config = carregar_configuracao(home)
    assert config.alertas == ()
    assert config.cliente_oauth is not None


def test_segredo_do_cliente_e_mascarado_e_fica_fora_do_repr(home, escrever_env):
    escrever_env(_env(EMAIL1="a@empresa.example", AUTH_EMAIL1="oauth", **OAUTH))
    config = carregar_configuracao(home)
    assert segredos.mascarar("x segredo-do-cliente y") == "x **** y"
    assert "segredo-do-cliente" not in repr(config)


def test_auth_orfa_gera_alerta(home, escrever_env):
    escrever_env(_env(EMAIL1="a@empresa.example", SENHA_EMAIL1="s1", AUTH_EMAIL3="oauth"))
    assert "AUTH_EMAIL3 sem EMAIL3" in carregar_configuracao(home).alertas


def test_duplicidade_independe_do_modo(home, escrever_env):
    escrever_env(_env(EMAIL1="a@empresa.example", SENHA_EMAIL1="s1",
                      EMAIL2="A@empresa.example", AUTH_EMAIL2="oauth", **OAUTH))
    config = carregar_configuracao(home)
    assert config.caixas_invalidas[0].motivo == "caixa 2: duplicada da caixa 1"


def test_dir_autorizacoes_relativo_e_absoluto(home, escrever_env, tmp_path_factory):
    escrever_env(_env(EMAIL1="a@empresa.example", SENHA_EMAIL1="s1", DIR_AUTORIZACOES="segredos/oauth"))
    assert carregar_configuracao(home).dir_autorizacoes == home / "segredos" / "oauth"
    absoluto = tmp_path_factory.mktemp("fora")
    escrever_env(_env(EMAIL1="a@empresa.example", SENHA_EMAIL1="s1", DIR_AUTORIZACOES=str(absoluto)))
    assert carregar_configuracao(home).dir_autorizacoes == absoluto


def test_endereco_com_separador_de_caminho_invalida_a_caixa_oauth(home, escrever_env):
    escrever_env(_env(EMAIL1="../fora@empresa.example", AUTH_EMAIL1="oauth",
                      EMAIL2="../fora@empresa.example", SENHA_EMAIL2="s2", PASTA_EMAIL2="Outra", **OAUTH))
    config = carregar_configuracao(home)
    assert [c.indice for c in config.caixas] == [2]  # em modo senha o endereço não vira nome de arquivo
    assert config.caixas_invalidas[0].motivo == "caixa 1: EMAIL1 não pode nomear o arquivo de autorização"


def test_permissao_aberta_da_autorizacao_gera_alerta(home, escrever_env):
    _autorizacao(home, modo_arquivo=0o644)
    escrever_env(_env(EMAIL1="A@empresa.example", AUTH_EMAIL1="oauth", **OAUTH))
    alertas = carregar_configuracao(home).alertas
    assert "permissão da autorização da caixa 1 mais aberta que 600" in alertas
    assert not any("diretório" in alerta for alerta in alertas)


def test_permissao_aberta_do_diretorio_gera_alerta(home, escrever_env):
    _autorizacao(home, modo_diretorio=0o755)
    escrever_env(_env(EMAIL1="a@empresa.example", AUTH_EMAIL1="oauth", **OAUTH))
    alertas = carregar_configuracao(home).alertas
    assert "permissão do diretório de autorizações mais aberta que 700" in alertas
    assert not any("autorização da caixa" in alerta for alerta in alertas)


def test_permissoes_corretas_nao_geram_alerta(home, escrever_env):
    _autorizacao(home)
    escrever_env(_env(EMAIL1="a@empresa.example", AUTH_EMAIL1="oauth", **OAUTH))
    assert carregar_configuracao(home).alertas == ()


def test_diretorio_aberto_sem_caixa_oauth_nao_gera_alerta(home, escrever_env):
    _autorizacao(home, modo_diretorio=0o755)
    escrever_env(_env(EMAIL1="a@empresa.example", SENHA_EMAIL1="s1"))
    assert carregar_configuracao(home).alertas == ()
