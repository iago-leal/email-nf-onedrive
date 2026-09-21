"""Resumo de fim de execução (EM RF-11, entidade ResumoExecucao)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass
class ResumoExecucao:
    inicio: datetime
    caixas_processadas: int = 0
    extraidos: int = 0
    enviados: int = 0
    retidos: int = 0
    falhas: int = 0
    falhas_autorizacao: int = 0  # já incluídas em `falhas`; só as distingue na linha de resumo (feature 002, D-13)
    intervalo_desde_anterior: timedelta | None = None
    codigo_saida: int = 0
    fim: datetime | None = field(default=None)

    def encerrar(self, fim: datetime, codigo_saida: int) -> None:
        self.fim = fim
        self.codigo_saida = codigo_saida

    @property
    def duracao_s(self) -> int:
        if self.fim is None:
            return 0
        return round((self.fim - self.inicio).total_seconds())

    def linha(self) -> str:
        caixas = f"{self.caixas_processadas} caixa" + ("" if self.caixas_processadas == 1 else "s")
        partes = [caixas, f"{self.extraidos} extraídos", f"{self.enviados} enviados"]
        if self.retidos:
            partes.append(f"{self.retidos} retidos")
        partes.append(f"{self.falhas} falhas")
        if self.falhas_autorizacao:
            partes.append(f"{self.falhas_autorizacao} de autorização")
        partes.append(f"{self.duracao_s} s")
        texto = "resumo: " + ", ".join(partes)
        if self.intervalo_desde_anterior is not None:
            minutos = round(self.intervalo_desde_anterior.total_seconds() / 60)
            texto += f" (desde a execução anterior: {minutos} min)"
        return texto
