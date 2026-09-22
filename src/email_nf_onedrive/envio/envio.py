"""Envio dos anexos ao OneDrive (spec envio-onedrive, interfaces/rclone-onedrive.md).

Protocolo por anexo: confirma que a pasta de destino existe (sem criá-la), escolhe
o nome livre ou reconhece arquivo idêntico já presente, envia sem sobrescrever e
só marca `enviado` depois de confirmar tamanho e hash no destino (RN-04). A cópia
local é apagada logo após a confirmação (RN-07).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

from email_nf_onedrive.coleta.classificacao import NFE_XML
from email_nf_onedrive.coleta.coleta import AnexoParaEnvio, Falha
from email_nf_onedrive.envio import nomeacao
from email_nf_onedrive.envio.rclone import ACESSO, CONFIG, TOKEN, ErroRclone, ObjetoRemoto, Rclone
from email_nf_onedrive.registro.banco import Registro

MAX_SUFIXO = 99
TENTATIVAS_PARA_AVISO = 5


class _Conflito(Exception):
    """Nenhum nome livre até o sufixo máximo."""


class _Divergente(Exception):
    """O arquivo no destino não confere com o local após o envio."""


@dataclass
class ResultadoEnvio:
    enviados: int = 0
    simulados: int = 0
    falhas_de_anexo: int = 0
    falhas: list[Falha] = field(default_factory=list)

    def registrar_falha(self, falha: Falha) -> None:
        if all(f.causa != falha.causa for f in self.falhas):
            self.falhas.append(falha)


def _falha_rclone(erro: ErroRclone, remote: str, destino: str) -> Falha | None:
    if erro.causa == TOKEN:
        return Falha("onedrive:token", f"OneDrive: reautorize o remote com 'rclone config reconnect {remote}:' "
                                        "(ver guia, renovação de credenciais).")
    if erro.causa == ACESSO:
        return Falha("onedrive:acesso", f"OneDrive: acesso negado em {destino} (403). Ação: confira a permissão "
                                         "de edição da conta autorizada no Rclone.")
    if erro.causa == CONFIG:
        return Falha("config:RCLONE_REMOTE", f"OneDrive: remote '{remote}' não encontrado ou Rclone ausente "
                                              f"({erro.detalhe}).")
    return None


class Enviador:
    def __init__(self, registro: Registro, rclone: Rclone, logger: logging.Logger, *, simulacao: bool = False,
                 internos: frozenset[str] = frozenset()) -> None:
        self.registro = registro
        self.rclone = rclone
        self.log = logger
        self.simulacao = simulacao
        self.internos = internos
        self.resultado = ResultadoEnvio()
        self._pastas: dict[str, bool] = {}
        self._erro_global: Falha | None = None

    def _pasta_existe(self, destino: str) -> bool:
        if destino not in self._pastas:
            self._pastas[destino] = self.rclone.pasta_existe(destino)
        return self._pastas[destino]

    def _escolher_nome(self, caminho: str, tamanho: int, hash_local: str) -> tuple[str, bool]:
        """Devolve (caminho, ja_existe_identico)."""
        pasta, nome = caminho.rsplit("/", 1)
        for n in range(1, MAX_SUFIXO + 1):
            candidato = caminho if n == 1 else f"{pasta}/{nomeacao.com_sufixo(nome, n)}"
            remoto = self.rclone.estatistica(candidato)
            if remoto is None:
                return candidato, False
            if self._confere(remoto, tamanho, hash_local):
                return candidato, True
        raise _Conflito(f"mais de {MAX_SUFIXO} arquivos com o nome {nome}")

    @staticmethod
    def _confere(remoto: ObjetoRemoto, tamanho: int, hash_local: str) -> bool:
        if remoto.tamanho != tamanho:
            return False
        return remoto.quickxor is None or remoto.quickxor.lower() == hash_local.lower()

    def _falhar(self, item: AnexoParaEnvio, motivo: str, falha: Falha | None = None) -> None:
        extra = {"caixa": item.caixa.indice}
        self.log.error("falha no envio de %s: %s", item.nome_original, motivo, extra=extra)
        self.resultado.falhas_de_anexo += 1
        if falha is not None:
            self.resultado.registrar_falha(falha)
        if self.simulacao:
            return
        tentativas = self.registro.marcar_falha_envio(item.anexo_id, motivo)
        self.registro.commit()
        if tentativas >= TENTATIVAS_PARA_AVISO:
            self.resultado.registrar_falha(Falha(
                f"anexo:{item.sha256}:tentativas",
                f"anexo {item.nome_original} (caixa {item.caixa.indice}, remetente {item.remetente}): "
                f"{tentativas} tentativas de envio falharam. Ação: ver log.",
            ))

    def _enviar_um(self, item: AnexoParaEnvio) -> None:
        extra = {"caixa": item.caixa.indice}
        destino = item.caixa.destino
        if self._erro_global is not None:
            self._falhar(item, f"envio suspenso nesta execução: {self._erro_global.causa}")
            return
        if not self._pasta_existe(destino):
            self._falhar(item, f"destino não encontrado: {destino}",
                         Falha("onedrive:destino", f"OneDrive: destino não encontrado: {destino}. "
                                                   "Ação: confira DESTINO_ONEDRIVE; a pasta não é criada automaticamente."))
            return
        inicio = time.monotonic()
        tamanho = item.caminho_local.stat().st_size
        hash_local = self.rclone.hash_local(item.caminho_local)
        caminho = nomeacao.caminho_destino(destino, nomeacao.DadosNome(
            empresa=item.caixa.empresa, remetente=item.remetente, nome_original=item.nome_original,
            assunto=item.assunto, classe=item.classe,
            conteudo=item.caminho_local.read_bytes() if item.classe == NFE_XML else None,
            emitente_mensagem=item.emitente_mensagem, remetentes_encaminhados=item.remetentes_encaminhados,
            internos=self.internos,
        ))
        caminho, identico = self._escolher_nome(caminho, tamanho, hash_local)
        nome_final = caminho.rsplit("/", 1)[1]

        if self.simulacao:
            acao = "já existe idêntico" if identico else "enviaria"
            self.log.info("simulação: %s %s -> %s", acao, nome_final, destino, extra=extra)
            self.resultado.simulados += 1
            return
        if not identico:
            self.rclone.copiar(item.caminho_local, caminho)
            remoto = self.rclone.estatistica(caminho)
            if remoto is None or not self._confere(remoto, tamanho, hash_local):
                raise _Divergente("tamanho divergente no destino após o envio")
        self.registro.marcar_enviado(item.anexo_id, caminho)
        self.registro.commit()
        item.caminho_local.unlink(missing_ok=True)
        self.resultado.enviados += 1
        situacao = "já existia idêntico" if identico else "enviado"
        self.log.info("%s: %s -> %s (%.1f s)", situacao, nome_final, destino, time.monotonic() - inicio, extra=extra)

    def enviar(self, itens: list[AnexoParaEnvio]) -> ResultadoEnvio:
        if not itens:
            self.log.info("nada a enviar")
            return self.resultado
        for item in itens:
            try:
                self._enviar_um(item)
            except ErroRclone as erro:
                falha = _falha_rclone(erro, self.rclone.remote, item.caixa.destino)
                if falha is not None and falha.causa in ("onedrive:token", "config:RCLONE_REMOTE"):
                    self._erro_global = falha  # os demais envios falhariam pelo mesmo motivo
                self._falhar(item, f"{erro.causa}: {erro.detalhe}", falha)
            except (_Conflito, _Divergente) as erro:
                self._falhar(item, str(erro))
        return self.resultado


def enviar_anexos(itens: list[AnexoParaEnvio], registro: Registro, rclone: Rclone, logger: logging.Logger,
                  *, simulacao: bool = False, internos: frozenset[str] = frozenset()) -> ResultadoEnvio:
    return Enviador(registro, rclone, logger, simulacao=simulacao, internos=internos).enviar(itens)
