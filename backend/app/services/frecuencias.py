"""Tabla de frecuencias de una columna, con o sin rangos."""

from collections.abc import Sequence
from typing import Any

import numpy as np
import pandas as pd

from ..errors import ErrorDataTab
from ..formato import miles
from .avisos import Aviso, aviso
from .columnas import PerfilColumna, clave_texto, orden_natural, valores_numericos
from .rangos import (
    ETIQUETA_FUERA,
    ETIQUETA_SIN_VALOR,
    Rango,
    asignar,
    aviso_valores_no_numericos,
    pares_solapados,
    rangos_de_columna,
)

MAX_AVISOS_SOLAPE = 5


def porcentaje(parte: int, total: int, decimales: int) -> float:
    return round(parte / total * 100, decimales) if total else 0.0


def calcular_frecuencias(
    serie: pd.Series, perfil: PerfilColumna, rangos_texto: Sequence[str] | None, max_valores_distintos: int
) -> dict[str, Any]:
    """Resultado con la forma de `POST /api/datasets/{id}/frecuencias`.

    Sin rangos hay una fila por valor distinto: si son más de `max_valores_distintos`, se rechaza.
    """
    rangos = rangos_de_columna(perfil, rangos_texto)
    validos = serie.dropna()
    n = len(validos)
    if n == 0:
        raise ErrorDataTab(
            "SIN_DATOS",
            f"La columna «{perfil.nombre}» no tiene ningún valor.",
            detalle={"columna": perfil.nombre},
        )
    if rangos:
        filas, solapados, avisos = _con_rangos(validos, perfil, rangos, n)
    else:
        filas, solapados, avisos = _sin_rangos(validos, perfil, n, max_valores_distintos), 0, []
    return {
        "columna": perfil.nombre,
        "tipo": perfil.tipo,
        "agrupado": bool(rangos),
        "n": n,
        "vacios_excluidos": len(serie) - n,
        "filas": filas,
        "solapados": solapados,
        "avisos": avisos,
    }


def _fila(tipo: str, etiqueta: str, rango: str | None, frecuencia: int, n: int) -> dict[str, Any]:
    return {
        "tipo": tipo,
        "etiqueta": etiqueta,
        "rango": rango,
        "frecuencia": frecuencia,
        "porcentaje": porcentaje(frecuencia, n, 2),
    }


def _demasiados_valores(perfil: PerfilColumna, distintos: int, maximo: int) -> ErrorDataTab:
    if perfil.tipo == "numerica":
        sugerencia = "Agrúpalos en rangos, por ejemplo 0-9, 10-19…"
    else:
        sugerencia = "Elige otra columna o limpia el archivo para unificar valores parecidos."
    return ErrorDataTab(
        "DEMASIADAS_CATEGORIAS",
        f"«{perfil.nombre}» tiene {miles(distintos)} valores distintos; son demasiados para una tabla de frecuencias.",
        sugerencia,
        {"valores_distintos": distintos, "maximo": maximo},
    )


def _sin_rangos(validos: pd.Series, perfil: PerfilColumna, n: int, maximo: int) -> list[dict[str, Any]]:
    conteo = validos.value_counts()
    if len(conteo) > maximo:
        raise _demasiados_valores(perfil, len(conteo), maximo)
    frecuencia = dict(zip(conteo.index.tolist(), conteo.tolist(), strict=True))
    if perfil.tipo == "texto":  # más frecuentes primero; en empate, alfabético
        orden = sorted(frecuencia, key=lambda v: (-frecuencia[v], clave_texto(v), v))
    else:
        orden = orden_natural(frecuencia, perfil.tipo)
    return [_fila("valor", valor, None, frecuencia[valor], n) for valor in orden]


def _con_rangos(
    validos: pd.Series, perfil: PerfilColumna, rangos: list[Rango], n: int
) -> tuple[list[dict[str, Any]], int, list[Aviso]]:
    asignacion = asignar(valores_numericos(validos), rangos)
    filas = [
        _fila("rango", rango.etiqueta, rango.texto, int(mascara.sum()), n)
        for rango, mascara in zip(rangos, asignacion.por_rango, strict=True)
    ]
    fuera = int(asignacion.fuera.sum())
    sin_valor = int(asignacion.sin_valor.sum())
    if fuera:
        filas.append(_fila("fuera_de_rango", ETIQUETA_FUERA, None, fuera, n))
    if sin_valor:
        filas.append(_fila("sin_valor_numerico", ETIQUETA_SIN_VALOR, None, sin_valor, n))

    solapados = int((np.sum(asignacion.por_rango, axis=0) > 1).sum())
    avisos = _avisos_solapes(rangos, asignacion.por_rango) if solapados else []
    if sin_valor:
        avisos.append(aviso_valores_no_numericos(perfil.nombre, sin_valor))
    return filas, solapados, avisos


def _avisos_solapes(rangos: list[Rango], mascaras: list[np.ndarray]) -> list[Aviso]:
    """Un aviso por cada pareja de rangos que comparte algún registro."""
    mensajes = []
    for i, j in pares_solapados(rangos):
        compartidos = int((mascaras[i] & mascaras[j]).sum())
        if compartidos:
            cuenta = "1 registro se cuenta dos veces" if compartidos == 1 else f"{compartidos} registros se cuentan dos veces"
            mensajes.append(f"Los rangos {rangos[i].texto} y {rangos[j].texto} se solapan: {cuenta}.")
    avisos = [aviso("RANGOS_SOLAPADOS", "atencion", m) for m in mensajes[:MAX_AVISOS_SOLAPE]]
    if len(mensajes) > MAX_AVISOS_SOLAPE:
        resto = len(mensajes) - MAX_AVISOS_SOLAPE
        avisos.append(aviso("RANGOS_SOLAPADOS", "atencion", f"Hay {resto} parejas de rangos más que también se solapan."))
    return avisos
