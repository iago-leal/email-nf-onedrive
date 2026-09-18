"""Trava de execução e limite de duração (D-14, EM RF-03, RF-04).

A trava é um arquivo criado de forma exclusiva com o PID e o horário. Ela é
considerada abandonada quando passa de 25 min ou quando o processo dono não
existe mais. O limite de 20 min garante que uma execução travada termine antes
de a trava expirar.
"""

from __future__ import annotations

import os
import signal
import time
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path
from typing import Callable, Iterator

EXPIRACAO = timedelta(minutes=25)
LIMITE_DURACAO_S = 20 * 60


class TravaOcupada(Exception):
    """Outra execução está em andamento."""


class TempoEsgotado(Exception):
    """A execução ultrapassou o limite de duração."""


def _processo_vivo(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


class Trava:
    def __init__(self, caminho: Path, *, expiracao: timedelta = EXPIRACAO,
                 agora: Callable[[], float] = time.time) -> None:
        self.caminho = Path(caminho)
        self.expiracao = expiracao
        self.agora = agora
        self._adquirida = False

    def _criar(self) -> None:
        fd = os.open(self.caminho, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as arquivo:
            arquivo.write(f"{os.getpid()}\n{self.agora()}\n")
        self._adquirida = True

    def _abandonada(self) -> bool:
        try:
            pid_texto, instante_texto = self.caminho.read_text(encoding="utf-8").split()[:2]
            pid, instante = int(pid_texto), float(instante_texto)
        except (OSError, ValueError):
            return True
        idade = self.agora() - instante
        return idade > self.expiracao.total_seconds() or not _processo_vivo(pid)

    def adquirir(self) -> bool:
        """Adquire a trava. Devolve True se removeu uma trava abandonada no caminho."""
        try:
            self._criar()
            return False
        except FileExistsError:
            pass
        if not self._abandonada():
            raise TravaOcupada(str(self.caminho))
        self.caminho.unlink(missing_ok=True)
        try:
            self._criar()
        except FileExistsError as erro:  # outra execução retomou a trava antes
            raise TravaOcupada(str(self.caminho)) from erro
        return True

    def liberar(self) -> None:
        if self._adquirida:
            self.caminho.unlink(missing_ok=True)
            self._adquirida = False

    def __enter__(self) -> "Trava":
        self.adquirir()
        return self

    def __exit__(self, *_exc) -> None:
        self.liberar()


@contextmanager
def limite_duracao(segundos: int = LIMITE_DURACAO_S) -> Iterator[None]:
    """Levanta TempoEsgotado se o bloco passar de `segundos`. Só na thread principal."""

    def _estourou(_sinal, _quadro):
        raise TempoEsgotado(f"execução passou de {segundos} s")

    anterior = signal.signal(signal.SIGALRM, _estourou)
    signal.alarm(segundos)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, anterior)
