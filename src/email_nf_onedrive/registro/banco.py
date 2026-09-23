"""Registro de processados em SQLite (data-delta.md, D-09, D-17).

Guarda só metadados, nunca o conteúdo dos anexos. Cada transição de estado tem
um único dono: `coleta` cria (`extraido` ou `retido`), `envio` conclui
(`enviado` ou `falha-envio`). Estados terminais não mudam.
"""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib import resources
from pathlib import Path

VERSAO_ESQUEMA = "1"
LIMITE_ERRO = 500
ESTADOS_INICIAIS = ("extraido", "retido")
ESTADOS_PENDENTES = ("extraido", "falha-envio")
TIPOS_OCORRENCIA = ("sem-anexo", "compactado")


class RegistroCorrompido(Exception):
    """O banco não abre ou falhou na verificação de integridade."""


class RegistroDuplicado(Exception):
    """Já existe anexo com a mesma chave (caixa, mensagem, conteúdo)."""


class TransicaoInvalida(Exception):
    """Transição de estado não permitida pela máquina de estados."""


@dataclass(frozen=True)
class Anexo:
    id: int
    caixa_endereco: str
    caixa_indice: int
    message_id: str
    sha256: str
    nome_original: str
    remetente: str
    assunto: str
    data_mensagem: datetime
    classe: str
    estado: str
    caminho_destino: str | None
    tentativas_envio: int
    ultimo_erro: str | None


@dataclass(frozen=True)
class EstadoAviso:
    causa: str
    primeira_ocorrencia: datetime
    ultimo_aviso: datetime | None
    ativa: bool
    mensagem: str
    entrega_pendente: bool


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def _dt(texto: str | None) -> datetime | None:
    return datetime.fromisoformat(texto) if texto else None


def _agora() -> str:
    return _iso(datetime.now(timezone.utc))


def _anexo(linha: sqlite3.Row) -> Anexo:
    dados = dict(linha)
    for descartado in ("criado_em", "atualizado_em"):
        dados.pop(descartado)
    dados["data_mensagem"] = _dt(dados["data_mensagem"])
    return Anexo(**dados)


def _aviso(linha: sqlite3.Row) -> EstadoAviso:
    return EstadoAviso(
        causa=linha["causa"],
        primeira_ocorrencia=_dt(linha["primeira_ocorrencia"]),
        ultimo_aviso=_dt(linha["ultimo_aviso"]),
        ativa=bool(linha["ativa"]),
        mensagem=linha["mensagem"],
        entrega_pendente=bool(linha["entrega_pendente"]),
    )


class Registro:
    def __init__(self, conexao: sqlite3.Connection, simulacao: bool) -> None:
        self._con = conexao
        self.simulacao = simulacao
        self._fechado = False

    # --- ciclo de vida --------------------------------------------------------

    @classmethod
    def abrir(cls, caminho: Path, *, simulacao: bool = False) -> "Registro":
        caminho = Path(caminho)
        if simulacao and not caminho.exists():
            alvo = ":memory:"  # simulação nunca cria o arquivo
        else:
            alvo = str(caminho)
            if not caminho.exists():
                caminho.parent.mkdir(parents=True, exist_ok=True)
                os.close(os.open(caminho, os.O_CREAT | os.O_WRONLY, 0o600))
        try:
            con = sqlite3.connect(alvo, isolation_level="DEFERRED")
            con.row_factory = sqlite3.Row
            if con.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise RegistroCorrompido(f"verificação de integridade falhou: {caminho}")
            registro = cls(con, simulacao)
            registro._aplicar_esquema()
        except sqlite3.DatabaseError as erro:
            raise RegistroCorrompido(f"registro ilegível: {caminho}: {erro}") from erro
        if alvo != ":memory:":
            os.chmod(caminho, 0o600)
        return registro

    def _aplicar_esquema(self) -> None:
        esquema = resources.files("email_nf_onedrive.registro").joinpath("esquema.sql").read_text("utf-8")
        self._con.executescript(esquema)
        self._con.execute(
            "INSERT OR IGNORE INTO meta (chave, valor) VALUES ('versao_esquema', ?)", (VERSAO_ESQUEMA,)
        )
        self.commit()

    def commit(self) -> None:
        if self.simulacao:
            return
        self._con.commit()

    def fechar(self, *, confirmar: bool = True) -> None:
        if self._fechado:
            return
        self._fechado = True
        if confirmar and not self.simulacao:
            self._con.commit()
        else:
            self._con.rollback()
        self._con.close()

    def __enter__(self) -> "Registro":
        return self

    def __exit__(self, tipo, _valor, _rastro) -> None:
        self.fechar(confirmar=tipo is None)

    # --- anexos -----------------------------------------------------------------

    def registrar_anexo(self, *, caixa_endereco: str, caixa_indice: int, message_id: str, sha256: str,
                        nome_original: str, remetente: str, assunto: str, data_mensagem: datetime,
                        classe: str, estado: str = "extraido") -> Anexo:
        if estado not in ESTADOS_INICIAIS:
            raise ValueError(f"estado inicial inválido: {estado}")
        agora = _agora()
        try:
            cursor = self._con.execute(
                """INSERT INTO anexos (caixa_endereco, caixa_indice, message_id, sha256, nome_original,
                       remetente, assunto, data_mensagem, classe, estado, criado_em, atualizado_em)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (caixa_endereco.lower(), caixa_indice, message_id, sha256, nome_original, remetente,
                 assunto, _iso(data_mensagem), classe, estado, agora, agora),
            )
        except sqlite3.IntegrityError as erro:
            raise RegistroDuplicado(f"{caixa_endereco} {message_id} {sha256}") from erro
        return self._por_id(cursor.lastrowid)

    def _por_id(self, anexo_id: int) -> Anexo:
        linha = self._con.execute("SELECT * FROM anexos WHERE id = ?", (anexo_id,)).fetchone()
        return _anexo(linha)

    def buscar(self, caixa_endereco: str, message_id: str, sha256: str) -> Anexo | None:
        linha = self._con.execute(
            "SELECT * FROM anexos WHERE caixa_endereco = ? AND message_id = ? AND sha256 = ?",
            (caixa_endereco.lower(), message_id, sha256),
        ).fetchone()
        return _anexo(linha) if linha else None

    def _exigir_pendente(self, anexo_id: int) -> Anexo:
        anexo = self._por_id(anexo_id)
        if anexo.estado not in ESTADOS_PENDENTES:
            raise TransicaoInvalida(f"anexo {anexo_id} em estado terminal {anexo.estado}")
        return anexo

    def marcar_enviado(self, anexo_id: int, caminho_destino: str) -> None:
        self._exigir_pendente(anexo_id)
        self._con.execute(
            "UPDATE anexos SET estado = 'enviado', caminho_destino = ?, atualizado_em = ? WHERE id = ?",
            (caminho_destino, _agora(), anexo_id),
        )

    def marcar_falha_envio(self, anexo_id: int, erro: str) -> int:
        anexo = self._exigir_pendente(anexo_id)
        tentativas = anexo.tentativas_envio + 1
        self._con.execute(
            """UPDATE anexos SET estado = 'falha-envio', tentativas_envio = ?, ultimo_erro = ?,
                   atualizado_em = ? WHERE id = ?""",
            (tentativas, erro[:LIMITE_ERRO], _agora(), anexo_id),
        )
        return tentativas

    def pendentes(self, caixa_endereco: str) -> list[Anexo]:
        linhas = self._con.execute(
            "SELECT * FROM anexos WHERE caixa_endereco = ? AND estado IN (?, ?) ORDER BY data_mensagem",
            (caixa_endereco.lower(), *ESTADOS_PENDENTES),
        ).fetchall()
        return [_anexo(linha) for linha in linhas]

    def ultima_data_mensagem(self, caixa_endereco: str) -> datetime | None:
        valor = self._con.execute(
            "SELECT max(data_mensagem) FROM anexos WHERE caixa_endereco = ?", (caixa_endereco.lower(),)
        ).fetchone()[0]
        return _dt(valor)

    def pendente_mais_antiga(self, caixa_endereco: str) -> datetime | None:
        valor = self._con.execute(
            "SELECT min(data_mensagem) FROM anexos WHERE caixa_endereco = ? AND estado IN (?, ?)",
            (caixa_endereco.lower(), *ESTADOS_PENDENTES),
        ).fetchone()[0]
        return _dt(valor)

    def mensagens_resolvidas(self, caixa_endereco: str) -> set[str]:
        """Mensagens já lidas sem nada pendente: todos os anexos em estado terminal, ou só ocorrência."""
        caixa = caixa_endereco.lower()
        linhas = self._con.execute(
            """SELECT message_id FROM anexos WHERE caixa_endereco = ?
               UNION SELECT message_id FROM ocorrencias WHERE caixa_endereco = ?
               EXCEPT SELECT message_id FROM anexos WHERE caixa_endereco = ? AND estado IN (?, ?)""",
            (caixa, caixa, caixa, *ESTADOS_PENDENTES),
        ).fetchall()
        return {linha[0] for linha in linhas}

    # --- ocorrências e meta -------------------------------------------------------

    def registrar_ocorrencia(self, caixa_endereco: str, message_id: str, tipo: str) -> bool:
        """Registra a ocorrência; devolve True só na primeira vez."""
        if tipo not in TIPOS_OCORRENCIA:
            raise ValueError(f"tipo de ocorrência inválido: {tipo}")
        cursor = self._con.execute(
            "INSERT OR IGNORE INTO ocorrencias (caixa_endereco, message_id, tipo, registrado_em) VALUES (?, ?, ?, ?)",
            (caixa_endereco.lower(), message_id, tipo, _agora()),
        )
        return cursor.rowcount == 1

    def meta_obter(self, chave: str) -> str | None:
        linha = self._con.execute("SELECT valor FROM meta WHERE chave = ?", (chave,)).fetchone()
        return linha[0] if linha else None

    def meta_definir(self, chave: str, valor: str) -> None:
        self._con.execute(
            "INSERT INTO meta (chave, valor) VALUES (?, ?) ON CONFLICT (chave) DO UPDATE SET valor = excluded.valor",
            (chave, valor),
        )

    # --- avisos ---------------------------------------------------------------------

    def aviso_obter(self, causa: str) -> EstadoAviso | None:
        linha = self._con.execute("SELECT * FROM avisos WHERE causa = ?", (causa,)).fetchone()
        return _aviso(linha) if linha else None

    def aviso_salvar(self, estado: EstadoAviso) -> None:
        self._con.execute(
            """INSERT INTO avisos (causa, primeira_ocorrencia, ultimo_aviso, ativa, mensagem, entrega_pendente)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT (causa) DO UPDATE SET
                   primeira_ocorrencia = excluded.primeira_ocorrencia,
                   ultimo_aviso = excluded.ultimo_aviso,
                   ativa = excluded.ativa,
                   mensagem = excluded.mensagem,
                   entrega_pendente = excluded.entrega_pendente""",
            (estado.causa, _iso(estado.primeira_ocorrencia),
             _iso(estado.ultimo_aviso) if estado.ultimo_aviso else None,
             int(estado.ativa), estado.mensagem, int(estado.entrega_pendente)),
        )

    def avisos_ativos(self) -> list[EstadoAviso]:
        linhas = self._con.execute("SELECT * FROM avisos WHERE ativa = 1 ORDER BY causa").fetchall()
        return [_aviso(linha) for linha in linhas]

    def avisos_com_entrega_pendente(self) -> list[EstadoAviso]:
        linhas = self._con.execute("SELECT * FROM avisos WHERE entrega_pendente = 1 ORDER BY causa").fetchall()
        return [_aviso(linha) for linha in linhas]
