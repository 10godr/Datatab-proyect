"""Modelos Pydantic de peticiones y respuestas. Reflejan exactamente docs/api.md."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

TipoColumna = Literal["numerica", "texto", "fecha"]
TipoFila = Literal["valor", "rango", "fuera_de_rango", "sin_valor_numerico"]


class Respuesta(BaseModel):
    """Base de las respuestas: un campo de más o de menos es un error, no se oculta."""

    model_config = ConfigDict(extra="forbid")


# --- Peticiones -------------------------------------------------------------------


class FrecuenciasPeticion(BaseModel):
    columna: str
    rangos: list[str] | None = None


class EjePeticion(BaseModel):
    columna: str
    rangos: list[str] | None = None


class TablaCruzadaPeticion(BaseModel):
    fila: EjePeticion
    columna: EjePeticion


# --- Respuestas: general --------------------------------------------------------------


class SaludRespuesta(Respuesta):
    estado: Literal["ok"]


class ConfiguracionRespuesta(Respuesta):
    max_mb: int
    max_bytes: int
    formatos: list[str]
    minutos_inactividad: int
    max_filas: int
    max_columnas: int
    max_celdas: int


class AvisoRespuesta(Respuesta):
    codigo: str
    nivel: Literal["info", "atencion"]
    mensaje: str


# --- Respuestas: archivos -----------------------------------------------------------------


class ColumnaRespuesta(Respuesta):
    nombre: str
    tipo: TipoColumna
    vacios: int
    distintos: int
    no_numericos: int
    minimo: int | float | None
    maximo: int | float | None


class DatasetRespuesta(Respuesta):
    dataset_id: str
    nombre: str
    formato: Literal["xlsx", "xls", "csv"]
    filas: int
    columnas: list[ColumnaRespuesta]
    avisos: list[AvisoRespuesta]
    expira_en_segundos: int


class FilasRespuesta(Respuesta):
    total: int
    desde: int
    cantidad: int
    columnas: list[str]
    filas: list[list[str]]


# --- Respuestas: análisis ----------------------------------------------------------------------


class FilaFrecuencia(Respuesta):
    tipo: TipoFila
    etiqueta: str
    rango: str | None
    frecuencia: int
    porcentaje: float


class FrecuenciasRespuesta(Respuesta):
    columna: str
    tipo: TipoColumna
    agrupado: bool
    n: int
    vacios_excluidos: int
    filas: list[FilaFrecuencia]
    solapados: int
    avisos: list[AvisoRespuesta]


class EjeRespuesta(Respuesta):
    columna: str
    agrupado: bool


class CategoriaCruce(Respuesta):
    tipo: TipoFila
    etiqueta: str
    rango: str | None


class CeldaCruce(Respuesta):
    frecuencia: int
    porcentaje: float


class FilaCruce(CategoriaCruce):
    total: int
    celdas: list[CeldaCruce]


class TablaCruzadaRespuesta(Respuesta):
    fila: EjeRespuesta
    columna: EjeRespuesta
    n: int
    vacios_excluidos: int
    columnas: list[CategoriaCruce]
    filas: list[FilaCruce]
    totales_columna: list[CeldaCruce]
    avisos: list[AvisoRespuesta]
