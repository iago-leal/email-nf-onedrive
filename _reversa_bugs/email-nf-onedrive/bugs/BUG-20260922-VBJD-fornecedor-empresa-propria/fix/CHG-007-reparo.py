"""CHG-007 (data-repair) do BUG-20260922-VBJD: devolve a pendente os envios de uma pasta de destino.

Uso na VPS, como email-nf, a partir de /opt/email-nf-onedrive, com o cron pausado, a versão
corrigida instalada e a pasta de teste já esvaziada no OneDrive:

    python3 CHG-007-reparo.py "AFLA Financeiro/CONTAS A PAGAR - TESTE"            # dry-run
    python3 CHG-007-reparo.py "AFLA Financeiro/CONTAS A PAGAR - TESTE" --aplicar  # backup + reparo

O reparo põe `estado='extraido'`, `caminho_destino=NULL`, `tentativas_envio=0`, `ultimo_erro=NULL`
nas linhas `enviado` daquele destino. O próximo ciclo recoleta as mensagens (a janela recua até a
pendente mais antiga) e as reenvia com os nomes corrigidos.

Rollback: pare o cron e copie o backup indicado de volta sobre var/registro.sqlite3.
"""

from __future__ import annotations

import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

REGISTRO = Path("var/registro.sqlite3")
FILTRO = "estado = 'enviado' AND caminho_destino LIKE ? ESCAPE '\\'"


def _prefixo(destino: str) -> str:
    escapado = destino.rstrip("/").replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return escapado + "/%"


def _contagem(con: sqlite3.Connection, destino: str) -> list[tuple[int, int]]:
    return list(con.execute(f"SELECT caixa_indice, count(*) FROM anexos WHERE {FILTRO} GROUP BY 1",
                            (_prefixo(destino),)))


def _backup() -> Path:
    alvo = REGISTRO.with_name(f"{REGISTRO.name}.bak-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}")
    origem = sqlite3.connect(REGISTRO)
    copia = sqlite3.connect(alvo)
    with copia:
        origem.backup(copia)
    origem.close()
    ok = copia.execute("PRAGMA integrity_check").fetchone()[0]
    total_copia = copia.execute("SELECT count(*) FROM anexos").fetchone()[0]
    copia.close()
    with sqlite3.connect(f"file:{REGISTRO}?mode=ro", uri=True) as con:
        total = con.execute("SELECT count(*) FROM anexos").fetchone()[0]
    if ok != "ok" or total_copia != total:
        sys.exit(f"backup {alvo} não confere (integrity_check={ok}, linhas {total_copia} x {total}); nada foi alterado")
    shutil.copymode(REGISTRO, alvo)
    return alvo


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1].startswith("-"):
        print(__doc__)
        return 2
    destino, aplicar = argv[1], "--aplicar" in argv[2:]
    with sqlite3.connect(f"file:{REGISTRO}?mode=ro", uri=True) as con:
        antes = _contagem(con, destino)
    total = sum(n for _, n in antes)
    print(f"linhas 'enviado' em {destino!r}: {total} (por caixa: {antes})")
    if not aplicar or total == 0:
        print("dry-run: nada alterado" if total else "nada a reparar")
        return 0
    alvo = _backup()
    print(f"backup verificado: {alvo}")
    con = sqlite3.connect(REGISTRO)
    with con:
        alteradas = con.execute(
            f"UPDATE anexos SET estado = 'extraido', caminho_destino = NULL, tentativas_envio = 0, "
            f"ultimo_erro = NULL, atualizado_em = ? WHERE {FILTRO}",
            (datetime.now(timezone.utc).isoformat(timespec="seconds"), _prefixo(destino)),
        ).rowcount
    restantes = _contagem(con, destino)
    con.close()
    print(f"reparadas: {alteradas}; 'enviado' restantes no destino: {sum(n for _, n in restantes)}")
    return 0 if alteradas == total and not restantes else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
