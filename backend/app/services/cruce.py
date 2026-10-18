"""Tabla cruzada de dos columnas, con rangos opcionales en cada eje."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from ..errors import ErrorDataTab
from .avisos import Aviso
from .columnas import PerfilColumna, orden_natural, valores_numericos
from .frecuencias import porcentaje
from .rangos import (
    ETIQUETA_FUERA,
    ETIQUETA_SIN_VALOR,
    Rango,
    asignar,
    aviso_valores_no_numericos,
    pares_solapados,
    rangos_de_columna,
)

MAX_FILAS = 100
MAX_COLUMNAS = 100
MAX_CELDAS = 2500


@dataclass(frozen=True)
class _Eje:
    categorias: list[dict[str, Any]]  # tipo, etiqueta, rango
    codigos: np.ndarray  # categoría de cada registro
    agrupado: bool
    avisos: list[Aviso]


def calcular_tabla_cruzada(
    serie_fila: pd.Series,
    perfil_fila: PerfilColumna,
    rangos_fila: Sequence[str] | None,
    serie_columna: pd.Series,
    perfil_columna: PerfilColumna,
    rangos_columna: Sequence[str] | None,
) -> dict[str, Any]:
    """Resultado con la forma de `POST /api/datasets/{id}/tabla-cruzada`."""
    rangos_f = _rangos_sin_solapes(perfil_fila, rangos_fila)
    rangos_c = _rangos_sin_solapes(perfil_columna, rangos_columna)

    completos = serie_fila.notna() & serie_columna.notna()
    n = int(completos.sum())
    if n == 0:
        raise ErrorDataTab(
            "SIN_DATOS",
            f"Ninguna fila tiene valor a la vez en «{perfil_fila.nombre}» y «{perfil_columna.nombre}».",
            detalle={"columnas": [perfil_fila.nombre, perfil_columna.nombre]},
        )
    eje_f = _construir_eje(serie_fila[completos], perfil_fila, rangos_f)
    eje_c = _construir_eje(serie_columna[completos], perfil_columna, rangos_c)

    n_filas, n_columnas = len(eje_f.categorias), len(eje_c.categorias)
    if n_filas > MAX_FILAS or n_columnas > MAX_COLUMNAS or n_filas * n_columnas > MAX_CELDAS:
        raise ErrorDataTab(
            "DEMASIADAS_CATEGORIAS",
            f"El cruce tendría {n_filas} filas y {n_columnas} columnas, y es demasiado grande para mostrarlo.",
            "Usa columnas con menos valores distintos o agrupa los números en rangos.",
            {
                "filas": n_filas,
                "columnas": n_columnas,
                "max_filas": MAX_FILAS,
                "max_columnas": MAX_COLUMNAS,
                "max_celdas": MAX_CELDAS,
            },
        )

    conteo = np.bincount(eje_f.codigos * n_columnas + eje_c.codigos, minlength=n_filas * n_columnas)
    conteo = conteo.reshape(n_filas, n_columnas)
    totales_fila = conteo.sum(axis=1)
    filas = []
    for i, categoria in enumerate(eje_f.categorias):
        total = int(totales_fila[i])
        celdas = [
            {"frecuencia": int(conteo[i, j]), "porcentaje": porcentaje(int(conteo[i, j]), total, 1)}
            for j in range(n_columnas)
        ]
        filas.append({**categoria, "total": total, "celdas": celdas})
    totales_columna = [
        {"frecuencia": int(t), "porcentaje": porcentaje(int(t), n, 1)} for t in conteo.sum(axis=0)
    ]
    return {
        "fila": {"columna": perfil_fila.nombre, "agrupado": eje_f.agrupado},
        "columna": {"columna": perfil_columna.nombre, "agrupado": eje_c.agrupado},
        "n": n,
        "vacios_excluidos": len(serie_fila) - n,
        "columnas": eje_c.categorias,
        "filas": filas,
        "totales_columna": totales_columna,
        "avisos": eje_f.avisos + eje_c.avisos,
    }


def _rangos_sin_solapes(perfil: PerfilColumna, textos: Sequence[str] | None) -> list[Rango]:
    rangos = rangos_de_columna(perfil, textos)
    pares = pares_solapados(rangos)
    if pares:
        i, j = pares[0]
        raise ErrorDataTab(
            "RANGOS_SOLAPADOS_EN_CRUCE",
            f"Los rangos {rangos[i].texto} y {rangos[j].texto} se solapan y en un cruce contarían doble.",
            "Cambia los límites para que cada valor caiga en un solo rango.",
            {"columna": perfil.nombre, "rangos": [rangos[i].texto, rangos[j].texto]},
        )
    return rangos


def _construir_eje(serie: pd.Series, perfil: PerfilColumna, rangos: list[Rango]) -> _Eje:
    """`serie` ya no tiene vacíos: son las filas donde las dos columnas tienen valor."""
    if not rangos:
        codigos, unicos = pd.factorize(serie)
        etiquetas = unicos.tolist()
        orden = orden_natural(etiquetas, perfil.tipo)
        posicion = {etiqueta: i for i, etiqueta in enumerate(orden)}
        nueva_posicion = np.array([posicion[e] for e in etiquetas], dtype=np.int64)
        categorias = [{"tipo": "valor", "etiqueta": e, "rango": None} for e in orden]
        return _Eje(categorias, nueva_posicion[codigos], False, [])

    asignacion = asignar(valores_numericos(serie), rangos)
    codigos = np.full(len(serie), -1, dtype=np.int64)
    categorias = []
    for rango, mascara in zip(rangos, asignacion.por_rango, strict=True):  # sin solapes: cada registro cae en uno
        codigos[mascara] = len(categorias)
        categorias.append({"tipo": "rango", "etiqueta": rango.etiqueta, "rango": rango.texto})
    avisos = []
    if asignacion.fuera.any():
        codigos[asignacion.fuera] = len(categorias)
        categorias.append({"tipo": "fuera_de_rango", "etiqueta": ETIQUETA_FUERA, "rango": None})
    if asignacion.sin_valor.any():
        codigos[asignacion.sin_valor] = len(categorias)
        categorias.append({"tipo": "sin_valor_numerico", "etiqueta": ETIQUETA_SIN_VALOR, "rango": None})
        avisos.append(aviso_valores_no_numericos(perfil.nombre, int(asignacion.sin_valor.sum())))
    return _Eje(categorias, codigos, True, avisos)
