"""Arquivo de autorização de uma caixa em modo oauth (feature 002, D-05, data-delta.md §4).

Um JSON por caixa, em `<DIR_AUTORIZACOES>/<endereço em minúsculas>.json`, com a
autorização durável (refresh token). Diretório com permissão 700 e arquivo com
600. Só o `autorizar-caixa` grava; o ciclo apenas lê (RF-09). Nada aqui depende
da máquina, de modo que o diretório pode ser copiado para a VPS (RF-05).
"""

from __future__ import annotations

import json
import os
import secrets
import stat
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from email_nf_onedrive import segredos

VERSAO = 1
ESCOPO_CORREIO = "https://mail.google.com/"

SEM_AUTORIZACAO = "sem autorização"
ILEGIVEL = "autorização ilegível"
OUTRO_ENDERECO = "autorização de outro endereço"
OUTRO_CLIENTE = "autorização emitida para outro cliente OAuth"


class ErroArquivoAutorizacao(Exception):
    """Autorização ausente ou recusada na leitura; `motivo` é o texto exibido ao operador."""

    def __init__(self, motivo: str, *, ausente: bool = False) -> None:
        super().__init__(motivo)
        self.motivo = motivo
        self.ausente = ausente


@dataclass(frozen=True)
class Autorizacao:
    endereco: str
    client_id: str
    refresh_token: str = field(repr=False)
    escopos: tuple[str, ...]
    autorizada_em: datetime | None = None


def nome_seguro(endereco: str) -> bool:
    """Falso se o endereço não puder nomear um arquivo sem sair do diretório."""
    return bool(endereco) and not any(c in endereco for c in ("/", "\\", "\0")) and endereco not in (".", "..")


def caminho(diretorio: Path, endereco: str) -> Path:
    return Path(diretorio) / f"{endereco.lower()}.json"


def existe_e_legivel(diretorio: Path, endereco: str) -> bool:
    """Estado exibido pelo `verificar-config`: só `stat` e permissão, sem abrir o arquivo (RF-10)."""
    destino = caminho(diretorio, endereco)
    try:
        return stat.S_ISREG(os.stat(destino).st_mode) and os.access(destino, os.R_OK)
    except OSError:
        return False


def ler(diretorio: Path, endereco: str, client_id: str) -> Autorizacao:
    try:
        bruto = caminho(diretorio, endereco).read_text(encoding="utf-8")
    except FileNotFoundError as erro:
        raise ErroArquivoAutorizacao(SEM_AUTORIZACAO, ausente=True) from erro
    except (OSError, UnicodeDecodeError) as erro:
        raise ErroArquivoAutorizacao(ILEGIVEL) from erro
    try:
        dados = json.loads(bruto)
    except ValueError as erro:
        raise ErroArquivoAutorizacao(ILEGIVEL) from erro
    if not isinstance(dados, dict):
        raise ErroArquivoAutorizacao(ILEGIVEL)

    refresh_token, escopos = dados.get("refresh_token"), dados.get("escopos")
    if isinstance(refresh_token, str):
        segredos.registrar(refresh_token)
    if dados.get("versao") != VERSAO or not isinstance(refresh_token, str) or not refresh_token:
        raise ErroArquivoAutorizacao(ILEGIVEL)
    if not isinstance(escopos, list) or ESCOPO_CORREIO not in escopos:
        raise ErroArquivoAutorizacao(ILEGIVEL)
    if str(dados.get("endereco", "")).lower() != endereco.lower():
        raise ErroArquivoAutorizacao(OUTRO_ENDERECO)
    if dados.get("client_id") != client_id:
        raise ErroArquivoAutorizacao(OUTRO_CLIENTE)
    try:
        autorizada_em = datetime.fromisoformat(dados.get("autorizada_em"))
    except (TypeError, ValueError):
        autorizada_em = None  # campo informativo
    return Autorizacao(endereco=dados["endereco"], client_id=client_id, refresh_token=refresh_token,
                       escopos=tuple(str(e) for e in escopos), autorizada_em=autorizada_em)


def gravar(diretorio: Path, autorizacao: Autorizacao) -> Path:
    """Grava de forma atômica: temporário com 600 no mesmo diretório e `os.replace` sobre o destino."""
    diretorio = Path(diretorio)
    diretorio.mkdir(parents=True, exist_ok=True, mode=0o700)
    destino = caminho(diretorio, autorizacao.endereco)
    conteudo = json.dumps({
        "versao": VERSAO,
        "endereco": autorizacao.endereco,
        "client_id": autorizacao.client_id,
        "refresh_token": autorizacao.refresh_token,
        "escopos": list(autorizacao.escopos),
        "autorizada_em": autorizacao.autorizada_em.isoformat(timespec="seconds") if autorizacao.autorizada_em else None,
    }, ensure_ascii=False, indent=2)
    temporario = diretorio / f".{destino.name}.{secrets.token_hex(4)}.tmp"
    fd = os.open(temporario, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as arquivo:
            arquivo.write(conteudo + "\n")
        os.replace(temporario, destino)
    except BaseException:
        temporario.unlink(missing_ok=True)
        raise
    return destino
