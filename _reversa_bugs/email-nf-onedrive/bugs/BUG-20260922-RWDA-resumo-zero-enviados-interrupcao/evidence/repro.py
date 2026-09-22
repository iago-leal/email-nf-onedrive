"""Reprodução do BUG-20260922-RWDA: resumo com `0 enviados` após interrupção por tempo.

Roda a partir da raiz do projeto: `.venv/bin/python _reversa_bugs/.../evidence/repro.py`.

O ciclo completo é exercitado pela infraestrutura de testes do projeto (IMAP dublê e
Rclone real em `:local`), por isso o script grava um arquivo de teste temporário em
`tests/integracao/`, roda o pytest nele e o apaga no fim.

A interrupção é imposta por um Rclone que levanta `TempoEsgotado` a partir da terceira
cópia. É a mesma exceção que `limite_duracao` levanta pelo SIGALRM, levantada no mesmo
ponto (dentro do laço de `Enviador.enviar`), sem depender do relógio de parede.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[5]
TEMPORARIO = RAIZ / "tests" / "integracao" / "test__repro_rwda.py"

TESTE = '''"""Temporário: reprodução do BUG-20260922-RWDA. Apagado pelo evidence/repro.py."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from email_nf_onedrive.envio.rclone import Rclone
from email_nf_onedrive.execucao.trava import TempoEsgotado

pytestmark = pytest.mark.integracao


class RcloneInterrompido(Rclone):
    """Rclone real que levanta TempoEsgotado a partir da N-ésima cópia."""

    def __init__(self, remote: str, limite: int) -> None:
        super().__init__(remote)
        self.limite = limite
        self.copias = 0

    def copiar(self, local: Path, relativo: str) -> None:
        self.copias += 1
        if self.copias > self.limite:
            raise TempoEsgotado("execução passou de 1200 s")
        super().copiar(local, relativo)


def test_repro_resumo_zero_enviados(cenario):
    cenario.entregar("encaminhada.eml", "encaminhada_em_linha.eml", "interna_nfe_e_danfe.eml")
    deps = cenario.deps()
    deps.criar_rclone = lambda remote: RcloneInterrompido(remote, 2)

    codigo = cenario.executar("executar", deps=deps)
    log = cenario.log()
    enviados_no_log = len(re.findall(r"enviado: ", log))
    resumo = [linha for linha in log.splitlines() if "resumo: " in linha][-1]

    print(f"\\ncódigo de saída          : {codigo}")
    print(f"arquivos no destino      : {len(cenario.arquivos_no_destino())}")
    print(f"linhas 'enviado:' no log : {enviados_no_log}")
    print(f"estados no registro      : {cenario.estados()}")
    print(f"resumo                   : {resumo.split('resumo: ')[1]}")

    assert "execução interrompida" in log
    assert enviados_no_log == 2
    assert "0 enviados" in resumo  # o defeito: o log tem 2 envios, o resumo diz 0
'''


def main() -> int:
    TEMPORARIO.write_text(TESTE, encoding="utf-8")
    try:
        return subprocess.call(
            [sys.executable, "-m", "pytest", str(TEMPORARIO), "-q", "-s"], cwd=RAIZ
        )
    finally:
        TEMPORARIO.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
