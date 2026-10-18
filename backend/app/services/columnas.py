"""Valores normalizados, tipos de columna y perfilado.

Una tabla en memoria es un DataFrame cuyas columnas son texto (dtype "str", vacío = NaN)
con el valor ya normalizado: es el texto con el que se cuenta y se muestra.
"""

import datetime as dt
import math
import re
import unicodedata
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass
from typing import Any, Literal

import numpy as np
import pandas as pd

from .avisos import Aviso, aviso

TipoColumna = Literal["numerica", "texto", "fecha"]

UMBRAL_NUMERICO = 0.9
MAX_GRUPOS_PARECIDOS = 3
MAX_VARIANTES_MOSTRADAS = 4

_NUMERO = re.compile(r"[+-]?(?:[0-9]+(?:[.,][0-9]+)?|[.,][0-9]+)")
_FECHA = re.compile(r"([0-9]{4})-([0-9]{2})-([0-9]{2})(?: ([0-9]{2}):([0-9]{2}))?")


@dataclass(frozen=True)
class PerfilColumna:
    nombre: str
    tipo: TipoColumna
    vacios: int
    distintos: int
    no_numericos: int
    minimo: int | float | None
    maximo: int | float | None

    def como_dict(self) -> dict[str, Any]:
        return asdict(self)


# --- Valor normalizado --------------------------------------------------------------


def formatear_numero(numero: int | float) -> str:
    """30.0 -> '30'; 1.5 -> '1.5'; sin notación científica."""
    if isinstance(numero, int):
        return str(numero)
    texto = f"{numero:.15g}"  # 15 cifras significativas: oculta el ruido binario (0.1+0.2)
    if "e" in texto:
        mantisa, _, exponente = texto.partition("e")
        texto = _sin_exponente(mantisa, int(exponente))
    return "0" if texto == "-0" else texto


def _sin_exponente(mantisa: str, exponente: int) -> str:
    signo = "-" if mantisa.startswith("-") else ""
    entera, _, decimal = mantisa.lstrip("-").partition(".")
    cifras = entera + decimal
    posicion = len(entera) + exponente
    if posicion <= 0:
        cuerpo = "0." + "0" * -posicion + cifras
    elif posicion >= len(cifras):
        cuerpo = cifras + "0" * (posicion - len(cifras))
    else:
        cuerpo = cifras[:posicion] + "." + cifras[posicion:]
    return signo + cuerpo


def normalizar_valor(valor: Any) -> str | None:
    """Convierte un valor de celda al texto con el que se cuenta; None si está vacío."""
    if valor is None:
        return None
    tipo = type(valor)
    if tipo is str:
        return " ".join(valor.split()) or None
    if tipo is bool:
        return "Verdadero" if valor else "Falso"
    if tipo is int:
        return str(valor)
    if tipo is float:
        return formatear_numero(valor) if math.isfinite(valor) else None
    if isinstance(valor, dt.datetime):
        fecha = valor.date().isoformat()
        if valor.hour or valor.minute or valor.second or valor.microsecond:
            return f"{fecha} {valor.hour:02d}:{valor.minute:02d}"
        return fecha
    if isinstance(valor, dt.date):
        return valor.isoformat()
    if isinstance(valor, dt.time):
        return f"{valor.hour:02d}:{valor.minute:02d}"
    if isinstance(valor, dt.timedelta):
        horas, resto = divmod(int(valor.total_seconds()), 3600)
        return f"{horas}:{resto // 60:02d}"
    return " ".join(str(valor).split()) or None


# --- Números y fechas escritos como texto -----------------------------------------------


def parsear_numero(texto: str) -> float | None:
    """'34', '1,5', '-2.5' -> número; cualquier otra cosa ('N/D', '31-40', '1e5') -> None."""
    if not _NUMERO.fullmatch(texto):
        return None
    numero = float(texto.replace(",", "."))
    return numero if math.isfinite(numero) else None


def numero_canonico(texto: str) -> str:
    """Texto numérico con la forma normalizada, sin perder cifras: '007' -> '7', '1,50' -> '1.5'."""
    signo = "-" if texto.startswith("-") else ""
    entera, _, decimal = texto.lstrip("+-").replace(",", ".").partition(".")
    entera = entera.lstrip("0") or "0"
    decimal = decimal.rstrip("0")
    cuerpo = entera + ("." + decimal if decimal else "")
    return cuerpo if cuerpo == "0" else signo + cuerpo


def es_fecha(texto: str) -> bool:
    """'AAAA-MM-DD' o 'AAAA-MM-DD HH:MM' con una fecha y hora reales."""
    partes = _FECHA.fullmatch(texto)
    if not partes:
        return False
    try:
        dt.date(int(partes[1]), int(partes[2]), int(partes[3]))
    except ValueError:
        return False
    return partes[4] is None or (int(partes[4]) < 24 and int(partes[5]) < 60)


def _numero_publico(numero: float) -> int | float:
    return int(numero) if numero.is_integer() and abs(numero) < 2**53 else numero


def valores_numericos(serie: pd.Series) -> np.ndarray:
    """float64 con NaN donde el valor está vacío o no es un número."""
    mapa = {}
    for texto in serie.dropna().unique():
        numero = parsear_numero(texto)
        if numero is not None:
            mapa[texto] = numero
    return serie.map(mapa).to_numpy(dtype="float64", na_value=np.nan)


# --- Orden y comparación de textos ------------------------------------------------------


def clave_texto(texto: str) -> str:
    """Minúsculas, sin tildes y con espacios colapsados: para ordenar y comparar."""
    sin_tildes = "".join(c for c in unicodedata.normalize("NFD", texto) if not unicodedata.combining(c))
    return " ".join(sin_tildes.casefold().split())


def _clave_numerica(texto: str) -> tuple[int, float, str, str]:
    numero = parsear_numero(texto)
    if numero is not None:
        return (0, numero, "", "")
    return (1, 0.0, clave_texto(texto), texto)  # lo no numérico, al final


def _clave_alfabetica(texto: str) -> tuple[str, str]:
    return (clave_texto(texto), texto)


def orden_natural(valores: Iterable[str], tipo: TipoColumna) -> list[str]:
    """Números y fechas de menor a mayor; texto alfabético sin distinguir tildes ni mayúsculas."""
    clave: Callable[[str], Any]
    if tipo == "numerica":
        clave = _clave_numerica
    elif tipo == "fecha":
        clave = str  # AAAA-MM-DD ordena igual como texto
    else:
        clave = _clave_alfabetica
    return sorted(valores, key=clave)


# --- Perfilado ----------------------------------------------------------------------------


def _lista_es(valores: list[str]) -> str:
    citados = [f"«{v}»" for v in valores]
    return citados[0] if len(citados) == 1 else ", ".join(citados[:-1]) + " y " + citados[-1]


def _aviso_valores_parecidos(nombre: str, cuentas: dict[str, int]) -> Aviso | None:
    grupos: dict[str, list[str]] = {}
    for valor in cuentas:
        grupos.setdefault(clave_texto(valor), []).append(valor)
    repetidos = [sorted(g, key=lambda v: (-cuentas[v], v)) for _, g in sorted(grupos.items()) if len(g) > 1]
    if not repetidos:
        return None
    ejemplos = "; ".join(_lista_es(g[:MAX_VARIANTES_MOSTRADAS]) for g in repetidos[:MAX_GRUPOS_PARECIDOS])
    mensaje = f"En «{nombre}»: {ejemplos} parecen el mismo valor pero se cuentan por separado."
    if len(repetidos) > MAX_GRUPOS_PARECIDOS:
        mensaje += f" Hay {len(repetidos) - MAX_GRUPOS_PARECIDOS} casos más."
    return aviso("VALORES_PARECIDOS", "info", mensaje)


def perfilar_columna(nombre: str, serie: pd.Series) -> tuple[pd.Series, PerfilColumna, list[Aviso]]:
    """Decide el tipo de la columna y devuelve la serie ya normalizada para ese tipo.

    En columnas numéricas los textos que parecen números pasan a su forma normalizada
    (`"1,5"` -> `"1.5"`), de modo que cuenten igual que los números reales.
    """
    conteos = serie.value_counts()
    valores: list[str] = conteos.index.tolist()
    cuentas: list[int] = conteos.tolist()
    total = sum(cuentas)
    vacios = len(serie) - total
    if total == 0:
        return serie, PerfilColumna(nombre, "texto", vacios, 0, 0, None, None), []

    if all(es_fecha(v) for v in valores):
        return serie, PerfilColumna(nombre, "fecha", vacios, len(valores), 0, None, None), []

    numeros = [parsear_numero(v) for v in valores]
    numericos = sum(c for c, n in zip(cuentas, numeros, strict=True) if n is not None)
    if numericos >= UMBRAL_NUMERICO * total:
        canonicos = {v: numero_canonico(v) if n is not None else v for v, n in zip(valores, numeros, strict=True)}
        if any(v != c for v, c in canonicos.items()):
            serie = serie.map(canonicos)
        encontrados = [n for n in numeros if n is not None]
        perfil = PerfilColumna(
            nombre,
            "numerica",
            vacios,
            len(set(canonicos.values())),
            total - numericos,
            _numero_publico(min(encontrados)),
            _numero_publico(max(encontrados)),
        )
        return serie, perfil, []

    avisos = []
    parecidos = _aviso_valores_parecidos(nombre, dict(zip(valores, cuentas, strict=True)))
    if parecidos:
        avisos.append(parecidos)
    return serie, PerfilColumna(nombre, "texto", vacios, len(valores), 0, None, None), avisos
