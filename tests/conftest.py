"""Fixtures compartilhadas pelos testes."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

DADOS = Path(__file__).parent / "dados"


@pytest.fixture
def dados() -> Path:
    """Diretório com e-mails e XMLs sintéticos."""
    return DADOS


@pytest.fixture
def home(tmp_path: Path) -> Path:
    """Diretório de instalação temporário, com a subpasta var/."""
    (tmp_path / "var").mkdir()
    return tmp_path


@pytest.fixture
def escrever_env(home: Path):
    """Fábrica que grava home/.env a partir de um dicionário."""

    def _escrever(variaveis: dict[str, str], modo: int = 0o600) -> Path:
        caminho = home / ".env"
        linhas = [f"{chave}={valor}" for chave, valor in variaveis.items()]
        caminho.write_text("\n".join(linhas) + "\n", encoding="utf-8")
        os.chmod(caminho, modo)
        return caminho

    return _escrever


class Relogio:
    """Relógio controlável, injetado onde o código consulta a hora."""

    def __init__(self, inicio: datetime) -> None:
        self.atual = inicio

    def agora(self) -> datetime:
        return self.atual

    def avancar(self, **kwargs: float) -> datetime:
        self.atual += timedelta(**kwargs)
        return self.atual


@pytest.fixture
def relogio() -> Relogio:
    return Relogio(datetime(2026, 9, 18, 12, 0, tzinfo=timezone.utc))


@pytest.fixture(autouse=True)
def _limpar_segredos():
    """Isola o registro global de segredos entre testes."""
    try:
        from email_nf_onedrive import segredos
    except ImportError:
        yield
        return
    segredos.limpar()
    yield
    segredos.limpar()
