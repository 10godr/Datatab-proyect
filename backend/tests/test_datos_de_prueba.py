"""Los archivos de datos-de-prueba/ (los que usa la persona para probar a mano) se pueden cargar."""

from pathlib import Path

import pytest

CARPETA = Path(__file__).resolve().parents[2] / "datos-de-prueba"


def test_hay_como_maximo_tres_archivos_de_prueba():
    datos = [p for p in CARPETA.iterdir() if p.suffix in {".xlsx", ".xls", ".csv"}]
    assert sorted(p.name for p in datos) == ["encuesta-escolar.csv", "pacientes-ficticios.xlsx", "ventas-tienda.xls"]


@pytest.mark.parametrize(("nombre", "formato", "minimo_filas"), [
    ("pacientes-ficticios.xlsx", "xlsx", 151), ("encuesta-escolar.csv", "csv", 50), ("ventas-tienda.xls", "xls", 50),
])
def test_se_cargan_los_archivos_de_prueba(cliente, nombre, formato, minimo_filas):
    respuesta = cliente.post("/api/datasets", files={"archivo": (nombre, (CARPETA / nombre).read_bytes())})
    assert respuesta.status_code == 201, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["formato"] == formato and cuerpo["filas"] >= minimo_filas
