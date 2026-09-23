"""Vencimento do documento e subpasta por vencimento (feature 003, cartão 2 do kanban).

O financeiro guarda cada documento em `NOTAS E BOLETOS POR VENCIMENTO/DIA <d>/202X-<mm>/`,
com dia e mês do vencimento e o ano literalmente `202X`, porque a grade se repete todo ano
(`docs/onedrive/estrutura-contas-a-pagar.md`, seção 1). As fontes, em ordem:

1. o XML de NF-e do próprio anexo (`cobr/dup/dVenc`, o mais cedo, quando há parcelas);
2. a linha digitável do próprio boleto, cujo fator de vencimento dá a data exata;
3. o vencimento da mensagem: o do XML de NF-e de outro anexo e, sem ele, o da linha digitável
   de um boleto irmão, de modo que DANFE, XML e boleto da mesma mensagem fiquem juntos;
4. uma data junto da palavra "vencimento" no texto do PDF.

As fontes do próprio anexo vêm antes das da mensagem para que o boleto de uma parcela não
herde o vencimento da primeira. Sem vencimento, o documento fica na raiz do destino.
"""

from __future__ import annotations

import io
import logging
import re
import unicodedata
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from pathlib import Path

from email_nf_onedrive.coleta.classificacao import NAMESPACE_NFE

PASTA_VENCIMENTOS = "NOTAS E BOLETOS POR VENCIMENTO"
PAGINAS_LIDAS = 3

# Febraban: fator 1000 era 2000-07-03 e, esgotado o 9999 em 2025-02-21, recomeçou em 1000.
_BASE_FATOR = date(1997, 10, 7)
_BASE_FATOR_2025 = date(2025, 2, 22)

# Boleto bancário, 47 dígitos: AAABC.CCCCX DDDDD.DDDDDY EEEEE.EEEEEZ K FFFFVVVVVVVVVV.
_LINHA_DIGITAVEL = re.compile(
    r"(?<!\d)(\d{5})[. ]?(\d{4})(\d)\s*(\d{5})[. ]?(\d{5})(\d)\s*(\d{5})[. ]?(\d{5})(\d)\s*(\d)\s*(\d{4})(\d{10})(?!\d)"
)
_DATA = r"(\d{2})[/.-](\d{2})[/.-](\d{4})"
_ROTULO = re.compile(r"venc(?:imentos?|to|\.)?")
_DATA_NO_TEXTO = re.compile(r"(?<!\d)" + _DATA + r"(?!\d)")
ALCANCE_DO_ROTULO = 80
# A emissão costuma vir ao lado do vencimento ("Data Emissão Data Vencimento" sobre
# "22/09/2026 02/10/2026") e cai no dia do recebimento ou antes; por isso só vale data posterior a ele.
# O documento que chega já vencido perde esta fonte e fica na raiz, que é o destino seguro.

logging.getLogger("pypdf").setLevel(logging.ERROR)  # PDFs malformados geram avisos que não interessam ao log


def _sem_acentos(texto: str) -> str:
    decomposto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in decomposto if not unicodedata.combining(c))


def _data(ano: str, mes: str, dia: str) -> date | None:
    try:
        return date(int(ano), int(mes), int(dia))
    except ValueError:
        return None


def vencimento_nfe(conteudo: bytes) -> date | None:
    """Primeiro vencimento das duplicatas de um XML de NF-e; None se não houver cobrança."""
    datas = []
    try:
        for _evento, elemento in ET.iterparse(io.BytesIO(conteudo), events=("end",)):
            if elemento.tag == f"{{{NAMESPACE_NFE}}}dVenc":
                achada = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", (elemento.text or "").strip())
                if achada and (valida := _data(*achada.groups())):
                    datas.append(valida)
    except ET.ParseError:
        pass
    return min(datas, default=None)


def _dv_modulo10(numero: str) -> int:
    soma = 0
    for i, digito in enumerate(reversed(numero)):
        produto = int(digito) * (2 if i % 2 == 0 else 1)
        soma += produto // 10 + produto % 10
    return (10 - soma % 10) % 10


def data_do_fator(fator: int, referencia: date) -> date | None:
    """Data do fator de vencimento; entre os dois ciclos, a mais próxima da referência."""
    if fator < 1000:
        return None  # 0000 é boleto sem vencimento
    candidatas = (_BASE_FATOR + timedelta(days=fator), _BASE_FATOR_2025 + timedelta(days=fator - 1000))
    return min(candidatas, key=lambda d: abs((d - referencia).days))


def vencimento_boleto(texto: str, referencia: date) -> date | None:
    """Vencimento da primeira linha digitável válida no texto."""
    for achada in _LINHA_DIGITAVEL.finditer(texto):
        g = achada.groups()
        campos = ((g[0] + g[1], g[2]), (g[3] + g[4], g[5]), (g[6] + g[7], g[8]))
        if all(_dv_modulo10(corpo) == int(dv) for corpo, dv in campos):
            return data_do_fator(int(g[10]), referencia)
    return None


def vencimento_texto(texto: str, referencia: date) -> date | None:
    """Primeira data válida, posterior ao recebimento, logo após "vencimento" (ou "venc.", "vencto")."""
    normalizado = _sem_acentos(texto).lower()
    for rotulo in _ROTULO.finditer(normalizado):
        trecho = normalizado[rotulo.end(): rotulo.end() + ALCANCE_DO_ROTULO]
        for achada in _DATA_NO_TEXTO.finditer(trecho):
            valida = _data(achada.group(3), achada.group(2), achada.group(1))
            if valida and valida > referencia:
                return valida
    return None


def texto_pdf(origem: Path | bytes) -> str:
    """Texto das primeiras páginas de um PDF, em arquivo ou em memória; vazio se não for PDF legível."""
    try:
        from pypdf import PdfReader

        leitor = PdfReader(io.BytesIO(origem) if isinstance(origem, bytes) else origem)
        return "\n".join((pagina.extract_text() or "") for pagina in leitor.pages[:PAGINAS_LIDAS])
    except Exception:  # PDF cifrado, corrompido ou que não é PDF: sem texto, sem vencimento
        return ""


def vencimento(caminho: Path, *, xml: bool, vencimento_mensagem: date | None, referencia: date) -> date | None:
    """Vencimento do anexo pelas fontes, em ordem; None se nenhuma o revelar."""
    if xml:
        return vencimento_nfe(caminho.read_bytes()) or vencimento_mensagem
    texto = texto_pdf(caminho) if caminho.suffix.lower() == ".pdf" else ""
    return vencimento_boleto(texto, referencia) or vencimento_mensagem or vencimento_texto(texto, referencia)


def vencimento_da_mensagem(anexos: list[tuple[str, bytes]], referencia: date) -> date | None:
    """Vencimento que vale para os anexos sem fonte própria: XML de NF-e primeiro, linha digitável depois."""
    for _nome, conteudo in anexos:
        if quando := vencimento_nfe(conteudo):
            return quando
    for nome, conteudo in anexos:
        if nome.lower().endswith(".pdf") and (quando := vencimento_boleto(texto_pdf(conteudo), referencia)):
            return quando
    return None


def pasta_vencimento(destino: str, quando: date | None) -> str:
    """`<destino>/NOTAS E BOLETOS POR VENCIMENTO/DIA <d>/202X-<mm>`; o próprio destino sem vencimento."""
    raiz = destino.rstrip("/")
    if quando is None:
        return raiz
    return f"{raiz}/{PASTA_VENCIMENTOS}/DIA {quando.day}/202X-{quando.month:02d}"
