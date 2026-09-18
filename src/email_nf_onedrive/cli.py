"""Linha de comando (interfaces/cli-e-env.md).

    email-nf-onedrive [--home DIR] executar [--simular]
    email-nf-onedrive [--home DIR] verificar-config
    email-nf-onedrive [--home DIR] testar-onedrive
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from email_nf_onedrive import __version__, segredos
from email_nf_onedrive.configuracao.carregar import carregar_configuracao
from email_nf_onedrive.configuracao.modelo import Configuracao, ErroConfiguracao
from email_nf_onedrive.envio import teste_onedrive
from email_nf_onedrive.execucao import ciclo


def _analisador() -> argparse.ArgumentParser:
    analisador = argparse.ArgumentParser(
        prog="email-nf-onedrive",
        description="Arquiva no OneDrive as NF-e e boletos recebidos por e-mail (leitura IMAP somente leitura).",
    )
    analisador.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    analisador.add_argument("--home", type=Path, default=None,
                            help="diretório de instalação, com .env e var/ (padrão: EMAIL_NF_HOME ou o diretório corrente)")
    sub = analisador.add_subparsers(dest="comando", required=True, metavar="comando")
    executar = sub.add_parser("executar", help="coleta as caixas e envia os anexos ao OneDrive")
    executar.add_argument("--simular", action="store_true",
                          help="coleta e classifica sem enviar, sem alterar o registro e sem avisar")
    sub.add_parser("verificar-config", help="valida o .env e lista as caixas, sem acessar a rede")
    sub.add_parser("testar-onedrive", help="grava e apaga um arquivo de teste em cada destino")
    return analisador


def _home(argumento: Path | None) -> Path:
    if argumento is not None:
        return argumento
    return Path(os.environ.get("EMAIL_NF_HOME") or Path.cwd())


def _carregar(home: Path) -> Configuracao | None:
    try:
        return carregar_configuracao(home)
    except ErroConfiguracao as erro:
        for item in erro.erros:
            print(f"erro: {item}", file=sys.stderr)
        return None


def _verificar_config(home: Path) -> int:
    config = _carregar(home)
    if config is None:
        return 2
    for caixa in config.caixas:
        print(f"{caixa.indice} · {caixa.endereco} · {caixa.pasta} · {caixa.destino} · senha {segredos.MASCARA}")
    for invalida in config.caixas_invalidas:
        print(f"inválida: {invalida.motivo}")
    print(f"remote do Rclone: {config.rclone_remote}")
    print(f"data inicial: {config.data_inicial.isoformat()}")
    print(f"avisos pelo Telegram: {'ativos' if config.telegram_ativo else 'desativados'}")
    for alerta in config.alertas:
        print(f"alerta: {alerta}")
    if not config.caixas:
        vazio = not config.caixas_invalidas
        print("erro: " + ("nenhuma caixa configurada no .env" if vazio else "nenhuma caixa válida no .env"),
              file=sys.stderr)
        return 2
    return 0


def _testar_onedrive(home: Path, deps: ciclo.Dependencias) -> int:
    config = _carregar(home)
    if config is None:
        return 2
    rclone = deps.criar_rclone(config.rclone_remote)
    destinos = sorted({caixa.destino for caixa in config.caixas})
    if not destinos:
        print("erro: nenhuma caixa válida no .env", file=sys.stderr)
        return 2
    codigo = 0
    for destino in destinos:
        ok, mensagem = teste_onedrive.testar_onedrive(rclone, destino)
        print(segredos.mascarar(mensagem), file=sys.stdout if ok else sys.stderr)
        codigo = codigo if ok else 2
    return codigo


def main(argv: list[str] | None = None, *, deps: ciclo.Dependencias | None = None) -> int:
    argumentos = _analisador().parse_args(argv)
    home = _home(argumentos.home)
    deps = deps or ciclo.Dependencias()
    if argumentos.comando == "executar":
        return ciclo.executar(home, simulacao=argumentos.simular, terminal=sys.stderr.isatty(), deps=deps)
    if argumentos.comando == "verificar-config":
        return _verificar_config(home)
    return _testar_onedrive(home, deps)


if __name__ == "__main__":
    sys.exit(main())
