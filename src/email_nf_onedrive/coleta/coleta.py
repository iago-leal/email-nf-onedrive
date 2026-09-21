"""Coleta dos anexos de cada caixa (spec coleta-email).

Por caixa: conecta, abre a pasta em somente leitura, calcula a janela, lê as
mensagens, extrai e classifica os anexos. Anexos `nfe-xml` e `palavra-chave` vão
para a pasta de trabalho e para o envio; `sem-classificacao` fica retido para
revisão (RN-03). A falha de uma caixa não interrompe as seguintes (RN-09).
"""

from __future__ import annotations

import logging
import os
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable

from email_nf_onedrive.coleta.classificacao import SEM_CLASSIFICACAO, classificar, contem_palavra_chave
from email_nf_onedrive.coleta.imap import AUTENTICACAO, PASTA, ClienteIMAP, ErroIMAP
from email_nf_onedrive.coleta.janela import data_de_corte
from email_nf_onedrive.coleta.mime import AnexoExtraido, MensagemAnalisada, analisar_mensagem
from email_nf_onedrive.configuracao.modelo import Caixa
from email_nf_onedrive.registro.banco import ESTADOS_PENDENTES, Registro

PROGRESSO_A_CADA = 50

FabricaIMAP = Callable[[Caixa], ClienteIMAP]


@dataclass(frozen=True)
class AnexoParaEnvio:
    anexo_id: int
    caminho_local: Path
    caixa: Caixa
    nome_original: str
    remetente: str
    data_mensagem: datetime
    sha256: str
    assunto: str = ""
    classe: str = ""


@dataclass(frozen=True)
class Falha:
    causa: str
    mensagem: str


@dataclass
class ResultadoCaixa:
    caixa: Caixa
    para_envio: list[AnexoParaEnvio] = field(default_factory=list)
    classes: Counter = field(default_factory=Counter)
    retidos: int = 0
    falha: Falha | None = None


def fabrica_imap_padrao(caixa: Caixa) -> ClienteIMAP:
    return ClienteIMAP(caixa.imap_host, caixa.imap_porta)


def _falha_imap(caixa: Caixa, erro: ErroIMAP) -> Falha:
    n = caixa.indice
    if erro.causa == AUTENTICACAO:
        mensagem = (f"caixa {n}: autenticação recusada. Ação: verifique a senha de app no .env "
                    f"(SENHA_EMAIL{n}) e se o IMAP está ativo no Google Workspace.")
    elif erro.causa == PASTA:
        mensagem = f"caixa {n}: pasta '{caixa.pasta}' inexistente. Ação: corrija PASTA_EMAIL{n}; as pastas disponíveis estão no log."
    else:
        mensagem = f"caixa {n}: servidor IMAP inacessível ({erro.detalhe}). Nova tentativa na próxima execução."
    return Falha(f"caixa{n}:{erro.causa}", mensagem)


class _ColetorCaixa:
    def __init__(self, caixa: Caixa, registro: Registro, pasta_trabalho: Path, logger: logging.Logger) -> None:
        self.caixa = caixa
        self.registro = registro
        self.pasta_trabalho = pasta_trabalho
        self.extra = {"caixa": caixa.indice}
        self.log = logger
        self.resultado = ResultadoCaixa(caixa)
        self._enfileirados: set[int] = set()

    def _gravar(self, anexo_id: int, anexo: AnexoExtraido) -> Path:
        extensao = Path(anexo.nome).suffix.lower() or ".bin"
        caminho = self.pasta_trabalho / f"{anexo_id}-{anexo.sha256[:12]}{extensao}"
        fd = os.open(caminho, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "wb") as arquivo:
            arquivo.write(anexo.conteudo)
        return caminho

    def _ocorrencia(self, msg: MensagemAnalisada, tipo: str, texto: str) -> None:
        if self.registro.registrar_ocorrencia(self.caixa.endereco, msg.message_id, tipo):
            self.log.warning("%s: remetente %s, assunto %r, data %s", texto, msg.remetente, msg.assunto,
                             msg.data.isoformat() if msg.data else "?", extra=self.extra)

    def processar(self, bruto: bytes) -> None:
        msg = analisar_mensagem(bruto)
        data = msg.data or datetime.now(timezone.utc)
        for nome in msg.compactados:
            self._ocorrencia(msg, "compactado", f"anexo compactado ignorado ({nome})")
        if not msg.anexos and contem_palavra_chave(msg.assunto):
            self._ocorrencia(msg, "sem-anexo", "possível documento sem anexo")

        for anexo in msg.anexos:
            existente = self.registro.buscar(self.caixa.endereco, msg.message_id, anexo.sha256)
            if existente is not None:
                if existente.estado in ESTADOS_PENDENTES:  # fluxo alternativo A: nova tentativa de envio
                    self._para_envio(existente.id, anexo, msg, data, existente.classe)
                continue
            classe = classificar(anexo.nome, msg.assunto, anexo.conteudo)
            self.resultado.classes[classe] += 1
            campos = dict(
                caixa_endereco=self.caixa.endereco, caixa_indice=self.caixa.indice, message_id=msg.message_id,
                sha256=anexo.sha256, nome_original=anexo.nome, remetente=msg.remetente, assunto=msg.assunto,
                data_mensagem=data, classe=classe,
            )
            if classe == SEM_CLASSIFICACAO:
                self.registro.registrar_anexo(**campos, estado="retido")
                self.resultado.retidos += 1
                self.log.warning("retido para revisão: %s (remetente %s, assunto %r)",
                                 anexo.nome, msg.remetente, msg.assunto, extra=self.extra)
                continue
            novo = self.registro.registrar_anexo(**campos, estado="extraido")
            self.log.info("extraído: %s (%s, sha256 %s, remetente %s, assunto %r)", anexo.nome, classe,
                          anexo.sha256, msg.remetente, msg.assunto, extra=self.extra)
            self._para_envio(novo.id, anexo, msg, data, classe)

    def _para_envio(self, anexo_id: int, anexo: AnexoExtraido, msg: MensagemAnalisada, data: datetime,
                    classe: str) -> None:
        if anexo_id in self._enfileirados:  # mesmo anexo repetido na mensagem ou na pasta
            return
        self._enfileirados.add(anexo_id)
        self.resultado.para_envio.append(AnexoParaEnvio(
            anexo_id=anexo_id, caminho_local=self._gravar(anexo_id, anexo), caixa=self.caixa,
            nome_original=anexo.nome, remetente=msg.remetente, data_mensagem=data, sha256=anexo.sha256,
            assunto=msg.assunto, classe=classe,
        ))

    def executar(self, fabrica: FabricaIMAP, data_inicial: date) -> ResultadoCaixa:
        caixa = self.caixa
        corte = data_de_corte(
            data_inicial,
            ultima_mensagem=self.registro.ultima_data_mensagem(caixa.endereco),
            pendente_mais_antiga=self.registro.pendente_mais_antiga(caixa.endereco),
        )
        cliente = fabrica(caixa)
        try:
            cliente.conectar(caixa.endereco, caixa.senha)
            self.log.info("caixa %d: conectada", caixa.indice, extra=self.extra)
            try:
                cliente.examinar(caixa.pasta)
            except ErroIMAP as erro:
                if erro.causa == PASTA:
                    self.log.error("pastas existentes na caixa: %s", ", ".join(cliente.listar_pastas()),
                                   extra=self.extra)
                raise
            numeros = cliente.buscar_desde(corte)
            self.log.info("caixa %d: %d mensagens desde %s", caixa.indice, len(numeros), corte.isoformat(),
                          extra=self.extra)
            for posicao, numero in enumerate(numeros, start=1):
                self.processar(cliente.obter(numero))
                self.registro.commit()
                if posicao % PROGRESSO_A_CADA == 0:
                    self.log.info("progresso: %d de %d mensagens", posicao, len(numeros), extra=self.extra)
        except ErroIMAP as erro:
            self.resultado.falha = _falha_imap(caixa, erro)
            self.log.error("%s", self.resultado.falha.mensagem, extra=self.extra)
        finally:
            cliente.encerrar()
        self._resumir()
        return self.resultado

    def _resumir(self) -> None:
        classes = self.resultado.classes
        total = sum(classes.values())
        if total == 0:
            self.log.info("caixa %d: nenhum anexo novo", self.caixa.indice, extra=self.extra)
            return
        detalhe = ", ".join(f"{classes[c]} {c}" for c in ("nfe-xml", "palavra-chave", "sem-classificacao"))
        self.log.info("caixa %d: %d anexos novos (%s)", self.caixa.indice, total, detalhe, extra=self.extra)


def coletar(caixas: tuple[Caixa, ...], registro: Registro, pasta_trabalho: Path, data_inicial: date,
            logger: logging.Logger, fabrica: FabricaIMAP = fabrica_imap_padrao) -> list[ResultadoCaixa]:
    """Coleta as caixas em sequência, na ordem dos índices (CE RF-10)."""
    pasta_trabalho.mkdir(parents=True, exist_ok=True, mode=0o700)
    return [
        _ColetorCaixa(caixa, registro, pasta_trabalho, logger).executar(fabrica, data_inicial)
        for caixa in sorted(caixas, key=lambda c: c.indice)
    ]
