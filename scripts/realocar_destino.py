"""Realoca documentos já enviados de uma pasta de destino para outra, no OneDrive e no registro.

Serve para quando o financeiro muda o destino de uma empresa depois que a ferramenta já enviou
documentos. Roda na VPS, como o usuário de serviço, com o Python do .venv:

    sudo -u email-nf env HOME=/opt/email-nf-onedrive /opt/email-nf-onedrive/.venv/bin/python \
        realocar_destino.py mover  "<ORIGEM>" "<DESTINO>" --caixas 3,4,5 [--executar]
    sudo -u email-nf env HOME=/opt/email-nf-onedrive /opt/email-nf-onedrive/.venv/bin/python \
        realocar_destino.py renomear "<ORIGEM>" "<DESTINO>" [--executar]

- `mover`: replica em DESTINO a árvore de pastas de ORIGEM (a grade não é criada pela ferramenta),
  move os arquivos que o registro atribui às caixas indicadas, cada um na mesma posição relativa,
  e regrava `caminho_destino` só dos que conferiram no destino.
- `renomear`: renomeia a pasta inteira (DirMove no servidor) e regrava o prefixo no registro.

Sem `--executar`, só relata o que faria. Com ele, copia antes o registro para
`registro.sqlite3.bak-<AAAAMMDD-HHMMSS>-realocacao`. Em ambos os casos apaga as chaves
`leiame:<ORIGEM>` e `leiame:<DESTINO>`, para que a próxima execução refaça as planilhas.
Depois, ajuste `DESTINO_ONEDRIVE<n>` no .env: o script não o toca.
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

HOME = Path("/opt/email-nf-onedrive")
REGISTRO = HOME / "var" / "registro.sqlite3"
CONFIG_RCLONE = HOME / ".config" / "rclone" / "rclone.conf"
REMOTE = "onedrive-financeiro"
TIMEOUT_S = 300


def rclone(*args: str, aceitar: tuple[int, ...] = (0,)) -> subprocess.CompletedProcess:
    proc = subprocess.run(["rclone", "--config", str(CONFIG_RCLONE), *args],
                          capture_output=True, text=True, timeout=TIMEOUT_S * 4)
    if proc.returncode not in aceitar:
        sys.exit(f"rclone {args[0]} falhou ({proc.returncode}): {proc.stderr.strip()[-500:]}")
    return proc


def remoto(caminho: str) -> str:
    return f"{REMOTE}:{caminho}"


def listar(pasta: str, *, pastas: bool) -> set[str] | None:
    proc = rclone("lsf", "-R", "--dirs-only" if pastas else "--files-only", remoto(pasta), aceitar=(0, 3))
    if proc.returncode == 3:  # diretório inexistente
        return None
    return {linha.rstrip("/") for linha in proc.stdout.splitlines() if linha}


def backup() -> Path:
    copia = REGISTRO.with_name(f"{REGISTRO.name}.bak-{datetime.now():%Y%m%d-%H%M%S}-realocacao")
    shutil.copy2(REGISTRO, copia)
    return copia


def limpar_leiame(con: sqlite3.Connection, *pastas: str) -> None:
    for pasta in pastas:
        con.execute("DELETE FROM meta WHERE chave = ?", (f"leiame:{pasta}",))


def cmd_renomear(origem: str, destino: str, executar: bool) -> None:
    if listar(origem, pastas=True) is None:
        sys.exit(f"origem inexistente: {origem}")
    if listar(destino, pastas=True) is not None:
        sys.exit(f"destino já existe, renome recusado: {destino}")
    prefixo = origem + "/"
    con = sqlite3.connect(REGISTRO)
    n = con.execute("SELECT count(*) FROM anexos WHERE substr(caminho_destino, 1, ?) = ?",
                    (len(prefixo), prefixo)).fetchone()[0]
    print(f"renomear: {origem} -> {destino}; {n} linhas do registro com o prefixo")
    if not executar:
        return
    print(f"cópia do registro: {backup()}")
    rclone("moveto", remoto(origem), remoto(destino))
    if listar(destino, pastas=True) is None:
        sys.exit("o destino não apareceu depois do renome; registro intocado")
    with con:
        con.execute("UPDATE anexos SET caminho_destino = ? || substr(caminho_destino, ?) "
                    "WHERE substr(caminho_destino, 1, ?) = ?",
                    (destino + "/", len(prefixo) + 1, len(prefixo), prefixo))
        limpar_leiame(con, origem, destino)
    print("feito")


def cmd_mover(origem: str, destino: str, caixas: list[int], executar: bool) -> None:
    arquivos_origem = listar(origem, pastas=False)
    if arquivos_origem is None:
        sys.exit(f"origem inexistente: {origem}")
    prefixo = origem + "/"
    con = sqlite3.connect(REGISTRO)
    marcas = ",".join("?" * len(caixas))
    linhas = con.execute(
        f"SELECT DISTINCT caminho_destino FROM anexos WHERE estado = 'enviado' "
        f"AND caixa_indice IN ({marcas}) AND substr(caminho_destino, 1, ?) = ?",
        (*caixas, len(prefixo), prefixo)).fetchall()
    relativos = sorted(linha[0][len(prefixo):] for linha in linhas)
    ausentes = [r for r in relativos if r not in arquivos_origem]
    presentes = [r for r in relativos if r in arquivos_origem]

    # Arquivo de outra caixa com o mesmo caminho ficaria sem registro coerente: recusa.
    compartilhados = con.execute(
        f"SELECT DISTINCT caminho_destino FROM anexos WHERE estado = 'enviado' "
        f"AND caixa_indice NOT IN ({marcas}) AND substr(caminho_destino, 1, ?) = ?",
        (*caixas, len(prefixo), prefixo)).fetchall()
    conflitos = sorted({c[0][len(prefixo):] for c in compartilhados} & set(presentes))
    if conflitos:
        sys.exit(f"{len(conflitos)} arquivos também pertencem a outras caixas; ex.: {conflitos[:3]}")

    pastas_origem = listar(origem, pastas=True) or set()
    pastas_destino = listar(destino, pastas=True)
    criar_base = pastas_destino is None
    arquivos_destino = set() if criar_base else listar(destino, pastas=False) or set()
    ja_no_destino = [r for r in presentes if r in arquivos_destino]
    a_criar = sorted(pastas_origem - (pastas_destino or set()))

    raiz = [r for r in presentes if "/" not in r]
    print(f"mover: {origem} -> {destino}, caixas {caixas}")
    print(f"  pasta-base: {'a criar' if criar_base else 'já existe'}")
    print(f"  pastas a criar: {len(a_criar)}")
    print(f"  arquivos a mover: {len(presentes)} ({len(raiz)} na raiz, {len(presentes) - len(raiz)} na grade)")
    print(f"  no registro mas ausentes da origem (ignorados): {len(ausentes)}")
    for r in ausentes[:10]:
        print(f"    - {r}")
    if ja_no_destino:
        sys.exit(f"{len(ja_no_destino)} arquivos já existem no destino; ex.: {ja_no_destino[:3]}")
    if not executar:
        return
    if not presentes and not a_criar and not criar_base:
        print("nada a fazer")  # lista vazia no --files-from-raw faria o Rclone tratar a origem como arquivo
        return

    print(f"cópia do registro: {backup()}")
    if criar_base:
        rclone("mkdir", remoto(destino))
    # Nível por nível: criar a filha cria a mãe no servidor, e duas chamadas simultâneas sobre a
    # mesma mãe fazem o Rclone falhar com "is a directory not a file".
    niveis = sorted({p.count("/") for p in a_criar})
    with ThreadPoolExecutor(max_workers=6) as pool:
        for nivel in niveis:
            lote = [p for p in a_criar if p.count("/") == nivel]
            list(pool.map(lambda p: rclone("mkdir", remoto(f"{destino}/{p}")), lote))
    print(f"  pastas criadas: {len(a_criar)}")

    if presentes:
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as lista:
            lista.write("\n".join(presentes) + "\n")
        rclone("move", remoto(origem), remoto(destino), "--files-from-raw", lista.name, "--no-traverse",
               "--transfers", "4")

    conferidos = listar(destino, pastas=False) or set()
    movidos = [r for r in presentes if r in conferidos]
    with con:
        for r in movidos:
            con.execute("UPDATE anexos SET caminho_destino = ? WHERE caminho_destino = ?",
                        (f"{destino}/{r}", f"{prefixo}{r}"))
        limpar_leiame(con, origem, destino)
    faltaram = [r for r in presentes if r not in conferidos]
    print(f"  movidos e regravados no registro: {len(movidos)}")
    if faltaram:
        print(f"  NÃO conferidos no destino, registro mantido: {len(faltaram)}")
        for r in faltaram:
            print(f"    - {r}")
        sys.exit(1)
    print("feito")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="comando", required=True)
    p_mover = sub.add_parser("mover")
    p_renomear = sub.add_parser("renomear")
    for p in (p_mover, p_renomear):
        p.add_argument("origem")
        p.add_argument("destino")
        p.add_argument("--executar", action="store_true")
    p_mover.add_argument("--caixas", required=True, help="índices separados por vírgula, ex.: 3,4,5")
    args = parser.parse_args()
    origem, destino = args.origem.rstrip("/"), args.destino.rstrip("/")
    if args.comando == "renomear":
        cmd_renomear(origem, destino, args.executar)
    else:
        cmd_mover(origem, destino, [int(c) for c in args.caixas.split(",")], args.executar)


if __name__ == "__main__":
    main()
