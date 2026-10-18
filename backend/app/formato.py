"""Formato de números para los mensajes en español."""

import math

MB = 1024 * 1024


def miles(n: int) -> str:
    """12345 -> '12.345'."""
    return f"{n:,}".replace(",", ".")


def megabytes(n_bytes: int) -> float:
    """Tamaño en MB redondeado hacia arriba a un decimal (5 MB + 1 byte -> 5.1)."""
    return math.ceil(n_bytes / MB * 10) / 10


def decimal_es(valor: float) -> str:
    """7.2 -> '7,2'; 5.0 -> '5'."""
    return f"{valor:.1f}".removesuffix(".0").replace(".", ",")
