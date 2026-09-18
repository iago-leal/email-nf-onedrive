"""UTF-7 modificado para nomes de pasta IMAP (RFC 3501, seção 5.1.3).

Caracteres ASCII imprimíveis passam como estão, `&` vira `&-`, e trechos com
outros caracteres viram `&<base64 modificado de UTF-16BE>-`, com `,` no lugar de `/`.
"""

from __future__ import annotations

import base64


def _eh_direto(caractere: str) -> bool:
    return 0x20 <= ord(caractere) <= 0x7E


def _codificar_trecho(trecho: str) -> str:
    b64 = base64.b64encode(trecho.encode("utf-16-be")).decode("ascii")
    return "&" + b64.rstrip("=").replace("/", ",") + "-"


def codificar(nome: str) -> str:
    partes: list[str] = []
    pendente: list[str] = []
    for caractere in nome:
        if _eh_direto(caractere):
            if pendente:
                partes.append(_codificar_trecho("".join(pendente)))
                pendente = []
            partes.append("&-" if caractere == "&" else caractere)
        else:
            pendente.append(caractere)
    if pendente:
        partes.append(_codificar_trecho("".join(pendente)))
    return "".join(partes)


def decodificar(nome: str) -> str:
    partes: list[str] = []
    i = 0
    while i < len(nome):
        if nome[i] != "&":
            partes.append(nome[i])
            i += 1
            continue
        fim = nome.index("-", i)
        trecho = nome[i + 1 : fim]
        if not trecho:
            partes.append("&")
        else:
            b64 = trecho.replace(",", "/")
            b64 += "=" * (-len(b64) % 4)
            partes.append(base64.b64decode(b64).decode("utf-16-be"))
        i = fim + 1
    return "".join(partes)
