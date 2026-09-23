"""Envio dos anexos ao OneDrive (spec envio-onedrive, interfaces/rclone-onedrive.md).

Protocolo por anexo, com até ENVIOS_SIMULTANEOS anexos em paralelo: confirma que a pasta de destino existe (sem criá-la), escolhe
o nome livre ou reconhece arquivo idêntico já presente, envia sem sobrescrever e
só marca `enviado` depois de confirmar tamanho e hash no destino (RN-04). A cópia
local é apagada logo após a confirmação (RN-07).
"""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

from email_nf_onedrive.coleta.classificacao import NFE_XML
from email_nf_onedrive.coleta.coleta import AnexoParaEnvio, Falha
from email_nf_onedrive.envio import nomeacao, vencimento
from email_nf_onedrive.envio.rclone import ACESSO, CONFIG, TOKEN, ErroRclone, ObjetoRemoto, Rclone
from email_nf_onedrive.registro.banco import Registro

MAX_SUFIXO = 99
TENTATIVAS_PARA_AVISO = 5
ENVIOS_SIMULTANEOS = 4


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


@dataclass
class _Desfecho:
    """O que o trabalho remoto de um anexo apurou; o registro é gravado depois, na thread principal."""

    item: AnexoParaEnvio
    destino: str
    motivo_raiz: str = ""  # por que ficou sem vencimento, para o sumário LEIAME (feature 006)
    caminho: str = ""
    identico: bool = False
    duracao: float = 0.0
    motivo: str = ""
    falha: Falha | None = None

    @property
    def falhou(self) -> bool:
        return bool(self.motivo)


class Enviador:
    """Envia os anexos em até `simultaneos` threads (o gargalo é a ida e volta ao OneDrive).

    As threads só falam com o Rclone; registro, contagens e cópia local ficam na thread principal,
    que também recebe a interrupção do limite de tempo. Anexos com o mesmo caminho de destino,
    comparado sem caixa como faz o OneDrive, vão juntos, em sequência, para que a escolha do
    sufixo `_n` continue vendo o arquivo que o anterior acabou de enviar.
    """

    def __init__(self, registro: Registro, rclone: Rclone, logger: logging.Logger, *, simulacao: bool = False,
                 internos: frozenset[str] = frozenset(), resultado: ResultadoEnvio | None = None,
                 simultaneos: int = ENVIOS_SIMULTANEOS) -> None:
        self.registro = registro
        self.rclone = rclone
        self.log = logger
        self.simulacao = simulacao
        self.internos = internos
        self.simultaneos = max(1, simultaneos)
        # Quem chama pode fornecer o acumulador para ler as contagens mesmo que o envio seja
        # interrompido no meio (BUG-20260922-RWDA): o retorno só existe quando a chamada termina.
        self.resultado = resultado if resultado is not None else ResultadoEnvio()
        self._pastas: dict[str, bool] = {}
        self._erro_global: Falha | None = None

    # --- preparação (thread principal) ------------------------------------------

    def _preparar(self, item: AnexoParaEnvio) -> tuple[str, str, str]:
        """(pasta de destino, caminho padronizado, motivo de ir à raiz) do anexo, sem tocar no OneDrive."""
        leitura = vencimento.ler(item.caminho_local, xml=item.classe == NFE_XML,
                                 vencimento_mensagem=item.vencimento_mensagem, referencia=item.data_mensagem.date())
        destino = vencimento.pasta_vencimento(item.caixa.destino, leitura.quando)
        caminho = nomeacao.caminho_destino(destino, nomeacao.DadosNome(
            empresa=item.caixa.empresa, remetente=item.remetente, nome_original=item.nome_original,
            assunto=item.assunto, classe=item.classe,
            conteudo=item.caminho_local.read_bytes() if item.classe == NFE_XML else None,
            emitente_mensagem=item.emitente_mensagem, remetentes_encaminhados=item.remetentes_encaminhados,
            internos=self.internos,
        ))
        return destino, caminho, leitura.motivo

    # --- trabalho remoto (threads) ----------------------------------------------

    def _pasta_existe(self, destino: str) -> bool:
        if destino not in self._pastas:  # duas threads podem consultar a mesma pasta; a leitura é inofensiva
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

    def _remoto(self, item: AnexoParaEnvio, destino: str, caminho: str, motivo_raiz: str) -> _Desfecho:
        desfecho = _Desfecho(item, destino, motivo_raiz)
        if self._erro_global is not None:
            desfecho.motivo = f"envio suspenso nesta execução: {self._erro_global.causa}"
            return desfecho
        inicio = time.monotonic()
        try:
            if not self._pasta_existe(destino):
                desfecho.motivo = f"destino não encontrado: {destino}"
                desfecho.falha = Falha("onedrive:destino", f"OneDrive: destino não encontrado: {destino}. "
                                                           "Ação: confira DESTINO_ONEDRIVE e a grade de pastas por "
                                                           "vencimento; a pasta não é criada automaticamente.")
                return desfecho
            tamanho = item.caminho_local.stat().st_size
            hash_local = self.rclone.hash_local(item.caminho_local)
            desfecho.caminho, desfecho.identico = self._escolher_nome(caminho, tamanho, hash_local)
            if not self.simulacao and not desfecho.identico:
                self.rclone.copiar(item.caminho_local, desfecho.caminho)
                remoto = self.rclone.estatistica(desfecho.caminho)
                if remoto is None or not self._confere(remoto, tamanho, hash_local):
                    raise _Divergente("tamanho divergente no destino após o envio")
        except ErroRclone as erro:
            desfecho.falha = _falha_rclone(erro, self.rclone.remote, item.caixa.destino)
            if desfecho.falha is not None and desfecho.falha.causa in ("onedrive:token", "config:RCLONE_REMOTE"):
                self._erro_global = desfecho.falha  # os demais envios falhariam pelo mesmo motivo
            desfecho.motivo = f"{erro.causa}: {erro.detalhe}"
        except (_Conflito, _Divergente) as erro:
            desfecho.motivo = str(erro)
        desfecho.duracao = time.monotonic() - inicio
        return desfecho

    def _remoto_em_sequencia(self, grupo: list[tuple[AnexoParaEnvio, str, str, str]]) -> list[_Desfecho]:
        return [self._remoto(*preparado) for preparado in grupo]

    # --- registro (thread principal) --------------------------------------------

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

    def _concluir(self, desfecho: _Desfecho) -> None:
        item = desfecho.item
        if desfecho.falhou:
            self._falhar(item, desfecho.motivo, desfecho.falha)
            return
        extra = {"caixa": item.caixa.indice}
        nome_final = desfecho.caminho.rsplit("/", 1)[1]
        if self.simulacao:
            acao = "já existe idêntico" if desfecho.identico else "enviaria"
            self.log.info("simulação: %s %s -> %s", acao, nome_final, desfecho.destino, extra=extra)
            self.resultado.simulados += 1
            return
        self.registro.marcar_enviado(item.anexo_id, desfecho.caminho)
        if desfecho.motivo_raiz:
            self.registro.registrar_motivo_raiz(item.anexo_id, desfecho.motivo_raiz)
        self.registro.commit()
        item.caminho_local.unlink(missing_ok=True)
        self.resultado.enviados += 1
        situacao = "já existia idêntico" if desfecho.identico else "enviado"
        self.log.info("%s: %s -> %s (%.1f s)", situacao, nome_final, desfecho.destino, desfecho.duracao, extra=extra)

    def enviar(self, itens: list[AnexoParaEnvio]) -> ResultadoEnvio:
        if not itens:
            self.log.info("nada a enviar")
            return self.resultado
        grupos: dict[str, list[tuple[AnexoParaEnvio, str, str, str]]] = {}
        for item in itens:
            destino, caminho, motivo_raiz = self._preparar(item)
            grupos.setdefault(caminho.casefold(), []).append((item, destino, caminho, motivo_raiz))
        pool = ThreadPoolExecutor(max_workers=self.simultaneos, thread_name_prefix="envio")
        try:
            futuros = [pool.submit(self._remoto_em_sequencia, grupo) for grupo in grupos.values()]
            for futuro in as_completed(futuros):
                for desfecho in futuro.result():
                    self._concluir(desfecho)
        finally:
            # Na interrupção pelo limite de tempo, nada novo começa; o que já está em curso termina
            # sem registro, e a execução seguinte o reconhece no destino pelo hash (já existia idêntico).
            pool.shutdown(wait=False, cancel_futures=True)
        return self.resultado


def enviar_anexos(itens: list[AnexoParaEnvio], registro: Registro, rclone: Rclone, logger: logging.Logger,
                  *, simulacao: bool = False, internos: frozenset[str] = frozenset(),
                  resultado: ResultadoEnvio | None = None, simultaneos: int = ENVIOS_SIMULTANEOS) -> ResultadoEnvio:
    return Enviador(registro, rclone, logger, simulacao=simulacao, internos=internos, resultado=resultado,
                    simultaneos=simultaneos).enviar(itens)
