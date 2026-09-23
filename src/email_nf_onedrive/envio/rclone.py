"""Fachada do Rclone com lista branca de subcomandos (D-10, interfaces/rclone-onedrive.md).

Única fronteira com o processo externo. Só admite os subcomandos de consulta,
cópia de um arquivo para nome exato e exclusão do arquivo de teste do
`testar-onedrive`; `sync`, `delete`, `purge`, `move` e afins são recusados antes
de executar (RN-02). O upload usa `--ignore-existing`: se o nome já existir no
destino, o Rclone não o sobrescreve.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from email_nf_onedrive import segredos

# Por chamada. O OneDrive, sob carga, pede espera (429 com Retry-After) que o Rclone cumpre dentro da
# própria chamada; com 120 s o limite a cortava no meio da espera (adendo 005).
TIMEOUT_S = 300
SUBCOMANDOS = frozenset({"lsjson", "hashsum", "copyto", "lsf", "deletefile"})
FLAGS_COMUNS = ("--retries", "3", "--low-level-retries", "10")
NOME_TESTE = re.compile(r"(^|/)\.email-nf-onedrive-teste-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.txt$")
LIMITE_DETALHE = 500
CODIGO_NAO_ENCONTRADO = 3

TOKEN = "token"
ACESSO = "acesso"
LIMITE = "limite"
CONFIG = "config"
TEMPO = "timeout"
OUTRO = "outro"

_CAUSAS = (
    (TOKEN, re.compile(r"invalid_grant|token expired|couldn't fetch token|failed to refresh|unauthenticated|\b401\b", re.I)),
    (ACESSO, re.compile(r"accessDenied|access denied|forbidden|\b403\b", re.I)),
    (LIMITE, re.compile(r"activityLimitReached|too many requests|\b429\b", re.I)),
    (CONFIG, re.compile(r"didn't find section in config file|config file .* not found", re.I)),
)


class SubcomandoProibido(Exception):
    """Tentativa de usar subcomando fora da lista branca ou de apagar arquivo que não é o de teste."""


class ErroRclone(Exception):
    def __init__(self, causa: str, detalhe: str) -> None:
        super().__init__(detalhe)
        self.causa = causa
        self.detalhe = detalhe


@dataclass(frozen=True)
class ObjetoRemoto:
    tamanho: int
    quickxor: str | None


def _classificar_erro(stderr: str) -> str:
    for causa, padrao in _CAUSAS:
        if padrao.search(stderr):
            return causa
    return OUTRO


class Rclone:
    def __init__(self, remote: str, *, binario: str | None = None, timeout: float = TIMEOUT_S,
                 executor: Callable[..., subprocess.CompletedProcess] = subprocess.run) -> None:
        self.remote = remote
        self.binario = binario or os.environ.get("RCLONE_BIN", "rclone")
        self.timeout = timeout
        self._executor = executor

    def caminho(self, relativo: str) -> str:
        return f"{self.remote}:{relativo}"

    def _executar(self, subcomando: str, *args: str, aceitar: tuple[int, ...] = (0,)) -> subprocess.CompletedProcess:
        if subcomando not in SUBCOMANDOS:
            raise SubcomandoProibido(subcomando)
        comando = [self.binario, subcomando, *args, *FLAGS_COMUNS]
        try:
            resultado = self._executor(comando, capture_output=True, text=True, timeout=self.timeout, check=False)
        except subprocess.TimeoutExpired as erro:
            raise ErroRclone(TEMPO, f"rclone {subcomando} passou de {self.timeout:.0f} s") from erro
        except FileNotFoundError as erro:
            raise ErroRclone(CONFIG, f"executável do rclone não encontrado: {self.binario}") from erro
        if resultado.returncode not in aceitar:
            stderr = segredos.mascarar(resultado.stderr.strip())[-LIMITE_DETALHE:]
            raise ErroRclone(_classificar_erro(stderr), stderr or f"código {resultado.returncode}")
        return resultado

    # --- consultas -----------------------------------------------------------

    def estatistica(self, relativo: str) -> ObjetoRemoto | None:
        """Tamanho e QuickXorHash de um arquivo; None se não existir."""
        resultado = self._executar(
            "lsjson", "--stat", "--hash-type", "quickxor", self.caminho(relativo),
            aceitar=(0, CODIGO_NAO_ENCONTRADO),
        )
        if resultado.returncode == CODIGO_NAO_ENCONTRADO or not resultado.stdout.strip():
            return None
        dados = json.loads(resultado.stdout)
        if dados.get("IsDir"):
            return None
        return ObjetoRemoto(tamanho=int(dados["Size"]), quickxor=(dados.get("Hashes") or {}).get("quickxor"))

    def hash_local(self, arquivo: Path) -> str:
        resultado = self._executar("hashsum", "quickxor", str(arquivo))
        return resultado.stdout.split()[0]

    def listar(self, relativo: str, *, profundidade: int = 1) -> list[str] | None:
        """Nomes na pasta; None se a pasta não existir."""
        resultado = self._executar(
            "lsf", "--max-depth", str(profundidade), self.caminho(relativo), aceitar=(0, CODIGO_NAO_ENCONTRADO)
        )
        if resultado.returncode == CODIGO_NAO_ENCONTRADO:
            return None
        return [linha for linha in resultado.stdout.splitlines() if linha]

    def pasta_existe(self, relativo: str) -> bool:
        return self.listar(relativo) is not None

    # --- escrita ---------------------------------------------------------------

    def copiar(self, local: Path, relativo: str) -> None:
        """Envia um arquivo para o nome exato, sem nunca sobrescrever (`--ignore-existing`)."""
        self._executar("copyto", "--ignore-existing", str(local), self.caminho(relativo))

    def apagar_arquivo_de_teste(self, relativo: str) -> None:
        if not NOME_TESTE.search(relativo):
            raise SubcomandoProibido(f"deletefile só é permitido no arquivo de teste: {relativo}")
        self._executar("deletefile", self.caminho(relativo))
