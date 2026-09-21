"""Convenção de nomes no OneDrive (D-12), fechada na L-03 em 2026-09-21.

Segue o padrão apurado em 2.304 arquivos da pasta `CONTAS A PAGAR`
(`docs/onedrive/estrutura-contas-a-pagar.md`, seção 3):

    <EMPRESA> - <FORNECEDOR>[ NF <n>] - <TIPO>.<ext>

- EMPRESA vem de `EMPRESA_EMAIL<n>` no .env; sem ele, do domínio da caixa.
- FORNECEDOR vem do emitente da NF-e (XML) ou do domínio do remetente.
- NF <n> vem do XML ou do primeiro número de nota no nome do anexo ou no assunto.
- TIPO é `BOLETO` quando o nome ou o assunto falam em boleto, e `REF` (a nota) nos demais.

O financeiro acrescenta ` - REF <n>` e ` - OK` à mão; a ferramenta não conhece
esses números. Toda a regra de nomes vive neste módulo para que a troca não
afete o restante do envio.
"""

from __future__ import annotations

import io
import re
import unicodedata
import xml.etree.ElementTree as ET
from dataclasses import dataclass

from email_nf_onedrive.coleta.classificacao import NAMESPACE_NFE, NFE_XML

LIMITE_NOME = 200
TIPO_NOTA = "REF"
TIPO_BOLETO = "BOLETO"

# Provedores genéricos não identificam fornecedor; nesses casos vale a parte local do endereço.
DOMINIOS_GENERICOS = frozenset({
    "gmail", "googlemail", "hotmail", "outlook", "live", "msn", "yahoo", "icloud", "me", "uol", "bol", "terra",
})

_INVALIDOS = re.compile(r'["*:<>?/\\|]')
_ESPACOS = re.compile(r" {2,}")
_RESERVADOS = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(10)), *(f"LPT{i}" for i in range(10))}
_NOMES_RESERVADOS = {".lock", "desktop.ini"}
_SEPARADORES = re.compile(r"[._\-]+")
_BOLETO = re.compile(r"(?<![a-z])boleto(?![a-z])")
# "NF 123", "NF-e nº 123", "NFS-e 123", "nota fiscal n. 123", "DANFE 123"; o número vai até 9 dígitos.
_NUMERO_NF = re.compile(
    r"(?<![a-z])(?:nfs?[-_ ]?e|nf|nota[-_ ]+fiscal|danfe)[-_ ]*(?:n[º°o.]?|num(?:ero)?\.?|#)?[-_ :]*(\d{1,9})(?!\d)"
)


@dataclass(frozen=True)
class DadosNome:
    """O que a nomeação precisa saber de um anexo, independente de onde veio."""

    empresa: str
    remetente: str
    nome_original: str
    assunto: str = ""
    classe: str = ""
    conteudo: bytes | None = None


def _sem_acentos(texto: str) -> str:
    decomposto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in decomposto if not unicodedata.combining(c))


def _separar_extensao(nome: str) -> tuple[str, str]:
    if "." in nome[1:]:
        base, ext = nome.rsplit(".", 1)
        return base, "." + ext
    return nome, ""


def _truncar(nome: str) -> str:
    if len(nome) <= LIMITE_NOME:
        return nome
    base, ext = _separar_extensao(nome)
    return base[: LIMITE_NOME - len(ext)] + ext


def sanear(nome: str) -> str:
    """Remove o que o OneDrive recusa e limita o nome a 200 caracteres (EO RF-02)."""
    nome = _INVALIDOS.sub("", nome)
    nome = _ESPACOS.sub(" ", nome).strip(" ").rstrip(".").strip(" ")
    nome = nome.replace("_vti_", "_vti-")
    if not nome:
        return "anexo"
    base, _ext = _separar_extensao(nome)
    if nome.lower() in _NOMES_RESERVADOS or base.upper() in _RESERVADOS:
        nome = "_" + nome
    return _truncar(nome)


def _rotulo(texto: str) -> str:
    """Rótulo em maiúsculas, sem acento nem separadores, como os nomes da pasta."""
    texto = _SEPARADORES.sub(" ", _sem_acentos(texto)).upper()
    return _ESPACOS.sub(" ", _INVALIDOS.sub("", texto)).strip(" ")


def rotulo_do_endereco(endereco: str) -> str:
    """`cobranca@fornecedor.com.br` vira `FORNECEDOR`; `fulano@gmail.com` vira `FULANO`."""
    local, _, dominio = endereco.strip().lower().partition("@")
    primeiro = dominio.split(".", 1)[0] if dominio else ""
    escolhido = local if not primeiro or primeiro in DOMINIOS_GENERICOS else primeiro
    return _rotulo(escolhido) or "REMETENTE"


def dados_nfe(conteudo: bytes) -> tuple[str, str]:
    """(nome do emitente, número da nota) de um XML de NF-e; vazios se não estiverem lá."""
    emitente = numero = ""
    try:
        for _evento, elemento in ET.iterparse(io.BytesIO(conteudo), events=("end",)):
            if elemento.tag == f"{{{NAMESPACE_NFE}}}xNome" and not emitente:
                emitente = (elemento.text or "").strip()  # o primeiro xNome do documento é o do emitente
            elif elemento.tag == f"{{{NAMESPACE_NFE}}}nNF" and not numero:
                numero = (elemento.text or "").strip()
            if emitente and numero:
                break
    except ET.ParseError:
        pass
    return emitente, numero


def _numero_nf(*textos: str) -> str:
    for texto in textos:
        achado = _NUMERO_NF.search(_sem_acentos(texto).lower())
        if achado:
            return achado.group(1).lstrip("0") or "0"
    return ""


def _tipo(dados: DadosNome) -> str:
    if dados.classe == NFE_XML:
        return TIPO_NOTA
    if _BOLETO.search(_sem_acentos(dados.nome_original + " " + dados.assunto).lower()):
        return TIPO_BOLETO
    return TIPO_NOTA


def nome_destino(dados: DadosNome) -> str:
    """`<EMPRESA> - <FORNECEDOR>[ NF <n>] - <TIPO>.<ext>`, com a extensão original em minúsculas."""
    empresa = _rotulo(dados.empresa) or rotulo_do_endereco(dados.remetente)
    fornecedor, numero = "", ""
    if dados.classe == NFE_XML and dados.conteudo is not None:
        emitente, numero = dados_nfe(dados.conteudo)
        fornecedor = _rotulo(emitente)
    fornecedor = fornecedor or rotulo_do_endereco(dados.remetente)
    numero = numero.lstrip("0") or _numero_nf(dados.nome_original, dados.assunto)
    nota = f" NF {numero}" if numero else ""
    _base, ext = _separar_extensao(dados.nome_original.strip())
    return sanear(f"{empresa} - {fornecedor}{nota} - {_tipo(dados)}{ext.lower()}")


def caminho_destino(destino: str, dados: DadosNome) -> str:
    """Caminho relativo ao remote: pasta de destino mais o nome padronizado."""
    return f"{destino.rstrip('/')}/{nome_destino(dados)}"


def com_sufixo(nome: str, n: int) -> str:
    """Acrescenta `_n` antes da extensão, respeitando o limite de tamanho (EO RF-04)."""
    base, ext = _separar_extensao(nome)
    sufixo = f"_{n}{ext}"
    return base[: LIMITE_NOME - len(sufixo)] + sufixo
