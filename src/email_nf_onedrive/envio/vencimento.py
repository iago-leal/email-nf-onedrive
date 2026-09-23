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
herde o vencimento da primeira. Sem vencimento, o documento fica na raiz do destino, com o
motivo apurado para o sumário LEIAME da raiz (feature 006).
"""

from __future__ import annotations

import io
import logging
import re
import unicodedata
import xml.etree.ElementTree as ET
from dataclasses import dataclass
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
    r"(?<!\d)(\d{5})[. ]?(\d{4})(\d)\s*(\d{5})[. ]?(\d{5})(\d)\s*(\d{5})[. ]?(\d{5})(\d)\s*(\d)\s*(\d{4})(\d{10})"
)
# Sem âncora no fim: o extrator de texto às vezes cola dígitos ao valor, e os três dígitos
# verificadores já descartam a sequência que não for linha digitável (adendo 003-v002).
_DATA = r"(\d{2})[/.-](\d{2})[/.-](\d{4})"
_ROTULO = re.compile(r"venc(?:imentos?|to|\.)?|duplicatas?")
_COLADA_AO_ROTULO = re.compile(r"[\s:.]*" + _DATA)
_DATA_NO_TEXTO = re.compile(r"(?<!\d)" + _DATA + r"(?!\d)")
ALCANCE_DO_ROTULO = 80
# A emissão costuma vir ao lado do vencimento ("Data Emissão Data Vencimento" sobre
# "22/09/2026 02/10/2026") e cai no dia do recebimento ou antes; por isso só vale data posterior a ele.
# A exceção é a data colada ao rótulo ("Vencimento: 19/09/2026"), que vale mesmo no dia do recebimento.
# O documento que chega já vencido perde esta fonte e fica na raiz, que é o destino seguro.

# Motivos da raiz, na linguagem do financeiro, que os lê no sumário LEIAME (feature 006).
MOTIVO_A_VISTA = "nota paga à vista: não há parcela a vencer"
MOTIVO_SEM_FATURA = "nota fiscal sem fatura: o XML não traz vencimento"
MOTIVO_SERVICO = "nota fiscal de serviço: não traz vencimento"
MOTIVO_DANFE = "nota fiscal (DANFE) sem vencimento identificável"
MOTIVO_ILEGIVEL = "documento sem texto legível (digitalizado ou com fonte embutida): o vencimento só seria lido com OCR"
MOTIVO_FORMATO = "imagem ou formato sem texto: o vencimento não é lido"
MOTIVO_NAO_LOCALIZADO = "vencimento não localizado no documento"
MINIMO_DE_PALAVRAS = 10  # abaixo disso o PDF é imagem, ou a fonte não tem mapa de caracteres ("/0/1 /2 /3")
_PALAVRA = re.compile(r"[a-z]{3,}")
_SERVICO = re.compile(r"nfs-?e|nota fiscal (?:eletronica )?de servicos?|prestacao de servicos?|prestador de servicos?")
_DANFE = re.compile(r"danf-?e|documento auxiliar da nota")

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
    """Primeira data válida, posterior ao recebimento, logo após "vencimento" (ou "venc.", "vencto", "duplicata").

    A data colada ao rótulo vale também quando cai no próprio dia do recebimento.
    """
    normalizado = _sem_acentos(texto).lower()
    for rotulo in _ROTULO.finditer(normalizado):
        trecho = normalizado[rotulo.end(): rotulo.end() + ALCANCE_DO_ROTULO]
        colada = _COLADA_AO_ROTULO.match(trecho)
        if colada and (valida := _data(colada.group(3), colada.group(2), colada.group(1))) and valida >= referencia:
            return valida
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


@dataclass(frozen=True)
class Leitura:
    """Vencimento do anexo ou, sem ele, o motivo pelo qual o documento fica na raiz."""

    quando: date | None
    motivo: str = ""


def _nfe_a_vista(conteudo: bytes) -> bool:
    try:
        for _evento, elemento in ET.iterparse(io.BytesIO(conteudo), events=("end",)):
            if elemento.tag == f"{{{NAMESPACE_NFE}}}indPag" and (elemento.text or "").strip() == "0":
                return True
    except ET.ParseError:
        pass
    return False


def vencido_ao_chegar(texto: str, referencia: date) -> date | None:
    """Vencimento anterior ao recebimento: o documento já chegou vencido.

    Vale a data colada a "vencimento" e a primeira data do quadro de duplicatas; a data solta
    perto de "vencimento" pode ser a emissão, e por isso não é tomada como vencida.
    """
    normalizado = _sem_acentos(texto).lower()
    for rotulo in _ROTULO.finditer(normalizado):
        if rotulo.group().startswith("duplicata"):
            achada = _DATA_NO_TEXTO.search(normalizado[rotulo.end(): rotulo.end() + ALCANCE_DO_ROTULO])
        else:
            achada = _COLADA_AO_ROTULO.match(normalizado, rotulo.end())
        if achada and (valida := _data(achada.group(3), achada.group(2), achada.group(1))) and valida < referencia:
            return valida
    return None


def _motivo_pdf(texto: str, referencia: date) -> str:
    normalizado = _sem_acentos(texto).lower()
    if len(_PALAVRA.findall(normalizado)) < MINIMO_DE_PALAVRAS:
        return MOTIVO_ILEGIVEL
    if vencido := vencido_ao_chegar(texto, referencia):
        return f"já chegou vencido: venceu em {vencido:%d/%m/%Y}"
    if _SERVICO.search(normalizado):
        return MOTIVO_SERVICO
    if _DANFE.search(normalizado):
        return MOTIVO_DANFE
    return MOTIVO_NAO_LOCALIZADO


def ler(caminho: Path, *, xml: bool, vencimento_mensagem: date | None, referencia: date) -> Leitura:
    """Vencimento do anexo pelas fontes, em ordem, ou o motivo de não haver nenhum."""
    if xml:
        conteudo = caminho.read_bytes()
        if quando := vencimento_nfe(conteudo) or vencimento_mensagem:
            return Leitura(quando)
        return Leitura(None, MOTIVO_A_VISTA if _nfe_a_vista(conteudo) else MOTIVO_SEM_FATURA)
    if caminho.suffix.lower() != ".pdf":
        return Leitura(vencimento_mensagem, "" if vencimento_mensagem else MOTIVO_FORMATO)
    texto = texto_pdf(caminho)
    if quando := vencimento_boleto(texto, referencia) or vencimento_mensagem or vencimento_texto(texto, referencia):
        return Leitura(quando)
    return Leitura(None, _motivo_pdf(texto, referencia))


def vencimento(caminho: Path, *, xml: bool, vencimento_mensagem: date | None, referencia: date) -> date | None:
    """Vencimento do anexo pelas fontes, em ordem; None se nenhuma o revelar."""
    return ler(caminho, xml=xml, vencimento_mensagem=vencimento_mensagem, referencia=referencia).quando


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
