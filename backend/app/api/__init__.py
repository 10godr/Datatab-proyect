"""Rutas de la API y dependencias compartidas."""

from fastapi import Request

from ..config import Configuracion
from ..services.dataset_store import AlmacenDatasets


def obtener_config(request: Request) -> Configuracion:
    return request.app.state.config


def obtener_almacen(request: Request) -> AlmacenDatasets:
    return request.app.state.almacen
