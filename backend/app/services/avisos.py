"""Avisos del contrato: acompañan a un resultado válido, no son errores."""

from typing import Literal, TypedDict


class Aviso(TypedDict):
    codigo: str
    nivel: Literal["info", "atencion"]
    mensaje: str


def aviso(codigo: str, nivel: Literal["info", "atencion"], mensaje: str) -> Aviso:
    return {"codigo": codigo, "nivel": nivel, "mensaje": mensaje}
