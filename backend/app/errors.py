"""Errores del contrato (docs/api.md) y su traducción a respuestas JSON.

Los servicios lanzan `ErrorDataTab` sin saber nada de HTTP; aquí se decide el estado.
Ningún mensaje ni registro incluye contenido de celdas, rutas del servidor ni el texto
de excepciones internas.
"""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import http_exception_handler
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from .formato import decimal_es, megabytes

registro = logging.getLogger("datatab")

# Código estable -> estado HTTP (tabla "Errores" del contrato)
ESTADO_HTTP: dict[str, int] = {
    "PETICION_NO_VALIDA": 400,
    "ARCHIVO_NO_ENCONTRADO": 404,
    "RUTA_NO_ENCONTRADA": 404,
    "METODO_NO_PERMITIDO": 405,
    "ARCHIVO_DEMASIADO_GRANDE": 413,
    "FORMATO_NO_SOPORTADO": 415,
    "CONTENIDO_NO_COINCIDE": 415,
    "ARCHIVO_ILEGIBLE": 422,
    "ARCHIVO_VACIO": 422,
    "TABLA_DEMASIADO_GRANDE": 422,
    "COLUMNA_NO_ENCONTRADA": 422,
    "COLUMNAS_IGUALES": 422,
    "RANGO_NO_VALIDO": 422,
    "RANGO_REPETIDO": 422,
    "DEMASIADOS_RANGOS": 422,
    "RANGOS_EN_COLUMNA_NO_NUMERICA": 422,
    "RANGOS_SOLAPADOS_EN_CRUCE": 422,
    "SIN_DATOS": 422,
    "DEMASIADAS_CATEGORIAS": 422,
    "ERROR_INTERNO": 500,
}


class ErrorDataTab(Exception):
    """Error previsto, con la forma del contrato. `mensaje` va dirigido a la persona usuaria."""

    def __init__(
        self,
        codigo: str,
        mensaje: str,
        sugerencia: str | None = None,
        detalle: dict[str, Any] | None = None,
    ):
        if codigo not in ESTADO_HTTP:
            raise ValueError("Código de error desconocido.")
        super().__init__(codigo)
        self.codigo = codigo
        self.mensaje = mensaje
        self.sugerencia = sugerencia
        self.detalle = detalle

    @property
    def estado(self) -> int:
        return ESTADO_HTTP[self.codigo]


def recortar(texto: str, maximo: int = 40) -> str:
    """Acorta un texto escrito por la persona antes de repetirlo en un mensaje."""
    return texto if len(texto) <= maximo else texto[:maximo] + "…"


def archivo_demasiado_grande(max_mb: int, tamano_bytes: int | None = None) -> ErrorDataTab:
    sugerencia = "Elimina hojas o columnas que no necesites y vuelve a intentarlo."
    if tamano_bytes is None:
        return ErrorDataTab(
            "ARCHIVO_DEMASIADO_GRANDE",
            f"El archivo supera el máximo de {max_mb} MB.",
            sugerencia,
            {"max_mb": max_mb},
        )
    tamano_mb = megabytes(tamano_bytes)
    return ErrorDataTab(
        "ARCHIVO_DEMASIADO_GRANDE",
        f"El archivo pesa {decimal_es(tamano_mb)} MB. El máximo es {max_mb} MB.",
        sugerencia,
        {"tamano_mb": tamano_mb, "max_mb": max_mb},
    )


def respuesta_error(error: ErrorDataTab) -> JSONResponse:
    cuerpo: dict[str, Any] = {"codigo": error.codigo, "mensaje": error.mensaje}
    if error.sugerencia is not None:
        cuerpo["sugerencia"] = error.sugerencia
    if error.detalle is not None:
        cuerpo["detalle"] = error.detalle
    return JSONResponse({"error": cuerpo}, status_code=error.estado)


def _es_api(ruta: str) -> bool:
    return ruta == "/api" or ruta.startswith("/api/")


async def _manejar_error_datatab(_: Request, error: ErrorDataTab) -> JSONResponse:
    return respuesta_error(error)


async def _manejar_validacion(_: Request, exc: RequestValidationError) -> JSONResponse:
    errores = exc.errors()
    campos: list[str] = []
    for error in errores:
        nombre = ".".join(parte for parte in error["loc"][1:] if isinstance(parte, str))
        if nombre and nombre not in campos:
            campos.append(recortar(nombre, 60))
    if any(error["loc"][-1:] == ("archivo",) for error in errores):
        mensaje = "No se recibió ningún archivo."
        sugerencia = "Elige un archivo Excel o CSV y vuelve a intentarlo."
    else:
        mensaje = "La petición no tiene el formato esperado."
        sugerencia = "Revisa que estén todos los datos y vuelve a intentarlo."
    return respuesta_error(
        ErrorDataTab("PETICION_NO_VALIDA", mensaje, sugerencia, {"campos": campos[:10]} if campos else None)
    )


async def _manejar_http(peticion: Request, exc: StarletteHTTPException):
    if not _es_api(peticion.url.path):
        return await http_exception_handler(peticion, exc)
    if exc.status_code == 404:
        error = ErrorDataTab("RUTA_NO_ENCONTRADA", "Esa dirección de la API no existe.")
    elif exc.status_code == 405:
        error = ErrorDataTab("METODO_NO_PERMITIDO", "Ese método no está permitido en esta dirección.")
    elif exc.status_code in (400, 422):
        error = ErrorDataTab("PETICION_NO_VALIDA", "La petición no tiene el formato esperado.")
    else:
        error = _error_interno()
    respuesta = respuesta_error(error)
    # Conserva cabeceras como Allow en los 405
    for nombre, valor in (exc.headers or {}).items():
        respuesta.headers[nombre] = valor
    return respuesta


def _error_interno() -> ErrorDataTab:
    return ErrorDataTab(
        "ERROR_INTERNO",
        "Ocurrió un error inesperado.",
        "Vuelve a intentarlo. Si sigue pasando, reinicia DataTab.",
    )


def registrar_manejadores(app: FastAPI) -> None:
    app.add_exception_handler(ErrorDataTab, _manejar_error_datatab)
    app.add_exception_handler(RequestValidationError, _manejar_validacion)
    app.add_exception_handler(StarletteHTTPException, _manejar_http)


class CapturaErroresInternos:
    """Middleware ASGI: convierte cualquier excepción no prevista en un 500 genérico.

    No se usa un manejador de `Exception` de Starlette porque vuelve a lanzar la excepción
    y el servidor imprimiría su traza completa, con el texto de la excepción (que podría
    contener datos del archivo). Aquí solo se registran el tipo de excepción y la ruta.
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        respuesta_iniciada = False

        async def send_vigilado(mensaje):
            nonlocal respuesta_iniciada
            if mensaje["type"] == "http.response.start":
                respuesta_iniciada = True
            await send(mensaje)

        try:
            await self.app(scope, receive, send_vigilado)
        except Exception as exc:
            registro.error(
                "Error interno (%s) en %s %r", type(exc).__name__, scope.get("method"), scope.get("path")
            )
            if not respuesta_iniciada:
                await respuesta_error(_error_interno())(scope, receive, send_vigilado)
