"""Lógica de avisos ao operador (D-16, EM RF-07 a RF-09, fluxo B).

Falhas são registradas por causa durante a execução; em `finalizar`, cada causa
é notificada na primeira ocorrência e depois no máximo a cada 6 h. Uma execução
com código 0 notifica a recuperação das causas ativas. Aviso não entregue fica
pendente e é reenviado na execução seguinte. O transporte (Telegram) é injetado.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Callable

from email_nf_onedrive import segredos
from email_nf_onedrive.execucao.logs import obter_logger
from email_nf_onedrive.registro.banco import EstadoAviso, Registro

INTERVALO_REPETICAO = timedelta(hours=6)
LIMITE_TEXTO = 4096
SUFIXO_TRUNCADO = "… (ver log)"
TITULO = "email-nf-onedrive"

Transporte = Callable[[str], tuple[bool, str | None]]


def descrever_recuperacao(causa: str) -> str:
    if m := re.match(r"^caixa(\d+):", causa):
        return f"caixa {m.group(1)} voltou a funcionar"
    if causa.startswith("onedrive:"):
        return "envio ao OneDrive voltou a funcionar"
    return f"{causa} normalizada"


def _truncar(texto: str) -> str:
    if len(texto) <= LIMITE_TEXTO:
        return texto
    return texto[: LIMITE_TEXTO - len(SUFIXO_TRUNCADO)] + SUFIXO_TRUNCADO


class GerenciadorAvisos:
    def __init__(self, registro: Registro, transporte: Transporte | None, *,
                 agora: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
                 intervalo: timedelta = INTERVALO_REPETICAO) -> None:
        self.registro = registro
        self.transporte = transporte
        self.agora = agora
        self.intervalo = intervalo
        self._causas_da_execucao: list[str] = []

    def registrar_falha(self, causa: str, mensagem: str) -> None:
        agora = self.agora()
        mensagem = segredos.mascarar(mensagem)
        anterior = self.registro.aviso_obter(causa)
        if anterior is None or not anterior.ativa:
            estado = EstadoAviso(causa, agora, None, True, mensagem, False)
        else:
            estado = EstadoAviso(causa, anterior.primeira_ocorrencia, anterior.ultimo_aviso, True,
                                 mensagem, anterior.entrega_pendente)
        self.registro.aviso_salvar(estado)
        if causa not in self._causas_da_execucao:
            self._causas_da_execucao.append(causa)

    def _vencida(self, estado: EstadoAviso, agora: datetime) -> bool:
        return (
            estado.entrega_pendente
            or estado.ultimo_aviso is None
            or agora - estado.ultimo_aviso >= self.intervalo
        )

    def _enviar(self, texto: str) -> bool:
        if self.transporte is None:
            return False
        entregue, motivo = self.transporte(_truncar(segredos.mascarar(texto)))
        if not entregue:
            obter_logger().warning("aviso não entregue: %s", motivo)
        return entregue

    def finalizar(self, codigo_saida: int) -> None:
        agora = self.agora()
        if codigo_saida == 0:
            self._notificar_recuperacao(agora)
        else:
            self._notificar_falhas(codigo_saida, agora)
        self.registro.commit()

    def _notificar_falhas(self, codigo_saida: int, agora: datetime) -> None:
        a_notificar = [
            estado for causa in self._causas_da_execucao
            if (estado := self.registro.aviso_obter(causa)) and self._vencida(estado, agora)
        ]
        if not a_notificar:
            return
        linhas = [f"{TITULO}: execução com falha (código {codigo_saida})"]
        linhas += [f"• {estado.mensagem}" for estado in a_notificar]
        entregue = self._enviar("\n".join(linhas))
        for estado in a_notificar:
            self.registro.aviso_salvar(EstadoAviso(
                estado.causa, estado.primeira_ocorrencia,
                agora if entregue else estado.ultimo_aviso,
                True, estado.mensagem, not entregue,
            ))

    def _notificar_recuperacao(self, agora: datetime) -> None:
        ativas = self.registro.avisos_ativos()
        if not ativas:
            return
        linhas = [f"{TITULO}: recuperado"]
        linhas += [f"• recuperado: {descrever_recuperacao(estado.causa)}" for estado in ativas]
        if not self._enviar("\n".join(linhas)):
            return  # continuam ativas; a próxima execução com código 0 tenta de novo
        for estado in ativas:
            self.registro.aviso_salvar(EstadoAviso(
                estado.causa, estado.primeira_ocorrencia, agora, False, estado.mensagem, False,
            ))
