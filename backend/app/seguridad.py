"""Middleware ASGI de seguridad: tope del cuerpo de la petición y cabeceras de las respuestas."""

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .config import MB
from .errors import archivo_demasiado_grande, respuesta_error

# Margen para el "envoltorio" multipart (límites, cabeceras de la parte) sobre el archivo
MARGEN_CUERPO = 64 * 1024

CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
    "font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; "
    "frame-ancestors 'none'; form-action 'self'"
)

# La documentación interactiva carga recursos de una CDN, así que no lleva la CSP estricta
RUTAS_SIN_CSP = frozenset({"/docs", "/docs/oauth2-redirect", "/redoc", "/openapi.json"})


def _cabeceras_de_seguridad(ruta: str) -> dict[str, str]:
    cabeceras = {"X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer"}
    if ruta not in RUTAS_SIN_CSP:
        cabeceras["Content-Security-Policy"] = CSP
    if ruta == "/api" or ruta.startswith("/api/"):
        cabeceras["Cache-Control"] = "no-store"
    return cabeceras


def _content_length(scope: Scope) -> int | None:
    for nombre, valor in scope["headers"]:
        if nombre == b"content-length":
            try:
                longitud = int(valor)
            except ValueError:
                return None
            return longitud if longitud >= 0 else None
    return None


class Seguridad:
    """Rechaza cuerpos demasiado grandes sin leerlos y añade las cabeceras de seguridad.

    - Con `Content-Length` mayor que el tope responde 413 sin leer nada del cuerpo.
    - Sin `Content-Length` (o con uno falso) cuenta los bytes según llegan y corta en
      cuanto se supera el tope: responde 413 y deja de leer.
    """

    def __init__(self, app: ASGIApp, max_mb: int):
        self.app = app
        self.max_mb = max_mb
        self.limite = max_mb * MB + MARGEN_CUERPO

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        cabeceras = _cabeceras_de_seguridad(scope["path"])
        cortado = False
        recibidos = 0

        async def enviar(mensaje: Message) -> None:
            if mensaje["type"] == "http.response.start":
                mensaje.setdefault("headers", [])
                destino = MutableHeaders(scope=mensaje)
                for nombre, valor in cabeceras.items():
                    destino[nombre] = valor
            await send(mensaje)

        async def enviar_app(mensaje: Message) -> None:
            if not cortado:  # tras el 413 se ignora lo que intente enviar la aplicación
                await enviar(mensaje)

        async def responder_413(tamano_bytes: int | None) -> None:
            respuesta = respuesta_error(archivo_demasiado_grande(self.max_mb, tamano_bytes))
            respuesta.headers["Connection"] = "close"
            await respuesta(scope, receive, enviar)

        async def recibir() -> Message:
            nonlocal cortado, recibidos
            if cortado:
                return {"type": "http.disconnect"}
            mensaje = await receive()
            if mensaje["type"] == "http.request":
                recibidos += len(mensaje.get("body", b""))
                if recibidos > self.limite:
                    cortado = True
                    await responder_413(None)
                    return {"type": "http.disconnect"}
            return mensaje

        longitud = _content_length(scope)
        if longitud is not None and longitud > self.limite:
            await responder_413(longitud)
            return

        try:
            await self.app(scope, recibir, enviar_app)
        except Exception:
            if not cortado:
                raise
