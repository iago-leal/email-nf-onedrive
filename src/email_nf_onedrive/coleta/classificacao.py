"""Classificação dos anexos em nfe-xml, palavra-chave ou sem-classificacao (D-07).

Só as duas primeiras classes seguem para o OneDrive; `sem-classificacao` fica
retido para revisão manual (RN-03).
"""

from __future__ import annotations

import io
import re
import unicodedata
import xml.etree.ElementTree as ET

NAMESPACE_NFE = "http://www.portalfiscal.inf.br/nfe"
RAIZES_NFE = frozenset({f"{{{NAMESPACE_NFE}}}nfeProc", f"{{{NAMESPACE_NFE}}}NFe"})
LIMITE_XML_BYTES = 10 * 1024 * 1024

# Lista única de palavras-chave (CE RF-06). Ampliá-la aqui vale para nome e assunto.
PALAVRAS_CHAVE = (
    "nf", "nfe", "nf-e", "nfs-e", "nota fiscal", "danfe", "boleto", "fatura", "cobranca", "duplicata",
)

NFE_XML = "nfe-xml"
PALAVRA_CHAVE = "palavra-chave"
SEM_CLASSIFICACAO = "sem-classificacao"


def _normalizar(texto: str) -> str:
    decomposto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in decomposto if not unicodedata.combining(c)).lower()


def _padrao(termo: str) -> str:
    # Hífen e espaço aceitam variações comuns em nomes de arquivo: nf-e, nf_e, nfe, nota_fiscal.
    corpo = re.escape(termo).replace(r"\-", "[-_ ]?").replace(r"\ ", "[-_ ]+")
    # Fronteira só de letras: "NF123" casa, "info" e "conforme" não.
    return rf"(?<![a-z]){corpo}(?![a-z])"


_REGEX_PALAVRAS = re.compile("|".join(_padrao(termo) for termo in PALAVRAS_CHAVE))


def contem_palavra_chave(texto: str) -> bool:
    return bool(_REGEX_PALAVRAS.search(_normalizar(texto)))


def eh_nfe_xml(conteudo: bytes) -> bool:
    """Verifica se o XML é bem formado e tem a raiz de uma NF-e.

    O documento é lido até o fim, e não só até a raiz, porque um XML truncado
    precisa cair nas regras de texto (CE EC-07). O limite de tamanho contém o custo.
    """
    if len(conteudo) > LIMITE_XML_BYTES or not conteudo.lstrip(b"\xef\xbb\xbf \t\r\n").startswith(b"<"):
        return False
    raiz = None
    try:
        for _evento, elemento in ET.iterparse(io.BytesIO(conteudo), events=("start",)):
            if raiz is None:
                raiz = elemento.tag
    except ET.ParseError:
        return False
    return raiz in RAIZES_NFE


def classificar(nome_arquivo: str, assunto: str, conteudo: bytes) -> str:
    if eh_nfe_xml(conteudo):
        return NFE_XML
    if contem_palavra_chave(nome_arquivo) or contem_palavra_chave(assunto):
        return PALAVRA_CHAVE
    return SEM_CLASSIFICACAO
