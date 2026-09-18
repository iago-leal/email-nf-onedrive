"""Comando `testar-onedrive`: prova de escrita no destino (EO RF-09).

Grava um arquivo de 1 KB com nome exclusivo, confirma-o e apaga só ele, pelo
caminho exato. Nada mais na pasta é tocado.
"""

from __future__ import annotations

import os
import tempfile
import uuid
from pathlib import Path

from email_nf_onedrive.envio.rclone import ErroRclone, Rclone

TAMANHO_TESTE = 1024


def testar_onedrive(rclone: Rclone, destino: str) -> tuple[bool, str]:
    try:
        if not rclone.pasta_existe(destino):
            return False, f"OneDrive: destino não encontrado: {destino}"
        nome = f".email-nf-onedrive-teste-{uuid.uuid4()}.txt"
        remoto = f"{destino.rstrip('/')}/{nome}"
        with tempfile.TemporaryDirectory() as temporario:
            local = Path(temporario) / nome
            local.write_bytes(os.urandom(TAMANHO_TESTE // 2).hex().encode()[:TAMANHO_TESTE])
            rclone.copiar(local, remoto)
        objeto = rclone.estatistica(remoto)
        if objeto is None or objeto.tamanho != TAMANHO_TESTE:
            return False, f"OneDrive: arquivo de teste não confirmado em {destino}"
        rclone.apagar_arquivo_de_teste(remoto)
    except ErroRclone as erro:
        return False, f"OneDrive: falha ({erro.causa}): {erro.detalhe}"
    return True, f"OneDrive: escrita confirmada em {destino}"
