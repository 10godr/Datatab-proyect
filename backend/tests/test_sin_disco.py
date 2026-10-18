"""Ningún byte del archivo del usuario toca el disco: ni archivos temporales ni copias.

Se comprueba por tres vías independientes:
  1. el análisis multipart de Starlette no pasa a un archivo temporal (se vigila `rollover`);
  2. un gancho de auditoría de Python (`sys.addaudithook`) registra cualquier apertura de archivos
     para escritura, `mkstemp` o `mkdtemp` durante la subida y el análisis;
  3. el directorio temporal del sistema, apuntado a una carpeta vacía, sigue vacío.
Un control negativo demuestra que el vigilante detecta el problema cuando el límite de memoria
de Starlette es el de fábrica (1 MB).
"""

import os
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

import pytest
from starlette.formparsers import MultiPartParser

from app.config import MB
from ayudas import crear_csv, crear_xls, crear_xlsx

_EVENTOS: list[tuple] | None = None  # el gancho de auditoría no se puede quitar: solo anota cuando está activo
_MODOS_ESCRITURA = ("w", "a", "x", "+")
_BANDERAS_ESCRITURA = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_TRUNC


def _es_ruido(ruta: object) -> bool:
    texto = os.fsdecode(ruta) if isinstance(ruta, (str, bytes, os.PathLike)) else ""
    return (
        not texto  # descriptor de archivo ya abierto
        or "__pycache__" in texto
        or texto.endswith((".pyc", ".pyo"))
        or texto.startswith(("/dev/", "/proc/", "/sys/"))
    )


def _gancho(evento: str, argumentos: tuple) -> None:
    if _EVENTOS is None:
        return
    if evento in ("tempfile.mkstemp", "tempfile.mkdtemp"):
        _EVENTOS.append((evento, argumentos))
    elif evento == "open":
        ruta, modo, banderas = argumentos
        if _es_ruido(ruta):
            return
        escribe = (isinstance(modo, str) and any(letra in modo for letra in _MODOS_ESCRITURA)) or (
            isinstance(banderas, int) and banderas & _BANDERAS_ESCRITURA
        )
        if escribe:
            _EVENTOS.append((evento, (os.fsdecode(ruta), modo, banderas)))


sys.addaudithook(_gancho)


@contextmanager
def vigilar_disco(monkeypatch, tmp_path: Path):
    """Anota cada intento de escribir en disco y desvía el directorio temporal a una carpeta vacía."""
    global _EVENTOS
    carpeta_temporal = tmp_path / "tmp-vacia"
    carpeta_temporal.mkdir()
    desbordes: list[int] = []
    original = tempfile.SpooledTemporaryFile.rollover

    def rollover_vigilado(self):
        desbordes.append(1)
        return original(self)

    monkeypatch.setattr(tempfile.SpooledTemporaryFile, "rollover", rollover_vigilado)
    monkeypatch.setattr(tempfile, "tempdir", str(carpeta_temporal))
    eventos: list[tuple] = []
    _EVENTOS = eventos
    try:
        yield desbordes, eventos, carpeta_temporal
    finally:
        _EVENTOS = None


def calentar(cliente) -> None:
    """Primera petición de cada tipo: las importaciones diferidas y las cachés no cuentan."""
    for nombre, contenido in (("a.csv", crear_csv([["a"], [1]])), ("a.xlsx", crear_xlsx([["a"], [1]])), ("a.xls", crear_xls([["a"], [1]]))):
        assert cliente.post("/api/datasets", files={"archivo": (nombre, contenido, "application/octet-stream")}).status_code == 201
    assert cliente.post("/api/datasets/ejemplo").status_code == 201


def comprobar_sin_disco(desbordes, eventos, carpeta_temporal):
    assert desbordes == [], "Starlette pasó parte del archivo a un temporal en disco"
    assert eventos == [], f"Intentos de escribir en disco: {eventos}"
    assert list(carpeta_temporal.iterdir()) == []


def test_el_limite_de_memoria_del_analisis_multipart_cubre_el_maximo_de_la_configuracion(app, config):
    assert MultiPartParser.spool_max_size >= config.max_bytes


@pytest.mark.lento
@pytest.mark.parametrize("formato", ["csv", "xlsx"])
def test_subir_un_archivo_de_casi_5_mb_y_analizarlo_no_escribe_en_disco(formato, cliente, csv_grande, xlsx_grande, monkeypatch, tmp_path):
    ruta = csv_grande if formato == "csv" else xlsx_grande
    contenido = ruta.read_bytes()
    assert 4.5 * MB < len(contenido) <= 5 * MB
    calentar(cliente)

    with vigilar_disco(monkeypatch, tmp_path) as (desbordes, eventos, carpeta_temporal):
        respuesta = cliente.post("/api/datasets", files={"archivo": (ruta.name, contenido, "application/octet-stream")})
        assert respuesta.status_code == 201, respuesta.text
        dataset_id = respuesta.json()["dataset_id"]
        assert cliente.get(f"/api/datasets/{dataset_id}/filas?desde=10&cantidad=5").status_code == 200
        assert cliente.post(f"/api/datasets/{dataset_id}/frecuencias", json={"columna": "Sexo"}).status_code == 200
        assert cliente.post(
            f"/api/datasets/{dataset_id}/frecuencias", json={"columna": "Edad", "rangos": ["<18", "18-39", "40-64", "65+"]}
        ).status_code == 200
        cruce = cliente.post(
            f"/api/datasets/{dataset_id}/tabla-cruzada",
            json={"fila": {"columna": "Sexo"}, "columna": {"columna": "Servicio"}},
        )
        assert cruce.status_code == 200
        assert cliente.delete(f"/api/datasets/{dataset_id}").status_code == 204
        assert cliente.post("/api/datasets/ejemplo").status_code == 201

    comprobar_sin_disco(desbordes, eventos, carpeta_temporal)


def test_un_xls_antiguo_y_un_error_de_lectura_tampoco_escriben_en_disco(cliente, monkeypatch, tmp_path):
    calentar(cliente)
    with vigilar_disco(monkeypatch, tmp_path) as (desbordes, eventos, carpeta_temporal):
        assert cliente.post("/api/datasets", files={"archivo": ("v.xls", crear_xls([["a", "b"], [1, 2]]), "application/vnd.ms-excel")}).status_code == 201
        malo = cliente.post("/api/datasets", files={"archivo": ("malo.xlsx", b"PK\x03\x04" + b"\x00" * 200, "application/octet-stream")})
        assert malo.status_code == 422
        pasado = cliente.post("/api/datasets", files={"archivo": ("g.csv", b"a\n" + b"1\n" * (3 * MB), "text/csv")})
        assert pasado.status_code == 413
    comprobar_sin_disco(desbordes, eventos, carpeta_temporal)


@pytest.mark.lento
def test_control_negativo_con_el_limite_de_fabrica_de_starlette_si_se_usa_disco(app, cliente, csv_grande, monkeypatch, tmp_path):
    """Demuestra que el vigilante funciona: con el valor de fábrica (1 MB) el mismo archivo SÍ pasa a disco."""
    contenido = csv_grande.read_bytes()
    calentar(cliente)
    monkeypatch.setattr(MultiPartParser, "spool_max_size", 1024 * 1024)
    with vigilar_disco(monkeypatch, tmp_path) as (desbordes, eventos, _):
        assert cliente.post("/api/datasets", files={"archivo": ("g.csv", contenido, "text/csv")}).status_code == 201
    assert desbordes, "el vigilante no detectó el desborde a disco con el límite de fábrica"
    assert eventos, "el gancho de auditoría no detectó la escritura en disco con el límite de fábrica"
