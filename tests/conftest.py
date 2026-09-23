"""Fixtures compartilhadas pelos testes."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

DADOS = Path(__file__).parent / "dados"


@pytest.fixture
def dados() -> Path:
    """Diretório com e-mails e XMLs sintéticos."""
    return DADOS


@pytest.fixture
def home(tmp_path: Path) -> Path:
    """Diretório de instalação temporário, com a subpasta var/."""
    (tmp_path / "var").mkdir()
    return tmp_path


@pytest.fixture
def escrever_env(home: Path):
    """Fábrica que grava home/.env a partir de um dicionário."""

    def _escrever(variaveis: dict[str, str], modo: int = 0o600) -> Path:
        caminho = home / ".env"
        linhas = [f"{chave}={valor}" for chave, valor in variaveis.items()]
        caminho.write_text("\n".join(linhas) + "\n", encoding="utf-8")
        os.chmod(caminho, modo)
        return caminho

    return _escrever


class Relogio:
    """Relógio controlável, injetado onde o código consulta a hora."""

    def __init__(self, inicio: datetime) -> None:
        self.atual = inicio

    def agora(self) -> datetime:
        return self.atual

    def avancar(self, **kwargs: float) -> datetime:
        self.atual += timedelta(**kwargs)
        return self.atual


@pytest.fixture
def relogio() -> Relogio:
    return Relogio(datetime(2026, 9, 18, 12, 0, tzinfo=timezone.utc))


@pytest.fixture(autouse=True)
def _limpar_segredos():
    """Isola o registro global de segredos entre testes."""
    try:
        from email_nf_onedrive import segredos
    except ImportError:
        yield
        return
    segredos.limpar()
    yield
    segredos.limpar()


def pdf_com_texto(*linhas: str) -> bytes:
    """PDF mínimo de uma página com as linhas em texto extraível (feature 003)."""
    texto = " ".join(
        f"({linha.replace(chr(92), chr(92) * 2).replace('(', r'\(').replace(')', r'\)')}) Tj 0 -14 Td" for linha in linhas
    )
    fluxo = f"BT /F1 10 Tf 40 800 Td {texto} ET".encode("latin-1")
    objetos = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(fluxo) + fluxo + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
    ]
    saida = bytearray(b"%PDF-1.4\n")
    posicoes = []
    for n, corpo in enumerate(objetos, 1):
        posicoes.append(len(saida))
        saida += b"%d 0 obj\n" % n + corpo + b"\nendobj\n"
    xref = len(saida)
    saida += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objetos) + 1)
    saida += b"".join(b"%010d 00000 n \n" % p for p in posicoes)
    saida += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objetos) + 1, xref)
    return bytes(saida)


def nfe_com_vencimentos(*datas: str, emitente: str = "FORNECEDOR FICTICIO LTDA", numero: str = "1234",
                        a_vista: bool = False) -> bytes:
    """XML de NF-e sintético com uma duplicata por data `AAAA-MM-DD` (feature 003); `a_vista` põe o pagamento à vista."""
    duplicatas = "".join(f"<dup><nDup>{i:03d}</nDup><dVenc>{d}</dVenc></dup>" for i, d in enumerate(datas, 1))
    cobranca = f"<cobr>{duplicatas}</cobr>" if datas else ""
    if a_vista:
        cobranca += "<pag><detPag><indPag>0</indPag><tPag>01</tPag><vPag>10.00</vPag></detPag></pag>"
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00"><NFe><infNFe versao="4.00">'
        f"<ide><nNF>{numero}</nNF></ide><emit><CNPJ>00000000000191</CNPJ><xNome>{emitente}</xNome></emit>"
        f"{cobranca}</infNFe></NFe></nfeProc>"
    ).encode()
