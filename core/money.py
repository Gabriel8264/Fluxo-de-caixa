from __future__ import annotations
"""Utilitarios para valores monetarios no padrao brasileiro."""

from decimal import Decimal, InvalidOperation


def brazilian_decimal_separator_index(cleaned: str) -> int | None:
    """Retorna o separador decimal em texto ja filtrado, quando existir."""
    separators = [index for index, char in enumerate(cleaned) if char in ",."]
    if not separators:
        return None

    last_separator = separators[-1]
    decimal_digits = "".join(char for char in cleaned[last_separator + 1 :] if char.isdigit())
    if cleaned[last_separator] == ",":
        return last_separator
    if cleaned.count(".") == 1 and 1 <= len(decimal_digits) <= 2:
        return last_separator
    return None


def parse_brazilian_money_parts(value: str | float | int | Decimal) -> tuple[str, str] | None:
    """Converte entrada monetaria para partes numericas de reais e centavos."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float | Decimal):
        try:
            numeric = Decimal(str(value))
        except InvalidOperation:
            return None
        formatted = f"{numeric:f}"
        integer_part, _, decimal_part = formatted.partition(".")
        return integer_part or "0", decimal_part[:2].ljust(2, "0")

    raw = str(value).strip()
    negative = raw.startswith("-")
    cleaned = "".join(char for char in raw if char.isdigit() or char in ",.")
    if not cleaned:
        return None

    decimal_separator = brazilian_decimal_separator_index(cleaned)
    if decimal_separator is not None:
        decimal_digits = "".join(char for char in cleaned[decimal_separator + 1 :] if char.isdigit())
        integer_digits = "".join(char for char in cleaned[:decimal_separator] if char.isdigit()) or "0"
        if negative:
            integer_digits = f"-{integer_digits}"
        return integer_digits, decimal_digits[:2].ljust(2, "0")

    digits = "".join(char for char in cleaned if char.isdigit())
    if not digits:
        return None
    if negative:
        digits = f"-{digits}"
    return digits, "00"


def parse_brazilian_money(value: str | float | int | Decimal) -> float:
    """Converte texto monetario brasileiro para float."""
    parsed = parse_brazilian_money_parts(value)
    if parsed is None:
        raise ValueError("Informe um valor numerico valido.")
    integer_part, decimal_part = parsed
    return float(f"{int(integer_part or '0')}.{decimal_part[:2].ljust(2, '0')}")
