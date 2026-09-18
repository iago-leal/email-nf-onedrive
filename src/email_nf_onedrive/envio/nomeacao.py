"""Convenção de nomes no OneDrive (D-12).

PROVISÓRIA até o fechamento da L-03: a convenção definitiva sai do levantamento
da pasta real com `rclone lsf` (ação T042). Toda a regra de nomes vive neste
módulo para que a troca não afete o restante do envio.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from zoneinfo import ZoneInfo

LIMITE_NOME = 200
FUSO_RECEBIMENTO = ZoneInfo("America/Sao_Paulo")

_INVALIDOS = re.compile(r'["*:<>?/\\|]')
_ESPACOS = re.compile(r" {2,}")
_RESERVADOS = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(10)), *(f"LPT{i}" for i in range(10))}
_NOMES_RESERVADOS = {".lock", "desktop.ini"}


def _separar_extensao(nome: str) -> tuple[str, str]:
    if "." in nome[1:]:
        base, ext = nome.rsplit(".", 1)
        return base, "." + ext
    return nome, ""


def _truncar(nome: str) -> str:
    if len(nome) <= LIMITE_NOME:
        return nome
    base, ext = _separar_extensao(nome)
    return base[: LIMITE_NOME - len(ext)] + ext


def sanear(nome: str) -> str:
    """Remove o que o OneDrive recusa e limita o nome a 200 caracteres (EO RF-02)."""
    nome = _INVALIDOS.sub("", nome)
    nome = _ESPACOS.sub(" ", nome).strip(" ").rstrip(".").strip(" ")
    nome = nome.replace("_vti_", "_vti-")
    if not nome:
        return "anexo"
    base, _ext = _separar_extensao(nome)
    if nome.lower() in _NOMES_RESERVADOS or base.upper() in _RESERVADOS:
        nome = "_" + nome
    return _truncar(nome)


def _data_recebimento(data_mensagem: datetime | date) -> date:
    if isinstance(data_mensagem, datetime):
        return data_mensagem.astimezone(FUSO_RECEBIMENTO).date()
    return data_mensagem


def nome_destino(data_mensagem: datetime | date, remetente: str, nome_original: str) -> str:
    """`AAAA-MM-DD_<remetente>_<nome-original>`, com a data de recebimento em Brasília."""
    local = sanear(remetente.split("@", 1)[0]) if remetente else "remetente"
    dia = _data_recebimento(data_mensagem).isoformat()
    return sanear(f"{dia}_{local}_{sanear(nome_original)}")


def caminho_destino(destino: str, *, data_mensagem: datetime | date, remetente: str, nome_original: str) -> str:
    """Caminho relativo ao remote: pasta de destino mais o nome padronizado."""
    return f"{destino.rstrip('/')}/{nome_destino(data_mensagem, remetente, nome_original)}"


def com_sufixo(nome: str, n: int) -> str:
    """Acrescenta `_n` antes da extensão, respeitando o limite de tamanho (EO RF-04)."""
    base, ext = _separar_extensao(nome)
    sufixo = f"_{n}{ext}"
    return base[: LIMITE_NOME - len(sufixo)] + sufixo
