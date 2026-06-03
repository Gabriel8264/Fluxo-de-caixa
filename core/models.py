from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class MovementType(StrEnum):
    ENTRADA = "entrada"
    SAIDA = "saída"

    @property
    def label(self) -> str:
        return self.value.capitalize()

    @property
    def storage_value(self) -> str:
        return "saida" if self is self.SAIDA else self.value

    @classmethod
    def from_db(cls, value: str) -> "MovementType":
        normalized = (value or "").strip().lower()
        if normalized in {"saida", "saída", "pagar"}:
            return cls.SAIDA
        return cls.ENTRADA

    @property
    def direction(self) -> int:
        return 1 if self is self.ENTRADA else -1


PAYMENT_METHODS = ["dinheiro", "pix", "débito", "crédito"]


@dataclass(slots=True)
class RegistryItem:
    nome: str
    id: int | None = None


@dataclass(slots=True)
class Technician:
    nome: str
    percentual_comissao: float
    status: str = "ativo"
    id: int | None = None

    @property
    def percentual_empresa(self) -> float:
        return round(100.0 - self.percentual_comissao, 2)


@dataclass(slots=True)
class Movement:
    tipo: str
    valor: float
    descricao: str
    categoria: str
    metodo: str
    pessoa: str
    data: str
    anexo: str = ""
    grupo_servico: str = ""
    papel_servico: str = ""
    tecnico: str = ""
    divisao_tecnicos: str = ""
    percentual_comissao_tecnico: float = 0.0
    valor_comissao_tecnico: float = 0.0
    valor_empresa: float = 0.0
    id: int | None = None

    @property
    def movement_type(self) -> MovementType:
        return MovementType.from_db(self.tipo)

    @property
    def display_type(self) -> str:
        return self.movement_type.value

    @property
    def signed_value(self) -> float:
        return self.valor if self.movement_type is MovementType.ENTRADA else -self.valor

    @property
    def formatted_date(self) -> str:
        try:
            return date.fromisoformat(self.data).strftime("%d/%m/%Y")
        except ValueError:
            return self.data


@dataclass(slots=True)
class CycleSummary:
    ciclo: str
    inicio: str
    fim: str
    entradas: float
    saidas: float
    saldo: float
    quantidade: int


@dataclass(slots=True)
class DailyFlowSummary:
    data: str
    entradas: float
    saidas: float
    saldo: float
    quantidade: int


@dataclass(slots=True)
class CompanyCashAdjustment:
    tipo: str
    valor: float
    descricao: str
    data: str
    saldo_antes: float
    saldo_depois: float
    created_at: str = ""
    id: int | None = None

    @property
    def formatted_date(self) -> str:
        try:
            return date.fromisoformat(self.data).strftime("%d/%m/%Y")
        except ValueError:
            return self.data
