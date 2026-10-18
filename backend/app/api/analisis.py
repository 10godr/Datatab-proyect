"""Frecuencias y tabla cruzada."""

from typing import Any

from fastapi import APIRouter, Depends

from ..config import Configuracion
from ..errors import ErrorDataTab
from ..schemas import (
    FrecuenciasPeticion,
    FrecuenciasRespuesta,
    TablaCruzadaPeticion,
    TablaCruzadaRespuesta,
)
from ..services.cruce import calcular_tabla_cruzada
from ..services.dataset_store import AlmacenDatasets
from ..services.frecuencias import calcular_frecuencias
from . import obtener_almacen, obtener_config

router = APIRouter(tags=["análisis"])


@router.post(
    "/datasets/{dataset_id}/frecuencias",
    response_model=FrecuenciasRespuesta,
    summary="Tabla de frecuencias de una columna",
)
def frecuencias(
    dataset_id: str,
    peticion: FrecuenciasPeticion,
    almacen: AlmacenDatasets = Depends(obtener_almacen),
    config: Configuracion = Depends(obtener_config),
) -> dict[str, Any]:
    serie, perfil = almacen.obtener(dataset_id).columna(peticion.columna)
    return calcular_frecuencias(serie, perfil, peticion.rangos, config.max_valores_distintos)


@router.post(
    "/datasets/{dataset_id}/tabla-cruzada",
    response_model=TablaCruzadaRespuesta,
    summary="Tabla cruzada de dos columnas",
)
def tabla_cruzada(
    dataset_id: str,
    peticion: TablaCruzadaPeticion,
    almacen: AlmacenDatasets = Depends(obtener_almacen),
) -> dict[str, Any]:
    dataset = almacen.obtener(dataset_id)
    serie_fila, perfil_fila = dataset.columna(peticion.fila.columna)
    serie_columna, perfil_columna = dataset.columna(peticion.columna.columna)
    if perfil_fila.nombre == perfil_columna.nombre:
        raise ErrorDataTab(
            "COLUMNAS_IGUALES",
            "Para cruzar elige dos columnas distintas.",
            detalle={"columna": perfil_fila.nombre},
        )
    return calcular_tabla_cruzada(
        serie_fila, perfil_fila, peticion.fila.rangos, serie_columna, perfil_columna, peticion.columna.rangos
    )
