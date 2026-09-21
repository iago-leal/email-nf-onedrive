"""Leitura e validação do .env (spec configuracao-caixas, D-03).

O .env é lido com `dotenv_values`, sem tocar em `os.environ`, para que as
credenciais não vazem para subprocessos como o Rclone. Toda a validação ocorre
antes de qualquer acesso à rede.
"""

from __future__ import annotations

import os
import re
import stat
from datetime import date
from pathlib import Path

from dotenv import dotenv_values

from email_nf_onedrive import segredos
from email_nf_onedrive.configuracao.modelo import Caixa, CaixaInvalida, Configuracao, ErroConfiguracao
from email_nf_onedrive.envio.nomeacao import rotulo_do_endereco

PASTA_PADRAO = "INBOX"
IMAP_HOST_PADRAO = "imap.gmail.com"

_EMAIL = re.compile(r"^EMAIL([1-9][0-9]*)$")
_SENHA = re.compile(r"^SENHA_EMAIL([1-9][0-9]*)$")
_DATA = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _ler_env(caminho: Path) -> dict[str, str]:
    if not caminho.exists():
        raise ErroConfiguracao(["arquivo .env não encontrado"])
    try:
        with caminho.open(encoding="utf-8") as arquivo:
            valores = dotenv_values(stream=arquivo)
    except OSError as erro:
        raise ErroConfiguracao(["arquivo .env ilegível"]) from erro
    return {chave: (valor or "").strip() for chave, valor in valores.items()}


def _permissao_aberta(caminho: Path) -> bool:
    modo = stat.S_IMODE(os.stat(caminho).st_mode)
    return bool(modo & (stat.S_IRWXG | stat.S_IRWXO))


def _data_inicial(env: dict[str, str], erros: list[str]) -> date | None:
    valor = env.get("DATA_INICIAL", "")
    if not valor:
        erros.append("DATA_INICIAL ausente")
        return None
    if _DATA.match(valor):
        try:
            return date.fromisoformat(valor)
        except ValueError:
            pass
    erros.append("DATA_INICIAL fora do formato AAAA-MM-DD")
    return None


def _indices(env: dict[str, str], padrao: re.Pattern[str]) -> set[int]:
    return {int(m.group(1)) for chave in env if (m := padrao.match(chave))}


def carregar_configuracao(home: Path) -> Configuracao:
    caminho = Path(home) / ".env"
    env = _ler_env(caminho)
    alertas: list[str] = []
    if _permissao_aberta(caminho):
        alertas.append("permissão do .env mais aberta que 600")

    erros: list[str] = []
    rclone_remote = env.get("RCLONE_REMOTE", "")
    destino_global = env.get("DESTINO_ONEDRIVE", "")
    if not rclone_remote:
        erros.append("RCLONE_REMOTE ausente")
    if not destino_global:
        erros.append("DESTINO_ONEDRIVE ausente")
    data_inicial = _data_inicial(env, erros)
    if erros:
        raise ErroConfiguracao(erros)

    token = env.get("TELEGRAM_BOT_TOKEN") or None
    chat_id = env.get("TELEGRAM_CHAT_ID") or None
    if bool(token) != bool(chat_id):
        alertas.append(
            "TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID devem ser definidos juntos; "
            "falhas não serão notificadas"
        )
    segredos.registrar(token)

    indices_email = _indices(env, _EMAIL)
    for orfa in sorted(_indices(env, _SENHA) - indices_email):
        alertas.append(f"SENHA_EMAIL{orfa} sem EMAIL{orfa}")

    caixas: list[Caixa] = []
    invalidas: list[CaixaInvalida] = []
    vistas: dict[tuple[str, str], int] = {}
    for n in sorted(indices_email):
        endereco = env[f"EMAIL{n}"]
        senha = env.get(f"SENHA_EMAIL{n}", "")
        pasta = env.get(f"PASTA_EMAIL{n}") or PASTA_PADRAO
        segredos.registrar(senha)
        if "@" not in endereco:
            invalidas.append(CaixaInvalida(n, f"caixa {n}: EMAIL{n} inválido"))
            continue
        if not senha:
            invalidas.append(CaixaInvalida(n, f"caixa {n}: SENHA_EMAIL{n} ausente"))
            continue
        chave = (endereco.lower(), pasta)
        if chave in vistas:
            invalidas.append(CaixaInvalida(n, f"caixa {n}: duplicada da caixa {vistas[chave]}"))
            continue
        vistas[chave] = n
        caixas.append(Caixa(
            indice=n,
            endereco=endereco,
            senha=senha,
            pasta=pasta,
            imap_host=env.get(f"IMAP_HOST_EMAIL{n}") or IMAP_HOST_PADRAO,
            destino=env.get(f"DESTINO_ONEDRIVE{n}") or destino_global,
            empresa=env.get(f"EMPRESA_EMAIL{n}") or rotulo_do_endereco(endereco),
        ))

    return Configuracao(
        caixas=tuple(caixas),
        caixas_invalidas=tuple(invalidas),
        rclone_remote=rclone_remote,
        data_inicial=data_inicial,
        telegram_bot_token=token,
        telegram_chat_id=chat_id,
        alertas=tuple(alertas),
    )
