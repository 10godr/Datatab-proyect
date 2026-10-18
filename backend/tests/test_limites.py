"""El límite de 5 MB es real: exactamente 5 MB pasa, 5 MB + 1 byte da 413 y un cuerpo enorme se corta pronto."""

import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from app.config import MB, Configuracion
from app.main import crear_app
from app.seguridad import MARGEN_CUERPO

LIMITE = 5 * MB
FRONTERA = "----frontera-de-prueba"
TIPO_MULTIPART = f"multipart/form-data; boundary={FRONTERA}"


def csv_de_tamano(tamano: int) -> bytes:
    """CSV válido de exactamente `tamano` bytes (filas largas, pocas filas)."""
    texto = "a,b\n"
    fila = "x" * 998 + ",1\n"  # 1001 bytes
    cuerpo = bytearray(texto.encode())
    while len(cuerpo) + len(fila) <= tamano:
        cuerpo += fila.encode()
    falta = tamano - len(cuerpo)
    if falta:
        cuerpo += b"y" * (falta - 1) + b"\n" if falta > 1 else b"\n"
    assert len(cuerpo) == tamano
    return bytes(cuerpo)


def cuerpo_multipart(contenido: bytes, nombre: str = "datos.csv") -> bytes:
    cabecera = (
        f"--{FRONTERA}\r\n"
        f'Content-Disposition: form-data; name="archivo"; filename="{nombre}"\r\n'
        "Content-Type: text/csv\r\n\r\n"
    ).encode()
    return cabecera + contenido + f"\r\n--{FRONTERA}--\r\n".encode()


def codigo_de(respuesta) -> str:
    return respuesta.json()["error"]["codigo"]


# --- Con cliente HTTP -------------------------------------------------------------------------------------------


def test_un_archivo_de_exactamente_5_mb_se_acepta(cliente):
    contenido = csv_de_tamano(LIMITE)
    assert len(contenido) == 5_242_880
    respuesta = cliente.post("/api/datasets", files={"archivo": ("justo.csv", contenido, "text/csv")})
    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json()["columnas"][0]["nombre"] == "a" and respuesta.json()["filas"] > 5000


def test_un_archivo_de_5_mb_mas_un_byte_da_413_con_el_tamano_en_el_detalle(cliente):
    contenido = csv_de_tamano(LIMITE + 1)
    respuesta = cliente.post("/api/datasets", files={"archivo": ("pasado.csv", contenido, "text/csv")})
    assert respuesta.status_code == 413
    error = respuesta.json()["error"]
    assert error["codigo"] == "ARCHIVO_DEMASIADO_GRANDE"
    assert error["detalle"] == {"tamano_mb": 5.1, "max_mb": 5}
    assert "5,1 MB" in error["mensaje"]


def test_el_limite_se_aplica_a_los_bytes_del_archivo_y_no_al_cuerpo_multipart(cliente):
    # El sobre multipart añade unos cientos de bytes: un archivo de 5 MB - 1 pasa aunque el cuerpo supere 5 MB
    contenido = csv_de_tamano(LIMITE - 1)
    cuerpo = cuerpo_multipart(contenido)
    assert len(cuerpo) > LIMITE
    respuesta = cliente.post("/api/datasets", content=cuerpo, headers={"Content-Type": TIPO_MULTIPART})
    assert respuesta.status_code == 201, respuesta.text


def test_la_configuracion_cambia_el_limite():
    app = crear_app(Configuracion(max_mb=1))
    cliente = TestClient(app, raise_server_exceptions=False)
    assert cliente.get("/api/configuracion").json()["max_bytes"] == MB
    justo = cliente.post("/api/datasets", files={"archivo": ("a.csv", csv_de_tamano(MB), "text/csv")})
    assert justo.status_code == 201
    pasado = cliente.post("/api/datasets", files={"archivo": ("a.csv", csv_de_tamano(MB + 1), "text/csv")})
    assert pasado.status_code == 413 and pasado.json()["error"]["detalle"] == {"tamano_mb": 1.1, "max_mb": 1}


def test_content_length_enorme_se_rechaza_sin_leer_el_cuerpo(cliente):
    respuesta = cliente.post(
        "/api/datasets",
        content=b"x",
        headers={"Content-Type": TIPO_MULTIPART, "Content-Length": str(10 * 1024 * MB)},
    )
    assert respuesta.status_code == 413
    assert codigo_de(respuesta) == "ARCHIVO_DEMASIADO_GRANDE"
    assert respuesta.json()["error"]["detalle"]["max_mb"] == 5


def test_content_length_falso_menor_que_el_cuerpo_real_se_corta_igual(cliente):
    cuerpo = cuerpo_multipart(b"z" * (LIMITE + MARGEN_CUERPO + 10_000))
    respuesta = cliente.post(
        "/api/datasets", content=cuerpo, headers={"Content-Type": TIPO_MULTIPART, "Content-Length": "100"}
    )
    assert respuesta.status_code == 413
    assert codigo_de(respuesta) == "ARCHIVO_DEMASIADO_GRANDE"


def test_cuerpo_sin_content_length_se_corta_igual(cliente):
    def trozos():
        cuerpo = cuerpo_multipart(b"z" * (LIMITE + MARGEN_CUERPO + 10_000))
        for inicio in range(0, len(cuerpo), 65_536):
            yield cuerpo[inicio : inicio + 65_536]

    respuesta = cliente.post("/api/datasets", content=trozos(), headers={"Content-Type": TIPO_MULTIPART})
    assert respuesta.status_code == 413
    assert codigo_de(respuesta) == "ARCHIVO_DEMASIADO_GRANDE"


def test_content_length_que_no_es_un_numero_no_evita_el_limite(cliente):
    cuerpo = cuerpo_multipart(b"z" * (LIMITE + MARGEN_CUERPO + 10_000))
    respuesta = cliente.post(
        "/api/datasets", content=cuerpo, headers={"Content-Type": TIPO_MULTIPART, "Content-Length": "abc"}
    )
    assert respuesta.status_code == 413


def test_el_limite_no_afecta_a_las_peticiones_pequenas(cliente):
    assert cliente.get("/api/salud").status_code == 200
    assert cliente.post("/api/datasets/ejemplo").status_code == 201


# --- A nivel ASGI: se demuestra que el cuerpo enorme no se lee entero -----------------------------------------------------


class CuerpoVirtual:
    """Cuerpo de petición "infinito" que se genera bajo demanda y cuenta cuánto se ha pedido."""

    def __init__(self, tamano_total: int, tamano_trozo: int = 65_536):
        self.pendiente = tamano_total
        self.tamano_trozo = tamano_trozo
        self.trozos_pedidos = 0
        self.bytes_entregados = 0
        cabecera = (
            f"--{FRONTERA}\r\n"
            'Content-Disposition: form-data; name="archivo"; filename="enorme.csv"\r\n'
            "Content-Type: text/csv\r\n\r\n"
        ).encode()
        self._inicio: bytes | None = cabecera
        self._relleno = b"a,b\n" + b"1,2\n" * (tamano_trozo // 4)

    async def receive(self):
        self.trozos_pedidos += 1
        if self._inicio is not None:
            trozo, self._inicio = self._inicio, None
        elif self.pendiente > 0:
            trozo = self._relleno[: min(self.tamano_trozo, self.pendiente)]
            self.pendiente -= len(trozo)
        else:
            return {"type": "http.disconnect"}
        self.bytes_entregados += len(trozo)
        return {"type": "http.request", "body": trozo, "more_body": True}


async def enviar_a_la_app(app, cuerpo: CuerpoVirtual, content_length: int | None):
    cabeceras = [(b"content-type", TIPO_MULTIPART.encode()), (b"host", b"testserver")]
    if content_length is not None:
        cabeceras.append((b"content-length", str(content_length).encode()))
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/api/datasets",
        "raw_path": b"/api/datasets",
        "query_string": b"",
        "root_path": "",
        "headers": cabeceras,
        "client": ("127.0.0.1", 50000),
        "server": ("testserver", 80),
        "state": {},
    }
    enviados: list[dict] = []

    async def send(mensaje):
        enviados.append(mensaje)

    await asyncio.wait_for(app(scope, cuerpo.receive, send), timeout=30)
    inicio = next(m for m in enviados if m["type"] == "http.response.start")
    cuerpo_respuesta = b"".join(m.get("body", b"") for m in enviados if m["type"] == "http.response.body")
    return inicio, cuerpo_respuesta


def test_un_cuerpo_de_un_gigabyte_se_corta_al_pasar_el_limite(app):
    gigabyte = 1024 * MB
    cuerpo = CuerpoVirtual(gigabyte)
    inicio, contenido = asyncio.run(enviar_a_la_app(app, cuerpo, content_length=None))

    assert inicio["status"] == 413
    assert json.loads(contenido)["error"]["codigo"] == "ARCHIVO_DEMASIADO_GRANDE"
    limite = LIMITE + MARGEN_CUERPO
    # Se pidió lo justo para superar el límite (más como mucho un trozo) y nada más: ni el 1 % del gigabyte
    assert limite < cuerpo.bytes_entregados <= limite + 2 * cuerpo.tamano_trozo
    assert cuerpo.pendiente > gigabyte * 0.99
    cabeceras = {nombre.decode(): valor.decode() for nombre, valor in inicio["headers"]}
    assert cabeceras["x-content-type-options"] == "nosniff"
    assert cabeceras["cache-control"] == "no-store"
    assert "content-security-policy" in cabeceras


def test_un_content_length_falso_no_engana_al_corte_por_conteo(app):
    cuerpo = CuerpoVirtual(1024 * MB)
    inicio, _ = asyncio.run(enviar_a_la_app(app, cuerpo, content_length=1000))
    assert inicio["status"] == 413
    assert cuerpo.bytes_entregados <= LIMITE + MARGEN_CUERPO + 2 * cuerpo.tamano_trozo


def test_con_content_length_enorme_no_se_pide_ni_un_byte(app):
    cuerpo = CuerpoVirtual(1024 * MB)
    inicio, contenido = asyncio.run(enviar_a_la_app(app, cuerpo, content_length=1024 * MB))
    assert inicio["status"] == 413
    assert cuerpo.trozos_pedidos == 0 and cuerpo.bytes_entregados == 0
    assert json.loads(contenido)["error"]["detalle"]["max_mb"] == 5


@pytest.mark.parametrize("tamano", [LIMITE - 1, LIMITE, LIMITE + 1])
def test_los_tamanos_de_la_frontera_con_el_cliente_http(cliente, tamano):
    respuesta = cliente.post("/api/datasets", files={"archivo": ("f.csv", csv_de_tamano(tamano), "text/csv")})
    assert respuesta.status_code == (201 if tamano <= LIMITE else 413)

