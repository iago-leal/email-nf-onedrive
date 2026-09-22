"""Ciclo do subcomando `executar` (spec execucao-monitoramento, RF-02 a RF-11).

Ordem: log, trava, limite de duração, registro, configuração, coleta de todas as
caixas válidas, envio, avisos e resumo. O registro é aberto antes da configuração
para que também o erro de configuração passe pela supressão de avisos. A pasta de
trabalho é removida no `finally`, qualquer que seja o desfecho.

Código de saída: 0 sem falhas; 1 falha parcial; 2 erro de configuração, nenhuma
caixa válida, todas as caixas com falha na coleta ou erro da própria execução.
"""

from __future__ import annotations

import errno
import logging
import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from dotenv import dotenv_values

from email_nf_onedrive import segredos
from email_nf_onedrive.autorizacao.credencial import ProvedorCredencial, e_causa_de_autorizacao
from email_nf_onedrive.autorizacao.servico import Enderecos
from email_nf_onedrive.coleta.coleta import Falha, FabricaIMAP, coletar, fabrica_imap_padrao
from email_nf_onedrive.configuracao.carregar import carregar_configuracao
from email_nf_onedrive.configuracao.modelo import MODO_OAUTH, Configuracao, ErroConfiguracao
from email_nf_onedrive.envio.envio import enviar_anexos
from email_nf_onedrive.envio.rclone import Rclone
from email_nf_onedrive.execucao import telegram
from email_nf_onedrive.execucao.avisos import TITULO, GerenciadorAvisos, Transporte
from email_nf_onedrive.execucao.logs import configurar_log
from email_nf_onedrive.execucao.resumo import ResumoExecucao
from email_nf_onedrive.execucao.trava import LIMITE_DURACAO_S, TempoEsgotado, Trava, TravaOcupada, limite_duracao
from email_nf_onedrive.registro.banco import Registro, RegistroCorrompido

ARQUIVO_REGISTRO = "registro.sqlite3"
ARQUIVO_TRAVA = "execucao.lock"
META_ULTIMA_EXECUCAO = "ultima_execucao_em"


def _agora_utc() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Dependencias:
    """Pontos de injeção para testes: rede, processo externo e relógio."""

    fabrica_imap: FabricaIMAP = fabrica_imap_padrao
    criar_rclone: Callable[[str], Rclone] = Rclone
    criar_transporte: Callable[[str, str], Transporte] = telegram.criar_transporte
    agora: Callable[[], datetime] = _agora_utc
    limite_s: int = LIMITE_DURACAO_S
    # Feature 002, D-14: os endereços do Google só mudam por aqui, nunca pelo .env.
    servico_autorizacao: Enderecos = field(default_factory=Enderecos)
    # Chamado pelo `autorizar-caixa` com o endereço de consentimento já impresso; os testes simulam o navegador.
    ao_exibir_endereco: Callable[[str], None] | None = None


def criar_provedor(config: Configuracao, deps: Dependencias, logger: logging.Logger | None) -> ProvedorCredencial | None:
    """Provedor de credencial da execução; `None` na instalação sem caixa em modo oauth."""
    if config.cliente_oauth is None or all(caixa.modo != MODO_OAUTH for caixa in config.caixas):
        return None
    return ProvedorCredencial(config.cliente_oauth, config.dir_autorizacoes, deps.servico_autorizacao, logger)


def _transporte_de_emergencia(home: Path, deps: Dependencias) -> Transporte | None:
    """Com a configuração inválida, ainda tenta avisar com o par TELEGRAM_* do .env."""
    try:
        env = dotenv_values(home / ".env")
    except OSError:
        return None
    token, chat_id = (env.get("TELEGRAM_BOT_TOKEN") or "").strip(), (env.get("TELEGRAM_CHAT_ID") or "").strip()
    if not (token and chat_id):
        return None
    segredos.registrar(token)
    return deps.criar_transporte(token, chat_id)


@dataclass
class _Ciclo:
    home: Path
    simulacao: bool
    log: logging.Logger
    deps: Dependencias
    registro: Registro | None = None
    config: Configuracao | None = None
    transporte: Transporte | None = None
    falhas: list[Falha] = field(default_factory=list)
    trabalho: Path | None = None

    @property
    def var(self) -> Path:
        return self.home / "var"

    def _falhar(self, causa: str, mensagem: str) -> None:
        if all(f.causa != causa for f in self.falhas):
            self.falhas.append(Falha(causa, mensagem))

    # --- etapas -------------------------------------------------------------------

    def _abrir_registro(self) -> bool:
        try:
            self.registro = Registro.abrir(self.var / ARQUIVO_REGISTRO, simulacao=self.simulacao)
        except RegistroCorrompido as erro:
            self.log.error("%s", erro)
            self._falhar("execucao:registro", f"registro de processados ilegível ({erro}). Ação: restaure o "
                                              "backup de var/registro.sqlite3 ou mova o arquivo para iniciar outro.")
            return False
        return True

    def _carregar_configuracao(self) -> bool:
        try:
            self.config = carregar_configuracao(self.home)
        except ErroConfiguracao as erro:
            for item in erro.erros:
                self.log.error("configuração: %s", item)
            self._falhar("config:global", f"configuração inválida: {'; '.join(erro.erros)}. Ação: corrija o .env.")
            return False
        for alerta in self.config.alertas:
            self.log.warning("configuração: %s", alerta)
        if self.config.telegram_ativo:
            self.transporte = self.deps.criar_transporte(self.config.telegram_bot_token, self.config.telegram_chat_id)
        for invalida in self.config.caixas_invalidas:
            self.log.error("%s", invalida.motivo, extra={"caixa": invalida.indice})
            self._falhar(f"config:caixa{invalida.indice}", f"{invalida.motivo}. Ação: corrija o .env.")
        return True

    def _executar(self, resumo: ResumoExecucao) -> int:
        if not self._abrir_registro():
            return 2
        anterior = self.registro.meta_obter(META_ULTIMA_EXECUCAO)
        if anterior:
            resumo.intervalo_desde_anterior = resumo.inicio - datetime.fromisoformat(anterior)
        if not self._carregar_configuracao():
            resumo.falhas += 1
            return 2
        config = self.config
        resumo.falhas += len(config.caixas_invalidas)
        if not config.caixas:
            self._falhar("config:caixas", "nenhuma caixa válida no .env. Ação: defina EMAIL1 e SENHA_EMAIL1.")
            return 2
        if self.simulacao:
            self.log.info("modo simulação: nada será enviado nem registrado")

        self.trabalho = self.var / "trabalho" / f"{resumo.inicio:%Y%m%dT%H%M%S}-{os.getpid()}"
        resultados = coletar(config.caixas, self.registro, self.trabalho, config.data_inicial, self.log,
                             self.deps.fabrica_imap, criar_provedor(config, self.deps, self.log))
        itens = []
        for resultado in resultados:
            resumo.extraidos += sum(resultado.classes.values())
            resumo.retidos += resultado.retidos
            itens += resultado.para_envio
            if resultado.falha is None:
                resumo.caixas_processadas += 1
            else:
                resumo.falhas += 1
                resumo.falhas_autorizacao += e_causa_de_autorizacao(resultado.falha.causa)
                self._falhar(resultado.falha.causa, resultado.falha.mensagem)

        envio = enviar_anexos(itens, self.registro, self.deps.criar_rclone(config.rclone_remote), self.log,
                              simulacao=self.simulacao, internos=config.dominios_internos)
        resumo.enviados += envio.enviados
        resumo.falhas += envio.falhas_de_anexo
        for falha in envio.falhas:
            self._falhar(falha.causa, falha.mensagem)

        if resumo.caixas_processadas == 0:
            return 2
        return 1 if self.falhas else 0

    # --- fechamento -------------------------------------------------------------------

    def _avisar(self, codigo: int) -> None:
        if self.simulacao:
            return
        transporte = self.transporte
        if transporte is None and self.config is None:
            transporte = _transporte_de_emergencia(self.home, self.deps)
        if self.registro is None:
            # Sem registro não há supressão: o aviso vai direto, uma vez por execução.
            if transporte is not None and self.falhas:
                linhas = [f"{TITULO}: execução com falha (código {codigo})"] + [f"• {f.mensagem}" for f in self.falhas]
                entregue, motivo = transporte(segredos.mascarar("\n".join(linhas)))
                if not entregue:
                    self.log.warning("aviso não entregue: %s", motivo)
            return
        avisos = GerenciadorAvisos(self.registro, transporte, agora=self.deps.agora)
        for falha in self.falhas:
            avisos.registrar_falha(falha.causa, falha.mensagem)
        avisos.finalizar(codigo)

    def _encerrar(self, resumo: ResumoExecucao, codigo: int) -> None:
        try:
            self._avisar(codigo)
            if self.registro is not None:
                self.registro.meta_definir(META_ULTIMA_EXECUCAO, resumo.inicio.isoformat())
                self.registro.fechar()
        except Exception:  # o encerramento nunca mascara o código já calculado
            self.log.exception("falha ao encerrar a execução")
        resumo.encerrar(self.deps.agora(), codigo)
        self.log.info("%s", resumo.linha())

    def rodar(self) -> int:
        resumo = ResumoExecucao(inicio=self.deps.agora())
        codigo = 2
        try:
            with limite_duracao(self.deps.limite_s):
                codigo = self._executar(resumo)
        except TempoEsgotado as erro:
            self.log.error("execução interrompida: %s", erro)
            self._falhar("execucao:tempo", f"execução interrompida após {self.deps.limite_s // 60} min; "
                                           "o restante fica para a próxima execução.")
            resumo.falhas += 1
        except Exception as erro:
            if isinstance(erro, OSError) and erro.errno == errno.ENOSPC:
                self.log.error("disco cheio: %s", erro)
                self._falhar("execucao:disco", "disco cheio na VPS. Ação: libere espaço em disco.")
            else:
                self.log.exception("exceção não prevista")
                self._falhar("execucao:excecao", f"exceção não prevista ({type(erro).__name__}). Ação: ver log.")
            resumo.falhas += 1
        finally:
            if self.trabalho is not None:
                shutil.rmtree(self.trabalho, ignore_errors=True)
        self._encerrar(resumo, codigo)
        return codigo


def executar(home: Path, *, simulacao: bool = False, terminal: bool = False,
             deps: Dependencias | None = None) -> int:
    """Executa um ciclo completo e devolve o código de saída."""
    home = Path(home)
    deps = deps or Dependencias()
    log = configurar_log(home / "var" / "log", terminal=terminal)
    trava = Trava(home / "var" / ARQUIVO_TRAVA)
    try:
        if trava.adquirir():
            log.warning("trava abandonada removida")
    except TravaOcupada:
        log.info("execução anterior em andamento")
        return 0
    try:
        return _Ciclo(home, simulacao, log, deps).rodar()
    finally:
        trava.liberar()
