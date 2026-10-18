"""Configuración por variables de entorno DATATAB_*."""

import re
from pathlib import Path

import pytest

from app.config import MB, RAIZ, Configuracion, cargar_configuracion
from app.main import crear_app
from fastapi.testclient import TestClient


def test_sin_variables_se_usan_los_valores_del_contrato():
    config = cargar_configuracion({})
    assert config == Configuracion()
    assert (config.max_mb, config.max_bytes, config.ttl_min, config.ttl_segundos) == (5, 5 * MB, 30, 1800)
    assert (config.host, config.port) == ("127.0.0.1", 8000)
    assert (config.max_filas, config.max_columnas, config.max_celdas) == (100_000, 200, 2_000_000)
    assert config.max_valores_distintos == 1000
    assert config.servir_frontend is True and config.docs is True
    assert config.ejemplo == RAIZ / "datos-de-prueba" / "pacientes-ficticios.xlsx"


def test_el_archivo_de_ejemplo_por_defecto_existe():
    assert Configuracion().ejemplo.is_file()


def test_las_variables_sustituyen_a_los_valores_por_defecto():
    config = cargar_configuracion(
        {
            "DATATAB_MAX_MB": "8",
            "DATATAB_TTL_MIN": "10",
            "DATATAB_HOST": "0.0.0.0",
            "DATATAB_PORT": "8765",
            "DATATAB_MAX_FILAS": "500",
            "DATATAB_MAX_COLUMNAS": "20",
            "DATATAB_MAX_CELDAS": "9000",
            "DATATAB_MAX_DESCOMPRIMIDO_MB": "50",
            "DATATAB_MAX_VALORES_DISTINTOS": "250",
            "DATATAB_MAX_DATASETS": "3",
            "DATATAB_SERVIR_FRONTEND": "0",
            "DATATAB_DOCS": "no",
        }
    )
    assert (config.max_mb, config.max_bytes, config.ttl_min, config.ttl_segundos) == (8, 8 * MB, 10, 600)
    assert (config.host, config.port) == ("0.0.0.0", 8765)
    assert (config.max_filas, config.max_columnas, config.max_celdas) == (500, 20, 9000)
    assert (config.max_descomprimido_mb, config.max_descomprimido_bytes) == (50, 50 * MB)
    assert config.max_valores_distintos == 250
    assert config.max_datasets == 3
    assert config.servir_frontend is False and config.docs is False


def test_los_espacios_y_los_valores_vacios_se_toleran():
    config = cargar_configuracion({"DATATAB_MAX_MB": " 7 ", "DATATAB_PORT": "", "DATATAB_HOST": "  ", "DATATAB_DOCS": ""})
    assert config.max_mb == 7 and config.port == 8000 and config.host == "127.0.0.1" and config.docs is True


@pytest.mark.parametrize("valor", ["0", "-1", "cinco", "5.5", "1e3", "5 MB"])
def test_un_entero_no_valido_se_rechaza_con_un_mensaje_claro(valor):
    with pytest.raises(ValueError, match="DATATAB_MAX_MB"):
        cargar_configuracion({"DATATAB_MAX_MB": valor})


@pytest.mark.parametrize("valor", ["0", "-5", "muchos"])
def test_el_maximo_de_valores_distintos_debe_ser_un_entero_positivo(valor):
    with pytest.raises(ValueError, match="DATATAB_MAX_VALORES_DISTINTOS"):
        cargar_configuracion({"DATATAB_MAX_VALORES_DISTINTOS": valor})


@pytest.mark.parametrize("valor", ["2", "quizá", "verdadero"])
def test_un_booleano_no_valido_se_rechaza(valor):
    with pytest.raises(ValueError, match="DATATAB_DOCS"):
        cargar_configuracion({"DATATAB_DOCS": valor})


@pytest.mark.parametrize("valor", ["1", "true", "TRUE", "sí", "yes", "on"])
def test_valores_verdaderos(valor):
    assert cargar_configuracion({"DATATAB_DOCS": valor}).docs is True


@pytest.mark.parametrize("valor", ["0", "false", "No", "off"])
def test_valores_falsos(valor):
    assert cargar_configuracion({"DATATAB_SERVIR_FRONTEND": valor}).servir_frontend is False


def test_el_archivo_de_ejemplo_relativo_se_cuenta_desde_la_raiz_del_repositorio(tmp_path):
    assert cargar_configuracion({"DATATAB_EJEMPLO": "backend/tests/fixtures/datos/ficticio-antiguo.xls"}).ejemplo == RAIZ / "backend" / "tests" / "fixtures" / "datos" / "ficticio-antiguo.xls"
    absoluta = tmp_path / "mio.xlsx"
    assert cargar_configuracion({"DATATAB_EJEMPLO": str(absoluta)}).ejemplo == absoluta


def test_el_archivo_de_ejemplo_configurado_es_el_que_carga_el_endpoint(tmp_path):
    ejemplo = Path(__file__).resolve().parents[2] / "backend" / "tests" / "fixtures" / "datos" / "ficticio-punto-y-coma.csv"
    config = cargar_configuracion({"DATATAB_EJEMPLO": str(ejemplo)})
    cliente = TestClient(crear_app(config), raise_server_exceptions=False)
    respuesta = cliente.post("/api/datasets/ejemplo")
    assert respuesta.status_code == 201 and respuesta.json()["nombre"] == "ficticio-punto-y-coma.csv"


def test_sin_archivo_de_ejemplo_el_endpoint_responde_404_y_la_configuracion_lo_indica(tmp_path):
    config = cargar_configuracion({"DATATAB_EJEMPLO": str(tmp_path / "no-existe.xlsx")})
    cliente = TestClient(crear_app(config), raise_server_exceptions=False)
    assert cliente.get("/api/configuracion").json()["ejemplo_disponible"] is False
    respuesta = cliente.post("/api/datasets/ejemplo")
    assert respuesta.status_code == 404 and respuesta.json()["error"]["codigo"] == "ARCHIVO_NO_ENCONTRADO"
    assert str(tmp_path) not in respuesta.text


def test_la_configuracion_es_inmutable():
    with pytest.raises(AttributeError):
        Configuracion().max_mb = 10  # type: ignore[misc]


def test_env_example_documenta_exactamente_las_variables_que_lee_el_codigo():
    texto = (RAIZ / ".env.example").read_text(encoding="utf-8")
    documentadas = set(re.findall(r"^#?\s*(DATATAB_[A-Z_]+)=", texto, flags=re.MULTILINE))
    fuente = (RAIZ / "backend" / "app" / "config.py").read_text(encoding="utf-8")
    usadas = {f"DATATAB_{nombre}" for nombre in re.findall(r'_(?:entero|booleano)\(env, "([A-Z_]+)"', fuente)}
    usadas |= set(re.findall(r'"(DATATAB_[A-Z_]+)"', fuente))
    assert documentadas == usadas


def test_los_valores_de_env_example_descomentados_coinciden_con_los_valores_por_defecto():
    texto = (RAIZ / ".env.example").read_text(encoding="utf-8")
    valores = dict(re.findall(r"^#\s*(DATATAB_[A-Z_]+)=(\S+)", texto, flags=re.MULTILINE))
    assert cargar_configuracion(valores) == Configuracion()
