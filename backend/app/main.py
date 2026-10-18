"""Creación de la aplicación FastAPI."""

import asyncio
import time
from collections.abc import Callable
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from starlette.formparsers import MultiPartParser
from starlette.routing import Match, Mount
from starlette.staticfiles import StaticFiles
from starlette.types import Scope

from . import __version__
from .api import analisis, datasets
from .config import RAIZ, Configuracion, cargar_configuracion
from .errors import CapturaErroresInternos, registrar_manejadores
from .seguridad import MARGEN_CUERPO, Seguridad
from .services.dataset_store import AlmacenDatasets

FRONTEND = RAIZ / "frontend"
INTERVALO_PURGA_SEGUNDOS = 60


class _MontajeFrontend(Mount):
    """El frontend no atiende nada bajo /api: así un /api/... inexistente da el 404 JSON del
    contrato (y un método incorrecto, el 405) en lugar de buscarlo entre los archivos estáticos."""

    def matches(self, scope: Scope):
        ruta = scope["path"]
        if ruta == "/api" or ruta.startswith("/api/"):
            return Match.NONE, {}
        return super().matches(scope)


async def purgar_periodicamente(almacen: AlmacenDatasets, intervalo: float = INTERVALO_PURGA_SEGUNDOS) -> None:
    while True:
        await asyncio.sleep(intervalo)
        almacen.purgar_caducados()


@asynccontextmanager
async def _ciclo_de_vida(app: FastAPI):
    almacen: AlmacenDatasets = app.state.almacen
    tarea = asyncio.create_task(purgar_periodicamente(almacen))
    try:
        yield
    finally:
        tarea.cancel()
        with suppress(asyncio.CancelledError):
            await tarea
        almacen.vaciar()  # al apagar no queda nada en memoria


def crear_app(config: Configuracion | None = None, reloj: Callable[[], float] = time.monotonic) -> FastAPI:
    config = config or cargar_configuracion()

    # Starlette pasa a un archivo temporal en disco las partes de formulario mayores que este
    # tamaño (1 MB por defecto). Se amplía para que un archivo de hasta `max_mb` siga en memoria.
    MultiPartParser.spool_max_size = max(MultiPartParser.spool_max_size, config.max_bytes + MARGEN_CUERPO)

    app = FastAPI(
        title="DataTab",
        version=__version__,
        docs_url="/docs" if config.docs else None,
        redoc_url="/redoc" if config.docs else None,
        openapi_url="/openapi.json" if config.docs else None,
        lifespan=_ciclo_de_vida,
    )
    app.state.config = config
    app.state.almacen = AlmacenDatasets(config.ttl_segundos, config.max_datasets, reloj)

    registrar_manejadores(app)
    # El último que se añade es el más externo: así el 500 genérico también lleva las cabeceras
    app.add_middleware(CapturaErroresInternos)
    app.add_middleware(Seguridad, max_mb=config.max_mb)

    app.include_router(datasets.router, prefix="/api")
    app.include_router(analisis.router, prefix="/api")

    # Siempre después de las rutas /api
    if config.servir_frontend and FRONTEND.is_dir():
        app.router.routes.append(_MontajeFrontend("/", app=StaticFiles(directory=FRONTEND, html=True), name="frontend"))
    return app


app = crear_app()
