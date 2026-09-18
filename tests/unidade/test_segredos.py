"""Testes do mascaramento de segredos (D-04, RF-03 do requirements)."""

from __future__ import annotations

import io
import logging

from email_nf_onedrive import segredos


def _logger_com_filtro() -> tuple[logging.Logger, io.StringIO]:
    saida = io.StringIO()
    handler = logging.StreamHandler(saida)
    handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    handler.addFilter(segredos.FiltroSegredos())
    logger = logging.getLogger(f"teste-segredos-{id(saida)}")
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel(logging.DEBUG)
    return logger, saida


def test_mascarar_substitui_valores_registrados():
    segredos.registrar("senha-de-app")
    segredos.registrar("123:token")
    assert segredos.mascarar("x senha-de-app y 123:token z") == "x **** y **** z"


def test_valor_vazio_nao_e_registrado():
    segredos.registrar("")
    segredos.registrar(None)
    assert segredos.mascarar("texto qualquer") == "texto qualquer"


def test_segredo_contido_em_outro_e_mascarado_por_inteiro():
    segredos.registrar("abc")
    segredos.registrar("abcdef")
    assert segredos.mascarar("abcdef") == "****"


def test_limpar_esquece_os_segredos():
    segredos.registrar("senha-de-app")
    segredos.limpar()
    assert segredos.mascarar("senha-de-app") == "senha-de-app"


def test_filtro_mascara_mensagem_formatada_com_argumentos():
    segredos.registrar("senha-de-app")
    logger, saida = _logger_com_filtro()
    logger.error("login falhou com %s", "senha-de-app")
    assert "senha-de-app" not in saida.getvalue()
    assert "login falhou com ****" in saida.getvalue()


def test_filtro_mascara_texto_de_excecao():
    segredos.registrar("senha-de-app")
    logger, saida = _logger_com_filtro()
    try:
        raise RuntimeError("servidor ecoou senha-de-app")
    except RuntimeError:
        logger.exception("erro inesperado")
    texto = saida.getvalue()
    assert "senha-de-app" not in texto
    assert "servidor ecoou ****" in texto
    assert "Traceback" in texto


def test_filtro_nunca_descarta_registros():
    logger, saida = _logger_com_filtro()
    logger.info("mensagem sem segredo")
    assert "mensagem sem segredo" in saida.getvalue()
