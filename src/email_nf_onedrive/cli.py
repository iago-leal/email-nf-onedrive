"""Linha de comando (interfaces/cli-e-env.md).

    email-nf-onedrive [--home DIR] executar [--simular]
    email-nf-onedrive [--home DIR] verificar-config
    email-nf-onedrive [--home DIR] testar-onedrive
    email-nf-onedrive [--home DIR] autorizar-caixa <n>
    email-nf-onedrive [--home DIR] testar-caixa [<n>]
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from email_nf_onedrive import __version__, segredos
from email_nf_onedrive.autorizacao import arquivo as arquivo_autorizacao
from email_nf_onedrive.autorizacao import fluxo
from email_nf_onedrive.autorizacao.credencial import ErroCredencial
from email_nf_onedrive.coleta import coleta
from email_nf_onedrive.coleta.imap import AUTENTICACAO, AUTORIZACAO, PASTA, ErroIMAP
from email_nf_onedrive.configuracao.carregar import carregar_configuracao
from email_nf_onedrive.configuracao.modelo import MODO_OAUTH, Caixa, Configuracao, ErroConfiguracao
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
    autorizar = sub.add_parser("autorizar-caixa", help="conduz o consentimento OAuth de uma caixa e grava a autorização")
    autorizar.add_argument("indice", type=int, metavar="n", help="índice da caixa no .env (EMAIL<n>)")
    testar = sub.add_parser("testar-caixa", help="autentica e abre a pasta de cada caixa, sem ler mensagens")
    testar.add_argument("indice", type=int, nargs="?", default=None, metavar="n",
                        help="índice da caixa no .env; sem ele, testa todas")
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


def _acesso(caixa: Caixa, config: Configuracao) -> str:
    """Final da linha do `verificar-config`. "Autorizada" diz só que o arquivo existe e é legível (RF-10)."""
    if caixa.modo != MODO_OAUTH:
        return f"senha {segredos.MASCARA}"
    autorizada = arquivo_autorizacao.existe_e_legivel(config.dir_autorizacoes, caixa.endereco)
    return "oauth (autorizada)" if autorizada else "oauth (sem autorização)"


def _verificar_config(home: Path) -> int:
    config = _carregar(home)
    if config is None:
        return 2
    for caixa in config.caixas:
        print(f"{caixa.indice} · {caixa.endereco} · {caixa.pasta} · {caixa.destino} · empresa {caixa.empresa} · "
              f"{_acesso(caixa, config)}")
    for invalida in config.caixas_invalidas:
        print(f"inválida: {invalida.motivo}")
    if any(caixa.modo == MODO_OAUTH for caixa in config.caixas):
        print("cliente OAuth: configurado")
        print(f"diretório de autorizações: {config.dir_autorizacoes}")
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


def _motivo_imap(caixa: Caixa, erro: ErroIMAP) -> str:
    if erro.causa == AUTORIZACAO:
        return f"autorização recusada; rode autorizar-caixa {caixa.indice}"
    if erro.causa == AUTENTICACAO:
        return "autenticação recusada"
    if erro.causa == PASTA:
        return f"pasta '{caixa.pasta}' inexistente"
    return f"servidor IMAP inacessível: {erro.detalhe}"


def _testar_caixa(home: Path, indice: int | None, deps: ciclo.Dependencias) -> int:
    """Autentica, abre a pasta com EXAMINE e encerra: uma tentativa por caixa, sem trava, aviso nem registro (D-11)."""
    config = _carregar(home)
    if config is None:
        return 2
    invalidas = {invalida.indice: invalida.motivo for invalida in config.caixas_invalidas}
    validas = {caixa.indice: caixa for caixa in config.caixas}
    if indice is not None and indice not in validas and indice not in invalidas:
        print(f"erro: caixa {indice} não existe no .env", file=sys.stderr)
        return 2
    if not validas:
        print("erro: nenhuma caixa válida no .env", file=sys.stderr)
        return 2
    provedor = ciclo.criar_provedor(config, deps, None)
    codigo = 0
    for n in sorted(validas.keys() | invalidas.keys()) if indice is None else [indice]:
        if n in invalidas:
            motivo = invalidas[n].removeprefix(f"caixa {n}: ")
        else:
            caixa, motivo = validas[n], None
            cliente = deps.fabrica_imap(caixa)
            try:
                coleta.conectar(cliente, caixa, provedor)
                cliente.examinar(caixa.pasta)
            except ErroCredencial as erro:
                motivo = erro.resumo
            except ErroIMAP as erro:
                motivo = _motivo_imap(caixa, erro)
            finally:
                cliente.encerrar()
        if motivo is None:
            print(f"caixa {n}: acesso confirmado ({validas[n].modo})")
        else:
            print(segredos.mascarar(f"caixa {n}: falhou ({motivo})"))
            codigo = 1
    return codigo


def _autorizar_caixa(home: Path, indice: int, deps: ciclo.Dependencias) -> int:
    """Consentimento OAuth de uma caixa (D-12): 0 quando grava a autorização, 2 em qualquer recusa."""
    config = _carregar(home)
    if config is None:
        return 2
    caixa = next((c for c in config.caixas if c.indice == indice), None)
    if caixa is None:
        invalida = next((i for i in config.caixas_invalidas if i.indice == indice), None)
        print("erro: " + (invalida.motivo if invalida else f"caixa {indice} não existe no .env"), file=sys.stderr)
        return 2
    if caixa.modo != MODO_OAUTH:
        print(f"erro: caixa {indice} não está em modo oauth (defina AUTH_EMAIL{indice}=oauth)", file=sys.stderr)
        return 2
    desfecho = fluxo.autorizar(caixa, config.cliente_oauth, config.dir_autorizacoes, deps.servico_autorizacao,
                               ao_exibir_endereco=deps.ao_exibir_endereco)
    for mensagem in desfecho.mensagens:
        texto = segredos.mascarar(mensagem)
        print(texto if desfecho.ok else f"erro: {texto}", file=sys.stdout if desfecho.ok else sys.stderr)
    return 0 if desfecho.ok else 2


def main(argv: list[str] | None = None, *, deps: ciclo.Dependencias | None = None) -> int:
    argumentos = _analisador().parse_args(argv)
    home = _home(argumentos.home)
    deps = deps or ciclo.Dependencias()
    if argumentos.comando == "executar":
        return ciclo.executar(home, simulacao=argumentos.simular, terminal=sys.stderr.isatty(), deps=deps)
    if argumentos.comando == "verificar-config":
        return _verificar_config(home)
    if argumentos.comando == "autorizar-caixa":
        return _autorizar_caixa(home, argumentos.indice, deps)
    if argumentos.comando == "testar-caixa":
        return _testar_caixa(home, argumentos.indice, deps)
    return _testar_onedrive(home, deps)


if __name__ == "__main__":
    sys.exit(main())
