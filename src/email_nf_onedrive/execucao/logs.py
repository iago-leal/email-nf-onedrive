"""Log em arquivo com rotação diária e retenção de 30 dias (D-15, EM RF-06).

Uma linha por evento: `AAAA-MM-DDTHH:MM:SS±HH:MM NIVEL [caixa n] mensagem`.
O prefixo de caixa vem do atributo `caixa` passado em `extra`. Todos os handlers
recebem o filtro de segredos.
"""

from __future__ import annotations

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path

NOME_LOGGER = "email_nf_onedrive"
ARQUIVO_LOG = "email-nf-onedrive.log"
COPIAS_ANTIGAS = 29  # 29 cópias + o arquivo corrente = 30 dias


class FormatoLinha(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        instante = datetime.fromtimestamp(record.created).astimezone().isoformat(timespec="seconds")
        caixa = getattr(record, "caixa", None)
        prefixo = f"[caixa {caixa}] " if caixa is not None else ""
        linha = f"{instante} {record.levelname} {prefixo}{record.getMessage()}"
        if record.exc_text:
            linha += "\n" + record.exc_text
        return linha


def _arquivo_rotativo(diretorio: Path) -> logging.Handler:
    diretorio.mkdir(parents=True, exist_ok=True)
    caminho = diretorio / ARQUIVO_LOG
    if not caminho.exists():
        os.close(os.open(caminho, os.O_CREAT | os.O_WRONLY, 0o600))
    handler = logging.handlers.TimedRotatingFileHandler(
        caminho, when="midnight", backupCount=COPIAS_ANTIGAS, encoding="utf-8"
    )
    os.chmod(caminho, 0o600)
    return handler


def configurar_log(diretorio: Path, *, terminal: bool = False, nivel: int = logging.INFO) -> logging.Logger:
    """Configura o logger da ferramenta. Chamadas repetidas substituem os handlers."""
    from email_nf_onedrive.segredos import FiltroSegredos

    logger = logging.getLogger(NOME_LOGGER)
    for antigo in list(logger.handlers):
        logger.removeHandler(antigo)
        antigo.close()
    handlers = [_arquivo_rotativo(Path(diretorio))]
    if terminal:
        handlers.append(logging.StreamHandler(sys.stderr))
    for handler in handlers:
        handler.setFormatter(FormatoLinha())
        handler.addFilter(FiltroSegredos())
        logger.addHandler(handler)
    logger.setLevel(nivel)
    logger.propagate = False
    return logger


def obter_logger() -> logging.Logger:
    return logging.getLogger(NOME_LOGGER)
