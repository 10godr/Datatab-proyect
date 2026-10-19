"""Configuración leída de variables de entorno DATATAB_*."""

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

# backend/app/config.py -> raíz del repositorio
RAIZ = Path(__file__).resolve().parents[2]

MB = 1024 * 1024


@dataclass(frozen=True)
class Configuracion:
    max_mb: int = 5
    ttl_min: int = 30
    host: str = "127.0.0.1"
    port: int = 8000
    max_filas: int = 100_000
    max_columnas: int = 200
    max_celdas: int = 2_000_000
    max_descomprimido_mb: int = 200
    max_valores_distintos: int = 1000
    max_datasets: int = 10
    servir_frontend: bool = True
    docs: bool = True

    @property
    def max_bytes(self) -> int:
        return self.max_mb * MB

    @property
    def max_descomprimido_bytes(self) -> int:
        return self.max_descomprimido_mb * MB

    @property
    def ttl_segundos(self) -> int:
        return self.ttl_min * 60


def _entero(env: Mapping[str, str], nombre: str, defecto: int) -> int:
    texto = env.get(f"DATATAB_{nombre}", "").strip()
    if not texto:
        return defecto
    try:
        valor = int(texto)
    except ValueError:
        raise ValueError(f"DATATAB_{nombre} debe ser un número entero.") from None
    if valor < 1:
        raise ValueError(f"DATATAB_{nombre} debe ser mayor que cero.")
    return valor


def _booleano(env: Mapping[str, str], nombre: str, defecto: bool) -> bool:
    texto = env.get(f"DATATAB_{nombre}", "").strip().lower()
    if not texto:
        return defecto
    if texto in ("1", "true", "si", "sí", "yes", "on"):
        return True
    if texto in ("0", "false", "no", "off"):
        return False
    raise ValueError(f"DATATAB_{nombre} debe ser 1 o 0.")


def cargar_configuracion(env: Mapping[str, str] | None = None) -> Configuracion:
    """Lee la configuración; las variables ausentes usan el valor por defecto."""
    env = os.environ if env is None else env
    base = Configuracion()
    return Configuracion(
        max_mb=_entero(env, "MAX_MB", base.max_mb),
        ttl_min=_entero(env, "TTL_MIN", base.ttl_min),
        host=env.get("DATATAB_HOST", "").strip() or base.host,
        port=_entero(env, "PORT", base.port),
        max_filas=_entero(env, "MAX_FILAS", base.max_filas),
        max_columnas=_entero(env, "MAX_COLUMNAS", base.max_columnas),
        max_celdas=_entero(env, "MAX_CELDAS", base.max_celdas),
        max_descomprimido_mb=_entero(env, "MAX_DESCOMPRIMIDO_MB", base.max_descomprimido_mb),
        max_valores_distintos=_entero(env, "MAX_VALORES_DISTINTOS", base.max_valores_distintos),
        max_datasets=_entero(env, "MAX_DATASETS", base.max_datasets),
        servir_frontend=_booleano(env, "SERVIR_FRONTEND", base.servir_frontend),
        docs=_booleano(env, "DOCS", base.docs),
    )
