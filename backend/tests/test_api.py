"""API completa con TestClient: cada endpoint, cada código de error del contrato y las cabeceras."""

import asyncio
import dataclasses
import logging

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict

from app import schemas
from app.config import Configuracion
from app.errors import ESTADO_HTTP
from app.main import crear_app, purgar_periodicamente
from app.services.dataset_store import AlmacenDatasets
from ayudas import crear_csv, crear_xls, crear_xlsx
from conftest import DATOS_DE_PRUEBA, RelojFalso

SECRETO = "SECRETO-CELDA-5521"


# --- Apoyo -----------------------------------------------------------------------------------------------


class ErrorContrato(BaseModel):
    model_config = ConfigDict(extra="forbid")
    codigo: str
    mensaje: str
    sugerencia: str | None = None
    detalle: dict | None = None


class SobreError(BaseModel):
    model_config = ConfigDict(extra="forbid")
    error: ErrorContrato


def subir(cliente: TestClient, nombre: str, contenido: bytes, tipo: str = "application/octet-stream"):
    return cliente.post("/api/datasets", files={"archivo": (nombre, contenido, tipo)})


def subir_pacientes(cliente: TestClient) -> dict:
    respuesta = subir(cliente, "pacientes-ficticios.xlsx", (DATOS_DE_PRUEBA / "pacientes-ficticios.xlsx").read_bytes())
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def frecuencias(cliente, dataset_id, columna, rangos=None):
    cuerpo = {"columna": columna} if rangos is None else {"columna": columna, "rangos": rangos}
    return cliente.post(f"/api/datasets/{dataset_id}/frecuencias", json=cuerpo)


def cruce(cliente, dataset_id, fila, columna):
    return cliente.post(f"/api/datasets/{dataset_id}/tabla-cruzada", json={"fila": fila, "columna": columna})


def verificar_error(respuesta, codigo: str) -> ErrorContrato:
    assert respuesta.status_code == ESTADO_HTTP[codigo], respuesta.text
    assert respuesta.headers["content-type"].startswith("application/json")
    error = SobreError.model_validate(respuesta.json()).error
    assert error.codigo == codigo
    assert error.mensaje and (error.mensaje[0].isupper() or error.mensaje[0] == "«")
    assert "Traceback" not in respuesta.text and "File \"" not in respuesta.text
    verificar_cabeceras(respuesta, api=True)
    return error


def verificar_cabeceras(respuesta, api: bool) -> None:
    cabeceras = respuesta.headers
    assert cabeceras["x-content-type-options"] == "nosniff"
    assert cabeceras["referrer-policy"] == "no-referrer"
    assert "default-src 'self'" in cabeceras["content-security-policy"]
    if api:
        assert cabeceras["cache-control"] == "no-store"


@pytest.fixture
def crear(reloj):
    """Fábrica de clientes con la configuración que se pida."""

    def fabrica(**cambios) -> TestClient:
        config = dataclasses.replace(Configuracion(), **cambios)
        return TestClient(crear_app(config, reloj), raise_server_exceptions=False)

    return fabrica


# --- Endpoints generales ---------------------------------------------------------------------------------------


def test_salud(cliente):
    respuesta = cliente.get("/api/salud")
    assert respuesta.status_code == 200 and respuesta.json() == {"estado": "ok"}


def test_configuracion_con_los_valores_del_contrato(cliente):
    respuesta = cliente.get("/api/configuracion")
    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "max_mb": 5, "max_bytes": 5242880, "formatos": ["xlsx", "xls", "csv"], "minutos_inactividad": 30,
        "max_filas": 100000, "max_columnas": 200, "max_celdas": 2000000,
    }  # fmt: skip
    schemas.ConfiguracionRespuesta.model_validate(respuesta.json())


def test_configuracion_refleja_la_configuracion_real(crear):
    cliente = crear(max_mb=2, ttl_min=10, max_filas=50)
    cuerpo = cliente.get("/api/configuracion").json()
    assert (cuerpo["max_mb"], cuerpo["max_bytes"], cuerpo["minutos_inactividad"], cuerpo["max_filas"]) == (2, 2097152, 10, 50)


# --- Subida ------------------------------------------------------------------------------------------------------------


def test_subir_un_archivo_con_la_forma_exacta_del_contrato(cliente, pacientes_bytes):
    respuesta = subir(cliente, "pacientes-ficticios.xlsx", pacientes_bytes)
    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    modelo = schemas.DatasetRespuesta.model_validate(cuerpo)  # cualquier campo de más o de menos falla
    assert (modelo.nombre, modelo.formato, modelo.filas, modelo.expira_en_segundos) == ("pacientes-ficticios.xlsx", "xlsx", 200, 1800)
    assert len(modelo.dataset_id) == 22 and modelo.avisos == []
    edad = next(c for c in cuerpo["columnas"] if c["nombre"] == "Edad")
    assert (edad["tipo"], edad["no_numericos"]) == ("numerica", 0) and edad["vacios"] > 0 and 15 < edad["minimo"] < edad["maximo"] <= 92
    sexo = next(c for c in cuerpo["columnas"] if c["nombre"] == "Sexo")
    assert (sexo["tipo"], sexo["minimo"], sexo["maximo"]) == ("texto", None, None)
    verificar_cabeceras(respuesta, api=True)


def test_subir_un_archivo_xlsx(cliente, pacientes_bytes):
    respuesta = subir(cliente, "mis datos.xlsx", pacientes_bytes)
    assert respuesta.status_code == 201
    assert respuesta.json()["nombre"] == "mis datos.xlsx"


@pytest.mark.parametrize(
    "nombre, formato, filas",
    [
        ("pacientes-ficticios.xlsx", "xlsx", 200),
        ("ficticio-antiguo.xls", "xls", 50),
        ("ficticio-punto-y-coma.csv", "csv", 60),
        ("ficticio-con-suciedad.xlsx", "xlsx", 40),
        ("ficticio-titulo-en-primera-fila.xlsx", "xlsx", 31),
    ],
)
def test_subir_cada_archivo_ficticio(cliente, nombre, formato, filas):
    respuesta = subir(cliente, nombre, (DATOS_DE_PRUEBA / nombre).read_bytes())
    assert respuesta.status_code == 201
    modelo = schemas.DatasetRespuesta.model_validate(respuesta.json())
    assert (modelo.formato, modelo.filas) == (formato, filas)


def test_los_avisos_viajan_en_la_subida_con_la_forma_del_contrato(cliente):
    respuesta = subir(cliente, "ficticio-titulo-en-primera-fila.xlsx", (DATOS_DE_PRUEBA / "ficticio-titulo-en-primera-fila.xlsx").read_bytes())
    assert respuesta.json()["avisos"] == [
        {"codigo": "ENCABEZADOS_DUDOSOS", "nivel": "atencion", "mensaje": "La primera fila no parece tener nombres de columna."}
    ]


def test_el_nombre_se_reduce_al_nombre_de_archivo(cliente):
    contenido = crear_csv([["a"], [1]])
    for enviado, esperado in [
        ("../../etc/datos.csv", "datos.csv"),
        ("..\\..\\Windows\\datos.csv", "datos.csv"),
        ("x" * 300 + ".csv", "x" * 116 + ".csv"),
    ]:
        respuesta = subir(cliente, enviado, contenido)
        assert respuesta.status_code == 201 and respuesta.json()["nombre"] == esperado, enviado


def test_columnas_con_html_se_devuelven_tal_cual(cliente):
    nombre_malo = "<script>alert('x')</script>"
    contenido = crear_csv([[nombre_malo, "b"], ["<img src=x onerror=alert(1)>", "2"], ["y", "3"]])
    respuesta = subir(cliente, "x.csv", contenido)
    assert respuesta.status_code == 201
    assert respuesta.json()["columnas"][0]["nombre"] == nombre_malo
    assert respuesta.headers["content-type"].startswith("application/json") and respuesta.headers["x-content-type-options"] == "nosniff"
    dataset_id = respuesta.json()["dataset_id"]
    resultado = frecuencias(cliente, dataset_id, nombre_malo).json()
    assert resultado["columna"] == nombre_malo
    assert resultado["filas"][0]["etiqueta"] in ("<img src=x onerror=alert(1)>", "y")
    filas = cliente.get(f"/api/datasets/{dataset_id}/filas").json()
    assert filas["columnas"][0] == nombre_malo and filas["filas"][0][0] == "<img src=x onerror=alert(1)>"


def test_subida_sin_el_campo_archivo(cliente):
    respuesta = cliente.post("/api/datasets", files={"otro": ("a.csv", b"a\n1\n")})
    error = verificar_error(respuesta, "PETICION_NO_VALIDA")
    assert "archivo" in error.mensaje
    verificar_error(cliente.post("/api/datasets"), "PETICION_NO_VALIDA")
    verificar_error(cliente.post("/api/datasets", json={"archivo": "x"}), "PETICION_NO_VALIDA")
    verificar_error(cliente.post("/api/datasets", data={"archivo": "no soy un archivo"}), "PETICION_NO_VALIDA")


# --- Consultar y borrar -------------------------------------------------------------------------------------------------------


def test_obtener_el_archivo_devuelve_lo_mismo_sin_avisos(cliente):
    subido = subir(cliente, "ficticio-con-suciedad.xlsx", (DATOS_DE_PRUEBA / "ficticio-con-suciedad.xlsx").read_bytes()).json()
    assert subido["avisos"]
    respuesta = cliente.get(f"/api/datasets/{subido['dataset_id']}")
    assert respuesta.status_code == 200
    assert schemas.DatasetRespuesta.model_validate(respuesta.json()).avisos == []
    assert respuesta.json() == {**subido, "avisos": []}


def test_filas_paginadas_con_la_forma_del_contrato(cliente):
    dataset_id = subir_pacientes(cliente)["dataset_id"]
    respuesta = cliente.get(f"/api/datasets/{dataset_id}/filas")
    modelo = schemas.FilasRespuesta.model_validate(respuesta.json())
    assert (modelo.total, modelo.desde, modelo.cantidad, len(modelo.filas)) == (200, 0, 50, 50)
    assert modelo.columnas[:3] == ["No.", "Sexo", "Edad"] and len(modelo.filas[0]) == 10
    assert modelo.filas[0][0] == "1" and all(isinstance(c, str) for fila in modelo.filas for c in fila)

    ultimo = cliente.get(f"/api/datasets/{dataset_id}/filas", params={"desde": 190, "cantidad": 200}).json()
    assert (ultimo["desde"], ultimo["cantidad"], len(ultimo["filas"])) == (190, 10, 10)
    pasado = cliente.get(f"/api/datasets/{dataset_id}/filas", params={"desde": 5000}).json()
    assert (pasado["total"], pasado["cantidad"], pasado["filas"]) == (200, 0, [])


def test_las_celdas_vacias_son_cadenas_vacias(cliente):
    dataset_id = subir(cliente, "x.csv", b"A,B,Fila\n1,,1\n,y,2\n").json()["dataset_id"]
    assert cliente.get(f"/api/datasets/{dataset_id}/filas").json()["filas"] == [["1", "", "1"], ["", "y", "2"]]


@pytest.mark.parametrize("parametros", [{"cantidad": 0}, {"cantidad": 201}, {"desde": -1}, {"desde": "abc"}, {"cantidad": "x"}, {"desde": 1.5}])
def test_filas_con_parametros_no_validos(cliente, parametros):
    dataset_id = subir_pacientes(cliente)["dataset_id"]
    verificar_error(cliente.get(f"/api/datasets/{dataset_id}/filas", params=parametros), "PETICION_NO_VALIDA")


def test_filas_con_desde_enorme(cliente):
    dataset_id = subir_pacientes(cliente)["dataset_id"]
    respuesta = cliente.get(f"/api/datasets/{dataset_id}/filas", params={"desde": 10**30})
    assert respuesta.status_code == 200 and respuesta.json()["filas"] == []


def test_borrar_es_idempotente(cliente):
    dataset_id = subir_pacientes(cliente)["dataset_id"]
    primero = cliente.delete(f"/api/datasets/{dataset_id}")
    assert primero.status_code == 204 and primero.content == b""
    assert cliente.delete(f"/api/datasets/{dataset_id}").status_code == 204
    assert cliente.delete("/api/datasets/nunca-existio").status_code == 204
    verificar_error(cliente.get(f"/api/datasets/{dataset_id}"), "ARCHIVO_NO_ENCONTRADO")
    verificar_cabeceras(primero, api=True)


@pytest.mark.parametrize("dataset_id", ["inventado", "x" * 5000, "%00", "<script>", "ñandú", "a b"])
def test_dataset_id_inventado(cliente, dataset_id):
    for respuesta in (
        cliente.get(f"/api/datasets/{dataset_id}"),
        cliente.get(f"/api/datasets/{dataset_id}/filas"),
        frecuencias(cliente, dataset_id, "Edad"),
        cruce(cliente, dataset_id, {"columna": "a"}, {"columna": "b"}),
    ):
        verificar_error(respuesta, "ARCHIVO_NO_ENCONTRADO")


def test_dataset_id_con_barras_codificadas_no_sale_de_la_api(cliente):
    # %2F llega decodificado como "/": la ruta ya no coincide con ninguna y la respuesta es el 404 JSON.
    for ruta in ("/api/datasets/..%2F..%2Fetc%2Fpasswd", "/api/datasets/..%2F..%2Fetc%2Fpasswd/filas", "/api/datasets/%2e%2e/%2e%2e/etc/passwd"):
        respuesta = cliente.get(ruta)
        assert respuesta.status_code == 404
        assert respuesta.headers["content-type"].startswith("application/json")
        assert SobreError.model_validate(respuesta.json()).error.codigo in {"RUTA_NO_ENCONTRADA", "ARCHIVO_NO_ENCONTRADO"}
        assert "passwd" not in respuesta.text


def test_caducidad_por_inactividad(cliente, reloj):
    dataset_id = subir_pacientes(cliente)["dataset_id"]
    reloj.avanzar(29 * 60)
    assert cliente.get(f"/api/datasets/{dataset_id}").json()["expira_en_segundos"] == 1800  # renovado
    reloj.avanzar(29 * 60)
    assert frecuencias(cliente, dataset_id, "Sexo").status_code == 200  # cada uso renueva el plazo
    reloj.avanzar(31 * 60)
    for respuesta in (
        cliente.get(f"/api/datasets/{dataset_id}"),
        cliente.get(f"/api/datasets/{dataset_id}/filas"),
        frecuencias(cliente, dataset_id, "Sexo"),
    ):
        error = verificar_error(respuesta, "ARCHIVO_NO_ENCONTRADO")
        assert "caducado" in error.mensaje and error.sugerencia == "Vuelve a subirlo."


def test_el_tope_de_archivos_expulsa_el_menos_usado(crear):
    cliente = crear(max_datasets=2)
    primero, segundo = (subir_pacientes(cliente)["dataset_id"] for _ in range(2))
    cliente.get(f"/api/datasets/{primero}")
    tercero = subir_pacientes(cliente)["dataset_id"]
    assert cliente.get(f"/api/datasets/{primero}").status_code == 200
    assert cliente.get(f"/api/datasets/{tercero}").status_code == 200
    verificar_error(cliente.get(f"/api/datasets/{segundo}"), "ARCHIVO_NO_ENCONTRADO")


# --- Análisis -------------------------------------------------------------------------------------------------------------------


def test_frecuencias_sin_y_con_rangos(cliente):
    dataset_id = subir_pacientes(cliente)["dataset_id"]
    sin = frecuencias(cliente, dataset_id, "Sexo")
    modelo = schemas.FrecuenciasRespuesta.model_validate(sin.json())
    assert (modelo.tipo, modelo.agrupado, modelo.n, modelo.vacios_excluidos, modelo.solapados) == ("texto", False, 200, 0, 0)
    assert sum(f.frecuencia for f in modelo.filas) == 200 and {f.tipo for f in modelo.filas} == {"valor"}

    con = frecuencias(cliente, dataset_id, "Edad", ["<30", "30-39", "40-59", ">=60"])
    modelo = schemas.FrecuenciasRespuesta.model_validate(con.json())
    assert (modelo.tipo, modelo.agrupado, modelo.n, modelo.vacios_excluidos) == ("numerica", True, 197, 3)
    assert [f.rango for f in modelo.filas] == ["<30", "30-39", "40-59", ">=60"]
    assert [f.etiqueta for f in modelo.filas] == ["Menos de 30", "30 a 39", "40 a 59", "60 o más"]
    assert sum(f.frecuencia for f in modelo.filas) == 197 and modelo.avisos == []
    verificar_cabeceras(con, api=True)


def test_frecuencias_de_una_columna_con_demasiados_valores_distintos(crear):
    cliente = crear(max_valores_distintos=50)
    dataset_id = subir_pacientes(cliente)["dataset_id"]  # «No.» va de 1 a 200
    error = verificar_error(frecuencias(cliente, dataset_id, "No."), "DEMASIADAS_CATEGORIAS")
    assert error.mensaje == "«No.» tiene 200 valores distintos; son demasiados para una tabla de frecuencias."
    assert error.sugerencia == "Agrúpalos en rangos, por ejemplo 0-9, 10-19…"
    assert error.detalle == {"valores_distintos": 200, "maximo": 50}
    # con rangos sí se puede, y una columna con pocos valores distintos no se ve afectada
    assert frecuencias(cliente, dataset_id, "No.", ["1-100", "101-200"]).status_code == 200
    assert frecuencias(cliente, dataset_id, "Sexo").status_code == 200


@pytest.mark.parametrize("distintos, estado", [(1000, 200), (1001, 422)])
def test_el_tope_de_fabrica_son_1000_valores_distintos(cliente, distintos, estado):
    contenido = crear_csv([["Codigo"]] + [[f"C{i}"] for i in range(distintos)])
    dataset_id = subir(cliente, "codigos.csv", contenido).json()["dataset_id"]
    respuesta = frecuencias(cliente, dataset_id, "Codigo")
    assert respuesta.status_code == estado
    if estado == 422:
        error = verificar_error(respuesta, "DEMASIADAS_CATEGORIAS")
        assert error.detalle == {"valores_distintos": 1001, "maximo": 1000}
        assert len(respuesta.content) < 600  # el rechazo no arrastra las 1001 filas
    else:
        assert len(respuesta.json()["filas"]) == 1000


def test_frecuencias_con_rangos_solapados_avisan(cliente):
    dataset_id = subir_pacientes(cliente)["dataset_id"]
    cuerpo = frecuencias(cliente, dataset_id, "Edad", ["30-39", "35-45"]).json()
    assert cuerpo["solapados"] > 0 and cuerpo["avisos"][0]["codigo"] == "RANGOS_SOLAPADOS"
    schemas.FrecuenciasRespuesta.model_validate(cuerpo)


def test_tabla_cruzada_con_la_forma_del_contrato(cliente):
    dataset_id = subir_pacientes(cliente)["dataset_id"]
    respuesta = cruce(cliente, dataset_id, {"columna": "Edad", "rangos": ["<30", "30-39", "40+"]}, {"columna": "Sexo"})
    modelo = schemas.TablaCruzadaRespuesta.model_validate(respuesta.json())
    assert modelo.fila.agrupado is True and modelo.columna.agrupado is False
    assert (modelo.n, modelo.vacios_excluidos) == (197, 3)
    assert [c.etiqueta for c in modelo.columnas] == ["Femenino", "Masculino"]
    assert sum(f.total for f in modelo.filas) == modelo.n == sum(t.frecuencia for t in modelo.totales_columna)
    verificar_cabeceras(respuesta, api=True)


def test_tabla_cruzada_sin_rangos_y_cuerpo_con_campos_de_mas(cliente):
    dataset_id = subir_pacientes(cliente)["dataset_id"]
    respuesta = cliente.post(
        f"/api/datasets/{dataset_id}/tabla-cruzada",
        json={"fila": {"columna": "Diagnóstico"}, "columna": {"columna": "Tipo de cirugía", "otro": 1}, "extra": True},
    )
    assert respuesta.status_code == 200
    assert schemas.TablaCruzadaRespuesta.model_validate(respuesta.json()).n == 200


# --- Cada código de error del contrato ---------------------------------------------------------------------------------------------


def _pacientes(crear, **config):
    cliente = crear(**config)
    return cliente, subir_pacientes(cliente)["dataset_id"]


def _error_interno(crear, monkeypatch):
    cliente, dataset_id = _pacientes(crear)

    def falla(*_args, **_kwargs):
        raise RuntimeError(f"fallo interno con {SECRETO} en /home/usuario/secreto.py")

    monkeypatch.setattr("app.api.analisis.calcular_frecuencias", falla)
    return frecuencias(cliente, dataset_id, "Sexo")


PROVOCAR = {
    "PETICION_NO_VALIDA": lambda crear, mp: crear().post("/api/datasets/x/frecuencias", json={"rangos": 5}),
    "ARCHIVO_NO_ENCONTRADO": lambda crear, mp: crear().get("/api/datasets/inventado"),
    "RUTA_NO_ENCONTRADA": lambda crear, mp: crear().get("/api/inexistente"),
    "METODO_NO_PERMITIDO": lambda crear, mp: crear().post("/api/salud"),
    "ARCHIVO_DEMASIADO_GRANDE": lambda crear, mp: subir(crear(max_mb=1), "a.csv", b"a\n" + b"1\n" * (600 * 1024)),
    "FORMATO_NO_SOPORTADO": lambda crear, mp: subir(crear(), "documento.pdf", b"%PDF-1.4"),
    "CONTENIDO_NO_COINCIDE": lambda crear, mp: subir(crear(), "falso.xlsx", b"texto, no un excel"),
    "ARCHIVO_ILEGIBLE": lambda crear, mp: subir(crear(), "roto.xlsx", b"PK\x03\x04" + bytes(500)),
    "ARCHIVO_VACIO": lambda crear, mp: subir(crear(), "vacio.csv", b""),
    "TABLA_DEMASIADO_GRANDE": lambda crear, mp: subir(crear(max_filas=1), "a.csv", b"a\n1\n2\n"),
    "COLUMNA_NO_ENCONTRADA": lambda crear, mp: frecuencias(*_pacientes(crear), "No existe"),
    "COLUMNAS_IGUALES": lambda crear, mp: cruce(*_pacientes(crear), {"columna": "Sexo"}, {"columna": "Sexo"}),
    "RANGO_NO_VALIDO": lambda crear, mp: frecuencias(*_pacientes(crear), "Edad", ["<30", "esto no es un rango"]),
    "RANGO_REPETIDO": lambda crear, mp: frecuencias(*_pacientes(crear), "Edad", ["40+", ">=40"]),
    "DEMASIADOS_RANGOS": lambda crear, mp: frecuencias(*_pacientes(crear), "Edad", [f"{i}-{i}" for i in range(51)]),
    "RANGOS_EN_COLUMNA_NO_NUMERICA": lambda crear, mp: frecuencias(*_pacientes(crear), "Sexo", ["<30"]),
    "RANGOS_SOLAPADOS_EN_CRUCE": lambda crear, mp: cruce(
        *_pacientes(crear), {"columna": "Edad", "rangos": ["30-39", "35-45"]}, {"columna": "Sexo"}
    ),
    "SIN_DATOS": lambda crear, mp: frecuencias(
        (c := crear()), c.post("/api/datasets", files={"archivo": ("a.csv", b"A,B\n1,\n2,\n")}).json()["dataset_id"], "B"
    ),
    "DEMASIADAS_CATEGORIAS": lambda crear, mp: cruce(*_pacientes(crear), {"columna": "No."}, {"columna": "Edad"}),
    "ERROR_INTERNO": _error_interno,
}


def test_hay_un_caso_por_cada_codigo_del_contrato():
    assert set(PROVOCAR) == set(ESTADO_HTTP)


@pytest.mark.parametrize("codigo", sorted(ESTADO_HTTP))
def test_cada_codigo_de_error_del_contrato(codigo, crear, monkeypatch):
    error = verificar_error(PROVOCAR[codigo](crear, monkeypatch), codigo)
    if codigo == "ERROR_INTERNO":
        assert error.detalle is None and SECRETO not in error.mensaje
    if codigo == "ARCHIVO_DEMASIADO_GRANDE":
        assert error.detalle["max_mb"] == 1 and error.detalle["tamano_mb"] > 1
        assert error.mensaje.startswith("El archivo pesa ") and error.mensaje.endswith(" MB. El máximo es 1 MB.")
    if codigo == "RANGO_NO_VALIDO":
        assert error.detalle == {"rango": "esto no es un rango"}
    if codigo == "COLUMNA_NO_ENCONTRADA":
        assert error.detalle == {"columna": "No existe"}


def test_peticiones_mal_formadas(cliente):
    dataset_id = subir_pacientes(cliente)["dataset_id"]
    url = f"/api/datasets/{dataset_id}/frecuencias"
    for kwargs in (
        {"content": b"{no es json", "headers": {"content-type": "application/json"}},
        {"json": {"columna": 5}},
        {"json": {"columna": "Edad", "rangos": "30-39"}},
        {"json": {"columna": "Edad", "rangos": [30]}},
        {"json": ["Edad"]},
        {"json": None},
        {"content": b"columna=Edad", "headers": {"content-type": "application/x-www-form-urlencoded"}},
    ):
        verificar_error(cliente.post(url, **kwargs), "PETICION_NO_VALIDA")
    verificar_error(cliente.post(f"/api/datasets/{dataset_id}/tabla-cruzada", json={"fila": "Sexo", "columna": "Edad"}), "PETICION_NO_VALIDA")


def test_la_validacion_nombra_los_campos_sin_repetir_los_valores(cliente):
    dataset_id = subir_pacientes(cliente)["dataset_id"]
    cuerpo = cliente.post(f"/api/datasets/{dataset_id}/frecuencias", json={"columna": SECRETO * 0 + "Edad", "rangos": [SECRETO]}).json()
    assert cuerpo["error"]["codigo"] == "RANGO_NO_VALIDO"
    cuerpo = cliente.post(f"/api/datasets/{dataset_id}/frecuencias", json={"columna": {"x": SECRETO}}).json()
    assert cuerpo["error"]["detalle"] == {"campos": ["columna"]} and SECRETO not in str(cuerpo)


def test_rangos_con_texto_malicioso(cliente):
    dataset_id = subir_pacientes(cliente)["dataset_id"]
    for malo in ("<script>alert(1)</script>", "'; DROP TABLE datos;--", "{{7*7}}", "${jndi:ldap://x}", "A" * 100_000, "‮30-39", "30-39\x00"):
        respuesta = frecuencias(cliente, dataset_id, "Edad", ["<30", malo])
        error = verificar_error(respuesta, "RANGO_NO_VALIDO")
        assert len(respuesta.text) < 600 and len(error.detalle["rango"]) <= 41


def test_ruta_inexistente_bajo_api_devuelve_json_siempre(cliente):
    for metodo in ("get", "post", "put", "delete", "patch"):
        respuesta = getattr(cliente, metodo)("/api/inexistente")
        verificar_error(respuesta, "RUTA_NO_ENCONTRADA")
    verificar_error(cliente.get("/api/datasets/a/b/c/d"), "RUTA_NO_ENCONTRADA")
    verificar_error(cliente.get("/api/"), "RUTA_NO_ENCONTRADA")


def test_metodo_no_permitido_indica_los_permitidos(cliente):
    respuesta = cliente.delete("/api/salud")
    verificar_error(respuesta, "METODO_NO_PERMITIDO")
    assert "GET" in respuesta.headers["allow"]
    verificar_error(cliente.get("/api/datasets/x/frecuencias"), "METODO_NO_PERMITIDO")
    verificar_error(cliente.put("/api/datasets/x"), "METODO_NO_PERMITIDO")


# --- Errores internos: ni datos ni rutas en la respuesta ni en el registro ----------------------------------------------------------------------


def test_un_error_inesperado_es_500_generico_y_solo_registra_el_tipo_y_la_ruta(crear, monkeypatch, caplog):
    cliente, dataset_id = _pacientes(crear)

    def falla(*_args, **_kwargs):
        raise ValueError(f"valor raro: {SECRETO}, archivo /home/usuario/datos.xlsx")

    monkeypatch.setattr("app.api.analisis.calcular_frecuencias", falla)
    with caplog.at_level(logging.DEBUG):
        respuesta = frecuencias(cliente, dataset_id, "Sexo")
    error = verificar_error(respuesta, "ERROR_INTERNO")
    assert error.mensaje == "Ocurrió un error inesperado." and error.detalle is None
    assert SECRETO not in respuesta.text and "/home" not in respuesta.text and "ValueError" not in respuesta.text

    registros = [r for r in caplog.records if r.name == "datatab"]
    assert len(registros) == 1 and registros[0].exc_info is None
    texto = caplog.text
    assert "ValueError" in texto and f"/api/datasets/{dataset_id}/frecuencias" in texto
    assert SECRETO not in texto and "/home/usuario" not in texto and "Traceback" not in texto


def test_el_registro_escapa_los_caracteres_de_control_de_la_ruta(crear, monkeypatch, caplog):
    cliente, _ = _pacientes(crear)
    monkeypatch.setattr("app.services.dataset_store.AlmacenDatasets.obtener", lambda *a, **k: 1 / 0)
    with caplog.at_level(logging.DEBUG):
        respuesta = cliente.get("/api/datasets/falso%0AINFO%20linea%20falsa")
    verificar_error(respuesta, "ERROR_INTERNO")
    registros = [r for r in caplog.records if r.name == "datatab"]
    assert len(registros) == 1
    mensaje = registros[0].getMessage()
    assert "\n" not in mensaje and "\r" not in mensaje
    assert "ZeroDivisionError" in mensaje and "falso" in mensaje


def test_un_error_de_respuesta_con_forma_incorrecta_tambien_es_500_generico(crear, monkeypatch):
    cliente, dataset_id = _pacientes(crear)
    monkeypatch.setattr("app.api.analisis.calcular_frecuencias", lambda *a, **k: {"columna": SECRETO})
    respuesta = frecuencias(cliente, dataset_id, "Sexo")
    verificar_error(respuesta, "ERROR_INTERNO")
    assert SECRETO not in respuesta.text


# --- Cabeceras, documentación y frontend ---------------------------------------------------------------------------------------------------------


CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; "
    "connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'"
)


def test_cabeceras_de_seguridad_exactas_en_las_respuestas_de_la_api(cliente):
    for respuesta in (cliente.get("/api/salud"), cliente.get("/api/inexistente"), subir(cliente, "a.csv", b"a\n1\n")):
        assert respuesta.headers["content-security-policy"] == CSP
        assert respuesta.headers["x-content-type-options"] == "nosniff"
        assert respuesta.headers["referrer-policy"] == "no-referrer"
        assert respuesta.headers["cache-control"] == "no-store"


def test_documentacion_sin_csp_estricta_y_sin_no_store(cliente):
    for ruta in ("/docs", "/redoc", "/openapi.json"):
        respuesta = cliente.get(ruta)
        assert respuesta.status_code == 200, ruta
        assert "content-security-policy" not in respuesta.headers
        assert respuesta.headers["x-content-type-options"] == "nosniff"
    rutas = cliente.get("/openapi.json").json()["paths"]
    assert "/api/datasets/{dataset_id}/tabla-cruzada" in rutas and "/api/datasets" in rutas


def test_documentacion_desactivable(crear):
    cliente = crear(docs=False)
    for ruta in ("/docs", "/redoc", "/openapi.json"):
        assert cliente.get(ruta).status_code == 404


@pytest.fixture
def frontend(tmp_path, monkeypatch):
    (tmp_path / "index.html").write_text("<!doctype html><title>DataTab</title>", encoding="utf-8")
    (tmp_path / "app.js").write_text("export {};", encoding="utf-8")
    monkeypatch.setattr("app.main.FRONTEND", tmp_path)
    return tmp_path


def test_el_frontend_se_sirve_despues_de_las_rutas_api(crear, frontend):
    cliente = crear()
    pagina = cliente.get("/")
    assert pagina.status_code == 200 and "<title>DataTab</title>" in pagina.text
    assert pagina.headers["content-security-policy"] == CSP and pagina.headers["x-content-type-options"] == "nosniff"
    assert "cache-control" not in pagina.headers  # no-store solo en /api
    assert cliente.get("/app.js").status_code == 200
    assert cliente.get("/no-existe.js").status_code == 404
    assert cliente.get("/api/salud").json() == {"estado": "ok"}


def test_con_frontend_montado_las_rutas_api_inexistentes_siguen_siendo_json(crear, frontend):
    cliente = crear()
    for metodo in ("get", "post", "delete"):
        verificar_error(getattr(cliente, metodo)("/api/inexistente"), "RUTA_NO_ENCONTRADA")
    verificar_error(cliente.get("/api/index.html"), "RUTA_NO_ENCONTRADA")  # no se sirve como archivo estático
    verificar_error(cliente.post("/api/salud"), "METODO_NO_PERMITIDO")
    assert cliente.post("/").status_code == 405


def test_sin_servir_frontend_solo_hay_api(crear, frontend):
    cliente = crear(servir_frontend=False)
    assert cliente.get("/").status_code == 404 and cliente.get("/api/salud").status_code == 200


def test_si_no_existe_la_carpeta_del_frontend_la_api_funciona(crear, tmp_path, monkeypatch):
    monkeypatch.setattr("app.main.FRONTEND", tmp_path / "no-existe")
    cliente = crear()
    assert cliente.get("/").status_code == 404 and cliente.get("/api/salud").status_code == 200


# --- Ciclo de vida -------------------------------------------------------------------------------------------------------------------------------


def test_al_apagar_el_servidor_no_queda_nada_en_memoria(app, reloj):
    with TestClient(app) as cliente:
        subir_pacientes(cliente)
        assert len(app.state.almacen) == 1
    assert len(app.state.almacen) == 0


def test_la_purga_periodica_elimina_los_caducados():
    reloj = RelojFalso()
    almacen = AlmacenDatasets(ttl_segundos=60, max_datasets=5, reloj=reloj)
    from ayudas import leer_filas

    leida = leer_filas([["A"], [1]])
    almacen.guardar("a.xlsx", "xlsx", leida.tabla, leida.perfiles)

    async def probar():
        tarea = asyncio.create_task(purgar_periodicamente(almacen, intervalo=0.01))
        await asyncio.sleep(0.05)
        assert len(almacen) == 1  # aún no ha caducado
        reloj.avanzar(61)
        await asyncio.sleep(0.05)
        tarea.cancel()
        assert len(almacen) == 0

    asyncio.run(probar())


def test_subir_xls_y_csv_por_la_api(cliente):
    assert subir(cliente, "a.xls", crear_xls([["A", "B"], [1, "x"], [2, "y"]])).json()["formato"] == "xls"
    assert subir(cliente, "a.csv", crear_csv([["A", "B"], [1, "x"], [2, "y"]], ";")).json()["formato"] == "csv"
    assert subir(cliente, "a.xlsx", crear_xlsx([["A", "B"], [1, "x"], [2, "y"]])).json()["filas"] == 2
