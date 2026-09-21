"""Provedor da credencial temporária de cada caixa em modo oauth (feature 002, D-06, D-08, D-09).

Uma instância por execução. Para cada caixa: lê a autorização durável do arquivo,
renova uma única vez e devolve a credencial, que vive só em memória. Toda falha
sai como `ErroCredencial`, já com a chave de causa dos avisos. Depois de um
`oauth:cliente`, as demais caixas recebem a mesma falha sem nova requisição. O
arquivo de autorização nunca é escrito nem apagado aqui (RF-09).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from email_nf_onedrive.autorizacao import arquivo, servico
from email_nf_onedrive.configuracao.modelo import Caixa, ClienteOAuth

CAUSA_CLIENTE = "oauth:cliente"
SUFIXO_AUTORIZACAO = "autorizacao"
SUFIXO_SERVICO = "autorizacao-servico"


def e_causa_de_autorizacao(causa: str) -> bool:
    """Causas que o resumo conta em `falhas_autorizacao` (D-13)."""
    return causa == CAUSA_CLIENTE or causa.endswith((f":{SUFIXO_AUTORIZACAO}", f":{SUFIXO_SERVICO}"))


class ErroCredencial(Exception):
    """`causa` é a chave do aviso; `mensagem`, o texto do aviso; `resumo`, o motivo curto do `testar-caixa`."""

    def __init__(self, causa: str, mensagem: str, resumo: str) -> None:
        super().__init__(mensagem)
        self.causa = causa
        self.mensagem = mensagem
        self.resumo = resumo


def erro_de_autorizacao(indice: int, estado: str, resumo: str) -> ErroCredencial:
    return ErroCredencial(f"caixa{indice}:{SUFIXO_AUTORIZACAO}",
                          f"caixa {indice}: autorização OAuth {estado} (rode autorizar-caixa {indice})", resumo)


@dataclass
class ProvedorCredencial:
    cliente: ClienteOAuth
    dir_autorizacoes: Path
    enderecos: servico.Enderecos
    logger: logging.Logger | None = None
    _cliente_recusado: bool = field(default=False, init=False)

    def _erro_do_cliente(self) -> ErroCredencial:
        return ErroCredencial(
            CAUSA_CLIENTE,
            "credenciais do cliente OAuth recusadas pelo Google. "
            "Ação: confira OAUTH_CLIENT_ID e OAUTH_CLIENT_SECRET no .env.",
            "credenciais do cliente OAuth recusadas pelo Google",
        )

    def obter(self, caixa: Caixa) -> str:
        n = caixa.indice
        if self._cliente_recusado:
            raise self._erro_do_cliente()
        try:
            autorizacao = arquivo.ler(self.dir_autorizacoes, caixa.endereco, self.cliente.client_id)
        except arquivo.ErroArquivoAutorizacao as erro:
            if erro.ausente:
                raise erro_de_autorizacao(n, "ausente", erro.motivo) from erro
            raise erro_de_autorizacao(n, f"inválida: {erro.motivo}", f"{erro.motivo}; rode autorizar-caixa {n}") from erro
        try:
            return servico.renovar(self.enderecos, self.cliente, autorizacao.refresh_token, self.logger).access_token
        except servico.ErroServico as erro:
            if erro.classe == servico.CLIENTE:
                self._cliente_recusado = True
                raise self._erro_do_cliente() from erro
            if erro.classe == servico.TRANSITORIA:
                raise ErroCredencial(
                    f"caixa{n}:{SUFIXO_SERVICO}",
                    f"caixa {n}: serviço de autorização do Google indisponível. Nova tentativa na próxima execução.",
                    "serviço de autorização indisponível",
                ) from erro
            raise erro_de_autorizacao(n, "recusada", f"autorização recusada; rode autorizar-caixa {n}") from erro
