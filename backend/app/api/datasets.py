"""Configuración, salud y ciclo de vida de los archivos cargados."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile
from starlette.concurrency import run_in_threadpool

from ..config import Configuracion
from ..errors import ErrorDataTab, archivo_demasiado_grande
from ..schemas import ConfiguracionRespuesta, DatasetRespuesta, FilasRespuesta, SaludRespuesta
from ..services.avisos import Aviso
from ..services.dataset_store import AlmacenDatasets, Dataset
from ..services.file_reader import FORMATOS, leer_archivo
from . import obtener_almacen, obtener_config

router = APIRouter(tags=["archivos"])


def _respuesta_dataset(dataset: Dataset, almacen: AlmacenDatasets, avisos: list[Aviso]) -> dict[str, Any]:
    return {
        "dataset_id": dataset.id,
        "nombre": dataset.nombre,
        "formato": dataset.formato,
        "filas": len(dataset.tabla),
        "columnas": [perfil.como_dict() for perfil in dataset.perfiles],
        "avisos": avisos,
        "expira_en_segundos": int(almacen.ttl_segundos),
    }


def _registrar(nombre: str | None, contenido: bytes, config: Configuracion, almacen: AlmacenDatasets) -> dict[str, Any]:
    if len(contenido) > config.max_bytes:
        raise archivo_demasiado_grande(config.max_mb, len(contenido))
    leida = leer_archivo(nombre, contenido, config)
    dataset = almacen.guardar(leida.nombre, leida.formato, leida.tabla, leida.perfiles)
    return _respuesta_dataset(dataset, almacen, leida.avisos)


@router.get("/salud", response_model=SaludRespuesta, summary="Comprobar que el servidor está activo")
def salud() -> dict[str, str]:
    return {"estado": "ok"}


@router.get("/configuracion", response_model=ConfiguracionRespuesta, summary="Límites vigentes")
def configuracion(config: Configuracion = Depends(obtener_config)) -> dict[str, Any]:
    return {
        "max_mb": config.max_mb,
        "max_bytes": config.max_bytes,
        "formatos": list(FORMATOS),
        "minutos_inactividad": config.ttl_min,
        "max_filas": config.max_filas,
        "max_columnas": config.max_columnas,
        "max_celdas": config.max_celdas,
        "ejemplo_disponible": config.ejemplo.is_file(),
    }


@router.post("/datasets", status_code=201, response_model=DatasetRespuesta, summary="Subir un archivo")
async def subir_dataset(
    archivo: Annotated[UploadFile, File(description="Archivo .xlsx, .xls o .csv")],
    config: Configuracion = Depends(obtener_config),
    almacen: AlmacenDatasets = Depends(obtener_almacen),
) -> dict[str, Any]:
    if archivo.size is not None and archivo.size > config.max_bytes:
        raise archivo_demasiado_grande(config.max_mb, archivo.size)
    contenido = await archivo.read()
    return await run_in_threadpool(_registrar, archivo.filename, contenido, config, almacen)


@router.post("/datasets/ejemplo", status_code=201, response_model=DatasetRespuesta, summary="Cargar el archivo de ejemplo")
def cargar_ejemplo(
    config: Configuracion = Depends(obtener_config),
    almacen: AlmacenDatasets = Depends(obtener_almacen),
) -> dict[str, Any]:
    if not config.ejemplo.is_file():
        raise ErrorDataTab("ARCHIVO_NO_ENCONTRADO", "No hay un archivo de ejemplo disponible.")
    return _registrar(config.ejemplo.name, config.ejemplo.read_bytes(), config, almacen)


@router.get("/datasets/{dataset_id}", response_model=DatasetRespuesta, summary="Recuperar un archivo cargado")
def obtener_dataset(dataset_id: str, almacen: AlmacenDatasets = Depends(obtener_almacen)) -> dict[str, Any]:
    return _respuesta_dataset(almacen.obtener(dataset_id), almacen, [])


@router.get("/datasets/{dataset_id}/filas", response_model=FilasRespuesta, summary="Filas para la vista de datos")
def filas(
    dataset_id: str,
    desde: Annotated[int, Query(ge=0)] = 0,
    cantidad: Annotated[int, Query(ge=1, le=200)] = 50,
    almacen: AlmacenDatasets = Depends(obtener_almacen),
) -> dict[str, Any]:
    tabla = almacen.obtener(dataset_id).tabla
    bloque = tabla.iloc[desde : desde + cantidad]
    return {
        "total": len(tabla),
        "desde": desde,
        "cantidad": len(bloque),
        "columnas": tabla.columns.tolist(),
        "filas": bloque.fillna("").values.tolist(),
    }


@router.delete("/datasets/{dataset_id}", status_code=204, summary="Borrar un archivo de la memoria")
def borrar_dataset(dataset_id: str, almacen: AlmacenDatasets = Depends(obtener_almacen)) -> Response:
    almacen.eliminar(dataset_id)
    return Response(status_code=204)
