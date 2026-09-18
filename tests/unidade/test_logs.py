"""Contrato do log em arquivo (EM RF-06, D-15)."""

from __future__ import annotations

import logging
import logging.handlers
import re

import pytest

from email_nf_onedrive import segredos
from email_nf_onedrive.execucao.logs import ARQUIVO_LOG, NOME_LOGGER, configurar_log


@pytest.fixture
def logger(home):
    log = configurar_log(home / "var" / "log")
    yield log
    for handler in list(log.handlers):
        log.removeHandler(handler)
        handler.close()


def test_rotacao_diaria_com_30_arquivos(logger):
    # o pytest acrescenta handlers de captura; o da ferramenta é o único de arquivo
    (handler,) = [h for h in logger.handlers if isinstance(h, logging.handlers.TimedRotatingFileHandler)]
    assert handler.when == "MIDNIGHT"
    assert handler.backupCount == 29  # 29 cópias + o arquivo corrente


def test_linha_iso_nivel_caixa_e_permissao_600(logger, home):
    logger.info("caixa 1: conectada", extra={"caixa": 1})
    logger.warning("sem caixa")
    caminho = home / "var" / "log" / ARQUIVO_LOG
    primeira, segunda = caminho.read_text(encoding="utf-8").splitlines()
    assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2} INFO \[caixa 1\] caixa 1: conectada$", primeira)
    assert segunda.endswith(" WARNING sem caixa")
    assert oct(caminho.stat().st_mode & 0o777) == oct(0o600)


def test_segredo_mascarado_no_arquivo(logger, home):
    segredos.registrar("senha-de-app-secreta")
    logging.getLogger(NOME_LOGGER).error("falhou com senha-de-app-secreta")
    texto = (home / "var" / "log" / ARQUIVO_LOG).read_text(encoding="utf-8")
    assert "senha-de-app-secreta" not in texto and "****" in texto
