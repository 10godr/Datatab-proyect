import random
from pathlib import Path

import openpyxl
import pytest
from fastapi.testclient import TestClient

from app.config import Configuracion
from app.main import crear_app

DATOS_DE_PRUEBA = Path(__file__).resolve().parent / "fixtures" / "datos"


class RelojFalso:
    """Reloj controlable para probar la caducidad sin esperar."""

    def __init__(self, inicio: float = 1000.0):
        self.ahora = inicio

    def __call__(self) -> float:
        return self.ahora

    def avanzar(self, segundos: float) -> None:
        self.ahora += segundos


@pytest.fixture
def config() -> Configuracion:
    return Configuracion()


@pytest.fixture
def reloj() -> RelojFalso:
    return RelojFalso()


@pytest.fixture
def app(config, reloj):
    return crear_app(config, reloj)


@pytest.fixture
def cliente(app) -> TestClient:
    # Con False, un fallo interno llega como respuesta 500 y no como excepción del cliente
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def pacientes_bytes() -> bytes:
    return (DATOS_DE_PRUEBA / "pacientes-ficticios.xlsx").read_bytes()


@pytest.fixture(scope="session")
def csv_grande(tmp_path_factory) -> Path:
    """CSV ficticio de unos 4,9 MB."""
    azar = random.Random(7)
    ruta = tmp_path_factory.mktemp("grandes") / "grande.csv"
    objetivo = int(4.9 * 1024 * 1024)
    with ruta.open("w", encoding="utf-8", newline="") as archivo:
        archivo.write("Id,Sexo,Edad,Peso,Talla,Servicio,Diagnostico,Dato A,Dato B\n")
        numero = 0
        while archivo.tell() < objetivo:
            numero += 1
            archivo.write(
                f"{numero},{azar.choice(['F', 'M'])},{azar.randrange(1, 95)},{azar.uniform(40, 120):.2f},{azar.uniform(1.3, 2.0):.3f},"
                f"{azar.choice(['Urgencias', 'Consulta', 'Cirugía'])},D{azar.randrange(1, 40)},{azar.random():.6f},{azar.random():.6f}\n"
            )
    return ruta


@pytest.fixture(scope="session")
def xlsx_grande(tmp_path_factory) -> Path:
    """xlsx ficticio de unos 4,9 MB (datos aleatorios, que comprimen poco)."""
    azar = random.Random(11)
    ruta = tmp_path_factory.mktemp("grandes") / "grande.xlsx"
    libro = openpyxl.Workbook(write_only=True)
    hoja = libro.create_sheet("Datos")
    hoja.append(["Id", "Sexo", "Edad", "Peso", "Talla", "Servicio", "Codigo", "Dato A", "Dato B"])
    for numero in range(1, 72501):
        hoja.append(
            [
                numero,
                azar.choice(["Femenino", "Masculino"]),
                azar.randrange(1, 95),
                round(azar.uniform(40, 120), 2),
                round(azar.uniform(1.3, 2.0), 3),
                azar.choice(["Urgencias", "Consulta externa", "Cirugía", "Hospitalización"]),
                f"C{azar.randrange(10**6):06d}",
                azar.random(),
                azar.random(),
            ]
        )
    libro.save(ruta)
    return ruta
