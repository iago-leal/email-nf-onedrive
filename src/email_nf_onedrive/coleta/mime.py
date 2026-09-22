"""Extração de anexos PDF e XML de uma mensagem (D-06, CE RF-04)."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email import message_from_bytes, policy
from email.message import EmailMessage
from email.utils import parseaddr, parsedate_to_datetime

EXTENSOES_DOCUMENTO = {".pdf": "pdf", ".xml": "xml"}
TIPOS_DOCUMENTO = {"application/pdf": "pdf", "application/xml": "xml", "text/xml": "xml"}
EXTENSOES_COMPACTADAS = (".zip", ".rar", ".7z")
TIPOS_COMPACTADOS = {"application/zip", "application/x-zip-compressed", "application/x-rar-compressed",
                     "application/vnd.rar", "application/x-7z-compressed"}
# Linha "De:"/"From:" de encaminhamento em linha ou de citação (Gmail, Outlook); só conta com endereço nela.
_LINHA_REMETENTE = re.compile(r"^[>\s]*\**(?:from|de)\**\s*:\**\s*(.*)$", re.IGNORECASE | re.MULTILINE)
_ENDERECO = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")


@dataclass(frozen=True)
class AnexoExtraido:
    nome: str
    conteudo: bytes = field(repr=False)

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.conteudo).hexdigest()


@dataclass(frozen=True)
class MensagemAnalisada:
    message_id: str
    remetente: str
    assunto: str
    data: datetime | None
    anexos: tuple[AnexoExtraido, ...]
    compactados: tuple[str, ...]
    remetentes_encaminhados: tuple[str, ...] = ()  # do original ao mais recente, sem o From de topo


def _extensao(nome: str | None) -> str:
    if not nome or "." not in nome:
        return ""
    return "." + nome.rsplit(".", 1)[1].lower()


def _tipo_documento(parte: EmailMessage, nome: str | None) -> str | None:
    return EXTENSOES_DOCUMENTO.get(_extensao(nome)) or TIPOS_DOCUMENTO.get(parte.get_content_type())


def _eh_compactado(parte: EmailMessage, nome: str | None) -> bool:
    return _extensao(nome) in EXTENSOES_COMPACTADAS or parte.get_content_type() in TIPOS_COMPACTADOS


def _percorrer(mensagem: EmailMessage):
    """Percorre as partes-folha, descendo em mensagens encaminhadas (message/rfc822)."""
    for parte in mensagem.walk():
        if parte.get_content_type() == "message/rfc822":
            continue  # walk() já desce no conteúdo embutido
        if not parte.is_multipart():
            yield parte


def _data(mensagem: EmailMessage) -> datetime | None:
    valor = mensagem.get("Date")
    if not valor:
        return None
    try:
        data = parsedate_to_datetime(str(valor))
    except (TypeError, ValueError):
        return None
    if data.tzinfo is None:
        data = data.replace(tzinfo=timezone.utc)
    return data.astimezone(timezone.utc)


def _remetentes_encaminhados(mensagem: EmailMessage) -> tuple[str, ...]:
    """Remetentes das mensagens encaminhadas, do original ao mais recente.

    Vêm do `From` das partes `message/rfc822` e das linhas `De:`/`From:` com endereço nos corpos
    em texto, onde o Gmail e o Outlook põem o cabeçalho do encaminhamento em linha.
    """
    achados: list[str] = []
    for parte in mensagem.walk():
        tipo = parte.get_content_type()
        if tipo == "message/rfc822":
            endereco = parseaddr(str(parte.get_content().get("From", "")))[1].lower()
            if endereco:
                achados.append(endereco)
        elif tipo == "text/plain" and parte.get_content_disposition() != "attachment":
            try:
                texto = parte.get_content()
            except (LookupError, UnicodeError):
                continue
            for linha in _LINHA_REMETENTE.finditer(texto):
                endereco = _ENDERECO.search(linha.group(1))
                if endereco:
                    achados.append(endereco.group(0).lower())
    return tuple(reversed(achados))


def analisar_mensagem(bruto: bytes) -> MensagemAnalisada:
    mensagem = message_from_bytes(bruto, policy=policy.default)
    remetente = parseaddr(str(mensagem.get("From", "")))[1].lower()
    assunto = str(mensagem.get("Subject", "")).strip()
    data = _data(mensagem)
    message_id = str(mensagem.get("Message-ID", "")).strip()
    if not message_id:
        # Fluxo alternativo B: identificador substituto estável.
        base = f"{remetente}\n{mensagem.get('Date', '')}\n{assunto}".encode()
        message_id = "sem-id:" + hashlib.sha256(base).hexdigest()

    anexos: list[AnexoExtraido] = []
    compactados: list[str] = []
    posicao = 0
    for parte in _percorrer(mensagem):
        nome = parte.get_filename()
        tipo = _tipo_documento(parte, nome)
        if tipo is None:
            if _eh_compactado(parte, nome):
                compactados.append(nome or "anexo-compactado")
            continue
        if parte.get_content_disposition() != "attachment" and not nome:
            continue  # parte inline sem nome não é anexo (ex.: corpo XML embutido)
        conteudo = parte.get_payload(decode=True) or b""
        posicao += 1
        anexos.append(AnexoExtraido(nome=nome or f"anexo-{posicao}.{tipo}", conteudo=conteudo))

    return MensagemAnalisada(
        message_id=message_id,
        remetente=remetente,
        assunto=assunto,
        data=data,
        anexos=tuple(anexos),
        compactados=tuple(compactados),
        remetentes_encaminhados=_remetentes_encaminhados(mensagem),
    )
