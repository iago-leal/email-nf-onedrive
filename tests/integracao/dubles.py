"""Dublês de teste: servidor IMAP em memória, serviço de autorização OAuth local e transporte de avisos."""

from __future__ import annotations

import base64
import imaplib
import json
import re
import threading
import time
from datetime import date
from email.utils import parsedate_to_datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

from email_nf_onedrive.coleta import utf7

_MESES = {m: i for i, m in enumerate(
    ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"), start=1)}


def _data_da_mensagem(bruto: bytes) -> date | None:
    for linha in bruto.split(b"\r\n\r\n", 1)[0].replace(b"\r\n", b"\n").split(b"\n"):
        if linha.lower().startswith(b"date:"):
            return parsedate_to_datetime(linha[5:].decode().strip()).date()
    return None


_SEM_SENHA = object()  # nenhuma senha confere: a caixa só entra por XOAUTH2

DESAFIO_XOAUTH2 = json.dumps({"status": "400", "schemes": "Bearer", "scope": "https://mail.google.com/"}).encode()


class ServidorIMAPFalso:
    """Caixas em memória, com registro de todos os comandos recebidos.

    `caixas` mapeia endereço -> (senha, {pasta: [mensagens brutas]}).
    `fora_do_ar` faz a conexão falhar com timeout.
    `credenciais_oauth` mapeia endereço -> credencial temporária aceita no XOAUTH2.
    """

    def __init__(self) -> None:
        self.caixas: dict[str, tuple[str, dict[str, list[bytes]]]] = {}
        self.comandos: list[tuple] = []
        self.fora_do_ar: set[str] = set()
        self.lidas: set[tuple[str, int]] = set()
        self.credenciais_oauth: dict[str, str] = {}

    def adicionar_caixa_oauth(self, endereco: str, credencial: str,
                              pastas: dict[str, list[bytes]] | None = None) -> None:
        """Caixa que só aceita AUTHENTICATE XOAUTH2 com a credencial temporária dada."""
        self.caixas[endereco] = (_SEM_SENHA, pastas or {"INBOX": []})
        self.credenciais_oauth[endereco] = credencial

    def adicionar_caixa(self, endereco: str, senha: str, pastas: dict[str, list[bytes]] | None = None) -> None:
        self.caixas[endereco] = (senha, pastas or {"INBOX": []})

    def entregar(self, endereco: str, bruto: bytes, pasta: str = "INBOX") -> None:
        self.caixas[endereco][1].setdefault(pasta, []).append(bruto)

    def fabrica(self, host: str, porta: int, timeout: float | None = None) -> "ConexaoFalsa":
        self.comandos.append(("CONNECT", host, porta, timeout))
        if host in self.fora_do_ar:
            raise TimeoutError("timed out")
        return ConexaoFalsa(self)

    def nomes_de_comandos(self) -> set[str]:
        return {c[0] for c in self.comandos}


class ConexaoFalsa:
    def __init__(self, servidor: ServidorIMAPFalso) -> None:
        self.servidor = servidor
        self.usuario: str | None = None
        self.pasta: list[bytes] | None = None

    def _registrar(self, *comando) -> None:
        self.servidor.comandos.append(comando)

    def login(self, usuario: str, senha: str):
        self._registrar("LOGIN", usuario)
        caixa = self.servidor.caixas.get(usuario)
        if caixa is None or caixa[0] != senha:
            raise imaplib.IMAP4.error("[AUTHENTICATIONFAILED] Invalid credentials (Failure)")
        self.usuario = usuario
        return "OK", [b"LOGIN completed"]

    def authenticate(self, mecanismo: str, funcao):
        """XOAUTH2 como o `imaplib` o conduz: desafio vazio, resposta inicial e, na recusa, desafio com JSON."""
        self._registrar("AUTHENTICATE", mecanismo)
        assert mecanismo == "XOAUTH2"
        partes = funcao(b"").split(b"\x01")
        assert len(partes) == 4 and partes[2:] == [b"", b""], "resposta inicial XOAUTH2 malformada"
        usuario = partes[0].removeprefix(b"user=").decode()
        credencial = partes[1].removeprefix(b"auth=Bearer ").decode()
        if self.servidor.credenciais_oauth.get(usuario) != credencial:
            assert funcao(DESAFIO_XOAUTH2) == b"", "o cliente deve responder ao desafio com linha vazia"
            raise imaplib.IMAP4.error("[AUTHENTICATIONFAILED] Invalid credentials (Failure)")
        self.usuario = usuario
        return "OK", [b"Success"]

    def list(self):
        self._registrar("LIST")
        pastas = self.servidor.caixas[self.usuario][1]
        return "OK", [f'(\\HasNoChildren) "/" "{utf7.codificar(p)}"'.encode() for p in pastas]

    def select(self, mailbox: str, readonly: bool = False):
        self._registrar("EXAMINE" if readonly else "SELECT", mailbox)
        nome = utf7.decodificar(mailbox.strip('"'))
        pastas = self.servidor.caixas[self.usuario][1]
        if nome not in pastas:
            return "NO", [b"[NONEXISTENT] Unknown Mailbox"]
        self.pasta = pastas[nome]
        return "OK", [str(len(self.pasta)).encode()]

    def search(self, charset, *criterios):
        self._registrar("SEARCH", *criterios)
        assert criterios[0] == "SINCE"
        dia, mes, ano = criterios[1].split("-")
        desde = date(int(ano), _MESES[mes], int(dia))
        numeros = [
            str(i).encode() for i, bruto in enumerate(self.pasta, start=1)
            if (_data_da_mensagem(bruto) or desde) >= desde
        ]
        return "OK", [b" ".join(numeros)]

    def fetch(self, numeros: bytes, partes: str):
        self._registrar("FETCH", numeros, partes)
        resposta = []
        for numero in numeros.split(b","):
            bruto = self.pasta[int(numero) - 1]
            if "PEEK" not in partes:
                self.servidor.lidas.add((self.usuario, int(numero)))
            if "HEADER.FIELDS" in partes:
                cabecalhos = re.split(rb"\r?\n\r?\n", bruto, maxsplit=1)[0]
                cabecalho = b"".join(
                    linha + b"\r\n" for linha in cabecalhos.splitlines() if linha.lower().startswith(b"message-id:")
                ) + b"\r\n"
                resposta += [(numero + b" (BODY[HEADER.FIELDS (MESSAGE-ID)] {%d}" % len(cabecalho), cabecalho), b")"]
            else:
                resposta += [(numero + b" (BODY[] {%d}" % len(bruto), bruto), b")"]
        return "OK", resposta

    def logout(self):
        self._registrar("LOGOUT")
        return "BYE", [b"LOGOUT"]

    def __getattr__(self, nome: str):
        # Qualquer comando fora da lista (store, copy, expunge...) é registrado e falha.
        def proibido(*args):
            self._registrar(nome.upper(), *args)
            raise AssertionError(f"comando IMAP proibido: {nome}")
        return proibido


class TransporteFalso:
    """Substitui o Telegram: guarda as mensagens e pode simular indisponibilidade."""

    def __init__(self) -> None:
        self.enviadas: list[str] = []
        self.disponivel = True

    def __call__(self, texto: str) -> tuple[bool, str | None]:
        if not self.disponivel:
            return False, "timeout"
        self.enviadas.append(texto)
        return True, None


def id_token_falso(email: str | None, verificado: bool = True) -> str:
    """JWT sem assinatura válida, como o código o lê: só o segmento do meio importa."""
    corpo = {"iss": "https://accounts.google.com", "email_verified": verificado}
    if email is not None:
        corpo["email"] = email
    b64 = lambda dado: base64.urlsafe_b64encode(json.dumps(dado).encode()).rstrip(b"=").decode()
    return f"{b64({'alg': 'RS256'})}.{b64(corpo)}.assinatura"


class ServicoAutorizacaoFalso:
    """Serviço de autorização do Google em `127.0.0.1`, em linha de execução própria.

    Rotas: `POST /token` (troca do código e renovação) e `POST /revoke`. As respostas
    são programadas por `refresh_token` e por `code`; o que não foi programado recebe
    `invalid_grant`. `requisicoes` guarda (rota, campos) de tudo o que chegou.
    """

    ERROS = {"invalid_grant": 400, "invalid_client": 401, "unauthorized_client": 400, "invalid_scope": 400}

    def __init__(self) -> None:
        self.renovacoes: dict[str, tuple[str, str]] = {}
        self.trocas: dict[str, dict | str] = {}
        self.requisicoes: list[tuple[str, dict[str, str]]] = []
        self.revogados: list[str] = []
        self.revogacao_disponivel = True
        self.atraso_s = 1.0
        servico = self

        class Manipulador(BaseHTTPRequestHandler):
            def log_message(self, *_args) -> None:
                pass

            def do_POST(self) -> None:
                tamanho = int(self.headers.get("Content-Length") or 0)
                campos = {k: v[0] for k, v in parse_qs(self.rfile.read(tamanho).decode()).items()}
                servico.requisicoes.append((self.path, campos))
                estado, corpo = servico._responder(self.path, campos)
                dados = corpo if isinstance(corpo, bytes) else json.dumps(corpo).encode()
                try:
                    self.send_response(estado)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(dados)))
                    self.end_headers()
                    self.wfile.write(dados)
                except OSError:  # o cliente desistiu (teste de tempo esgotado)
                    pass

        self._servidor = ThreadingHTTPServer(("127.0.0.1", 0), Manipulador)
        self._servidor.daemon_threads = True
        self._linha = threading.Thread(target=self._servidor.serve_forever, args=(0.02,), daemon=True)
        self._linha.start()

    # --- programação ------------------------------------------------------------------

    def programar_renovacao(self, refresh_token: str, resposta: str = "ok", access_token: str = "") -> None:
        """`resposta`: ok, um nome de `ERROS`, 503, 429, json-invalido, sem-access-token ou lento."""
        self.renovacoes[refresh_token] = (resposta, access_token)

    def programar_troca(self, code: str, *, email: str | None, refresh_token: str | None = "1//durável-nova",
                        scope: str = "https://mail.google.com/ openid email", verificado: bool = True,
                        access_token: str = "ya29.troca") -> None:
        corpo = {"access_token": access_token, "expires_in": 3599, "scope": scope, "token_type": "Bearer",
                 "id_token": id_token_falso(email, verificado)}
        if refresh_token is not None:
            corpo["refresh_token"] = refresh_token
        self.trocas[code] = corpo

    # --- respostas --------------------------------------------------------------------

    def _erro(self, nome: str) -> tuple[int, dict]:
        return self.ERROS[nome], {"error": nome, "error_description": f"descrição de {nome}"}

    def _responder(self, rota: str, campos: dict[str, str]) -> tuple[int, dict | bytes]:
        if rota == "/revoke":
            if not self.revogacao_disponivel:
                return 503, {"error": "indisponivel"}
            self.revogados.append(campos.get("token", ""))
            return 200, {}
        if rota != "/token":
            return 404, {"error": "rota"}
        if campos.get("grant_type") == "authorization_code":
            resposta = self.trocas.get(campos.get("code", ""), "invalid_grant")
            return self._erro(resposta) if isinstance(resposta, str) else (200, resposta)
        resposta, access_token = self.renovacoes.get(campos.get("refresh_token", ""), ("invalid_grant", ""))
        if resposta == "ok":
            return 200, {"access_token": access_token, "expires_in": 3599, "token_type": "Bearer",
                         "scope": "https://mail.google.com/"}
        if resposta in self.ERROS:
            return self._erro(resposta)
        if resposta in ("503", "429"):
            return int(resposta), {"error": "indisponivel"}
        if resposta == "json-invalido":
            return 200, b"<html>isto nao e json</html>"
        if resposta == "sem-access-token":
            return 200, {"expires_in": 3599}
        if resposta == "lento":
            time.sleep(self.atraso_s)
            return 200, {"access_token": access_token, "expires_in": 3599}
        raise AssertionError(f"resposta não programável: {resposta}")

    # --- consulta ---------------------------------------------------------------------

    @property
    def base(self) -> str:
        return f"http://127.0.0.1:{self._servidor.server_address[1]}"

    def contagem(self, rota: str = "/token", grant_type: str | None = None) -> int:
        return sum(1 for r, campos in self.requisicoes
                   if r == rota and (grant_type is None or campos.get("grant_type") == grant_type))

    def encerrar(self) -> None:
        if self._linha.is_alive():
            self._servidor.shutdown()
            self._linha.join()
        self._servidor.server_close()
