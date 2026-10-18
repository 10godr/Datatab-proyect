import re
import pandas as pd
from typing import List


def calcular_frecuencias(df: pd.DataFrame, columna: str) -> dict:
    """Calcula frecuencias absolutas y relativas de una columna."""
    serie = df[columna].dropna()
    total = len(serie)
    es_numerica = pd.api.types.is_numeric_dtype(serie)

    conteo = serie.value_counts().reset_index()
    conteo.columns = ["valor", "frecuencia"]
    conteo["porcentaje"] = (conteo["frecuencia"] / total * 100).round(2)

    resultado = conteo.to_dict(orient="records")
    for r in resultado:
        r["valor"] = str(r["valor"])

    return {
        "columna": columna,
        "total": total,
        "es_numerica": es_numerica,
        "frecuencias": resultado,
    }


def calcular_frecuencias_con_rangos(df: pd.DataFrame, columna: str, rangos_texto: List[str]) -> dict:
    """
    Calcula frecuencias agrupando valores numéricos en rangos definidos por el usuario.
    Soporta: <30, >60, >=60, 30-39, 40+
    """
    serie = df[columna].dropna()
    total = len(serie)
    resultado = []

    for rango in rangos_texto:
        rango = rango.strip()
        if not rango:
            continue

        frecuencia = _parse_rango(serie, rango)
        resultado.append({
            "valor": rango,
            "frecuencia": frecuencia,
            "porcentaje": round(frecuencia / total * 100, 2) if total > 0 else 0,
        })

    return {
        "columna": columna,
        "total": total,
        "es_numerica": True,
        "frecuencias": resultado,
    }


def _parse_rango(serie: pd.Series, rango: str) -> int:
    """Parsea un string de rango y retorna la frecuencia."""
    # < X
    m = re.match(r"^[<＜]\s*(\d+\.?\d*)$", rango)
    if m:
        return int((serie < float(m.group(1))).sum())

    # >= X o > X
    m = re.match(r"^(>=?|≥)\s*(\d+\.?\d*)$", rango)
    if m:
        op, val = m.group(1), float(m.group(2))
        return int((serie >= val).sum() if op in (">=", "≥") else (serie > val).sum())

    # X+
    m = re.match(r"^(\d+\.?\d*)\s*\+$", rango)
    if m:
        return int((serie >= float(m.group(1))).sum())

    # X - Y
    m = re.match(r"^(\d+\.?\d*)\s*[-–]\s*(\d+\.?\d*)$", rango)
    if m:
        a, b = float(m.group(1)), float(m.group(2))
        return int(((serie >= a) & (serie <= b)).sum())

    return 0


def calcular_tabla_cruzada(df: pd.DataFrame, col_fila: str, col_columna: str) -> dict:
    """
    Genera una tabla cruzada entre dos variables.
    Retorna frecuencias y porcentajes por fila.
    """
    # Limpiar filas donde alguna de las dos columnas sea nula
    df_clean = df[[col_fila, col_columna]].dropna()
    total = len(df_clean)

    # Tabla cruzada de frecuencias
    tabla = pd.crosstab(df_clean[col_fila], df_clean[col_columna])
    tabla_pct = pd.crosstab(df_clean[col_fila], df_clean[col_columna], normalize="index") * 100

    columnas = tabla.columns.tolist()
    filas = []

    for idx in tabla.index:
        fila_data = {
            "etiqueta": str(idx),
            "total_fila": int(tabla.loc[idx].sum()),
            "celdas": []
        }
        for col in columnas:
            fila_data["celdas"].append({
                "columna": str(col),
                "frecuencia": int(tabla.loc[idx, col]),
                "porcentaje": round(float(tabla_pct.loc[idx, col]), 1),
            })
        filas.append(fila_data)

    # Totales por columna
    totales_col = {str(col): int(tabla[col].sum()) for col in columnas}

    return {
        "col_fila": col_fila,
        "col_columna": col_columna,
        "total": total,
        "columnas": [str(c) for c in columnas],
        "filas": filas,
        "totales_col": totales_col,
    }
