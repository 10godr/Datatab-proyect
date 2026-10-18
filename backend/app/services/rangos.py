"""Rangos numéricos escritos por la persona: sintaxis, etiquetas, asignación y solapes."""

import re
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from ..errors import ErrorDataTab, recortar
from .avisos import Aviso, aviso
from .columnas import PerfilColumna, formatear_numero

MAX_RANGOS = 50
MAX_LONGITUD_RANGO = 40

ETIQUETA_FUERA = "Fuera de los rangos"
ETIQUETA_SIN_VALOR = "Sin valor numérico"

# Variantes tipográficas que se aceptan como los símbolos del contrato
_EQUIVALENCIAS = str.maketrans({"≤": "<=", "≥": ">=", "＜": "<", "＞": ">", "–": "-", "—": "-", "−": "-"})

_NUM = r"-?(?:[0-9]+(?:[.,][0-9]+)?|[.,][0-9]+)"
_COMPARACION = re.compile(rf"(<=|>=|<|>)\s*({_NUM})")
_O_MAS = re.compile(rf"({_NUM})\s*\+")
_ENTRE = re.compile(rf"({_NUM})\s*-\s*({_NUM})")

_INFINITO = float("inf")


@dataclass(frozen=True)
class Rango:
    texto: str  # tal como lo escribió la persona (sin espacios en los extremos)
    etiqueta: str
    minimo: float  # -inf si no tiene límite inferior
    incluye_minimo: bool
    maximo: float  # inf si no tiene límite superior
    incluye_maximo: bool

    @property
    def equivalencia(self) -> tuple[float, bool, float, bool]:
        """Dos rangos con la misma equivalencia significan lo mismo (`40+` y `>=40`)."""
        return (self.minimo, self.incluye_minimo, self.maximo, self.incluye_maximo)

    def contiene(self, valores: np.ndarray) -> np.ndarray:
        """Máscara de los valores dentro del rango; los NaN nunca caen dentro."""
        if self.incluye_minimo:
            dentro = valores >= self.minimo
        else:
            dentro = valores > self.minimo
        if self.incluye_maximo:
            return dentro & (valores <= self.maximo)
        return dentro & (valores < self.maximo)


def _numero(texto: str) -> float:
    return float(texto.replace(",", "."))


def _rango_no_valido(texto: str) -> ErrorDataTab:
    recortado = recortar(texto, MAX_LONGITUD_RANGO)
    return ErrorDataTab(
        "RANGO_NO_VALIDO",
        f"No se entiende el rango «{recortado}».",
        "Escribe rangos como <30, 30-39, 40+ o >=60.",
        {"rango": recortado},
    )


def parsear_rango(texto: str) -> Rango:
    texto = texto.strip()
    if len(texto) > MAX_LONGITUD_RANGO:
        raise _rango_no_valido(texto)
    normalizado = texto.translate(_EQUIVALENCIAS)

    if partes := _COMPARACION.fullmatch(normalizado):
        operador, limite = partes[1], _numero(partes[2])
        numero = formatear_numero(limite)
        if operador == "<":
            return Rango(texto, f"Menos de {numero}", -_INFINITO, False, limite, False)
        if operador == "<=":
            return Rango(texto, f"{numero} o menos", -_INFINITO, False, limite, True)
        if operador == ">":
            return Rango(texto, f"Más de {numero}", limite, False, _INFINITO, False)
        return Rango(texto, f"{numero} o más", limite, True, _INFINITO, False)

    if partes := _O_MAS.fullmatch(normalizado):
        limite = _numero(partes[1])
        return Rango(texto, f"{formatear_numero(limite)} o más", limite, True, _INFINITO, False)

    if partes := _ENTRE.fullmatch(normalizado):
        desde, hasta = _numero(partes[1]), _numero(partes[2])
        if desde > hasta:
            raise _rango_no_valido(texto)
        etiqueta = f"{formatear_numero(desde)} a {formatear_numero(hasta)}"
        return Rango(texto, etiqueta, desde, True, hasta, True)

    raise _rango_no_valido(texto)


def parsear_rangos(textos: Sequence[str] | None) -> list[Rango]:
    """Valida la lista completa. Los textos vacíos se ignoran."""
    pedidos = [t.strip() for t in textos or [] if t.strip()]
    if len(pedidos) > MAX_RANGOS:
        raise ErrorDataTab(
            "DEMASIADOS_RANGOS",
            f"Se pidieron {len(pedidos)} rangos. El máximo es {MAX_RANGOS}.",
            detalle={"max_rangos": MAX_RANGOS, "recibidos": len(pedidos)},
        )
    vistos: dict[tuple, Rango] = {}
    rangos = []
    for texto in pedidos:
        rango = parsear_rango(texto)
        anterior = vistos.get(rango.equivalencia)
        if anterior is not None:
            raise ErrorDataTab(
                "RANGO_REPETIDO",
                f"El rango «{rango.texto}» está repetido (es igual que «{anterior.texto}»).",
                "Quita uno de los dos.",
                {"rango": rango.texto, "igual_a": anterior.texto},
            )
        vistos[rango.equivalencia] = rango
        rangos.append(rango)
    return rangos


def rangos_de_columna(perfil: PerfilColumna, textos: Sequence[str] | None) -> list[Rango]:
    """Rangos pedidos para una columna: solo se admiten en columnas numéricas."""
    if perfil.tipo != "numerica" and any(t.strip() for t in textos or []):
        raise ErrorDataTab(
            "RANGOS_EN_COLUMNA_NO_NUMERICA",
            f"Los rangos solo sirven en columnas numéricas y «{perfil.nombre}» no lo es.",
            "Quita los rangos para contar cada valor por separado.",
            {"columna": perfil.nombre},
        )
    return parsear_rangos(textos)


def se_solapan(a: Rango, b: Rango) -> bool:
    """True si algún valor puede caer en los dos rangos (según sus límites, no sus datos)."""
    if a.minimo == b.minimo:
        inferior, incluye_inferior = a.minimo, a.incluye_minimo and b.incluye_minimo
    elif a.minimo > b.minimo:
        inferior, incluye_inferior = a.minimo, a.incluye_minimo
    else:
        inferior, incluye_inferior = b.minimo, b.incluye_minimo
    if a.maximo == b.maximo:
        superior, incluye_superior = a.maximo, a.incluye_maximo and b.incluye_maximo
    elif a.maximo < b.maximo:
        superior, incluye_superior = a.maximo, a.incluye_maximo
    else:
        superior, incluye_superior = b.maximo, b.incluye_maximo
    return inferior < superior or (inferior == superior and incluye_inferior and incluye_superior)


def pares_solapados(rangos: Sequence[Rango]) -> list[tuple[int, int]]:
    return [
        (i, j)
        for i in range(len(rangos))
        for j in range(i + 1, len(rangos))
        if se_solapan(rangos[i], rangos[j])
    ]


@dataclass(frozen=True)
class Asignacion:
    """Dónde cae cada registro. Todas las listas son máscaras del mismo largo que los valores."""

    por_rango: list[np.ndarray]
    fuera: np.ndarray  # número que no entra en ningún rango
    sin_valor: np.ndarray  # no es un número


def asignar(valores: np.ndarray, rangos: Sequence[Rango]) -> Asignacion:
    """`valores` son los registros no vacíos como float; NaN = no es un número."""
    por_rango = [rango.contiene(valores) for rango in rangos]
    sin_valor = np.isnan(valores)
    dentro = np.logical_or.reduce(por_rango) if por_rango else np.zeros(len(valores), dtype=bool)
    return Asignacion(por_rango, ~sin_valor & ~dentro, sin_valor)


def aviso_valores_no_numericos(columna: str, cantidad: int) -> Aviso:
    plural = "valor que no es un número" if cantidad == 1 else "valores que no son números"
    return aviso(
        "VALORES_NO_NUMERICOS",
        "info",
        f"La columna «{columna}» tiene {cantidad} {plural}; aparecen como «{ETIQUETA_SIN_VALOR}».",
    )
