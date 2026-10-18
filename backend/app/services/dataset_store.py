"""Almacén en memoria de los archivos cargados. Nada se escribe en disco."""

import secrets
import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass, field

import pandas as pd

from ..errors import ErrorDataTab, recortar
from .columnas import PerfilColumna


@dataclass
class Dataset:
    id: str
    nombre: str
    formato: str
    tabla: pd.DataFrame
    perfiles: list[PerfilColumna]
    ultimo_uso: float = 0.0
    _por_nombre: dict[str, PerfilColumna] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._por_nombre = {perfil.nombre: perfil for perfil in self.perfiles}

    def columna(self, nombre: str) -> tuple[pd.Series, PerfilColumna]:
        perfil = self._por_nombre.get(nombre)
        if perfil is None:
            raise ErrorDataTab(
                "COLUMNA_NO_ENCONTRADA",
                f"La columna «{recortar(nombre)}» no existe en este archivo.",
                "Elige una de las columnas del archivo.",
                {"columna": recortar(nombre)},
            )
        return self.tabla[nombre], perfil


class AlmacenDatasets:
    """Guarda hasta `max_datasets` archivos. Cada uso renueva su plazo de `ttl_segundos`.

    El reloj se inyecta para poder probar la caducidad sin esperar.
    """

    def __init__(self, ttl_segundos: float, max_datasets: int, reloj: Callable[[], float] = time.monotonic):
        self.ttl_segundos = ttl_segundos
        self._max_datasets = max_datasets
        self._reloj = reloj
        self._datasets: OrderedDict[str, Dataset] = OrderedDict()  # del menos al más recientemente usado
        self._cerrojo = threading.Lock()

    def __len__(self) -> int:
        with self._cerrojo:
            return len(self._datasets)

    def guardar(self, nombre: str, formato: str, tabla: pd.DataFrame, perfiles: list[PerfilColumna]) -> Dataset:
        dataset = Dataset(secrets.token_urlsafe(16), nombre, formato, tabla, perfiles)
        with self._cerrojo:
            self._purgar()
            while len(self._datasets) >= self._max_datasets:
                self._datasets.popitem(last=False)  # el menos recientemente usado
            dataset.ultimo_uso = self._reloj()
            self._datasets[dataset.id] = dataset
        return dataset

    def obtener(self, dataset_id: str) -> Dataset:
        """Devuelve el archivo y renueva su plazo. Lanza ARCHIVO_NO_ENCONTRADO si no existe o caducó."""
        with self._cerrojo:
            dataset = self._datasets.get(dataset_id)
            if dataset is not None and self._caducado(dataset):
                del self._datasets[dataset_id]
                dataset = None
            if dataset is None:
                raise ErrorDataTab(
                    "ARCHIVO_NO_ENCONTRADO",
                    "El archivo ya no está disponible. Puede haber caducado por inactividad.",
                    "Vuelve a subirlo.",
                )
            dataset.ultimo_uso = self._reloj()
            self._datasets.move_to_end(dataset_id)
            return dataset

    def eliminar(self, dataset_id: str) -> None:
        with self._cerrojo:
            self._datasets.pop(dataset_id, None)

    def purgar_caducados(self) -> int:
        with self._cerrojo:
            return self._purgar()

    def vaciar(self) -> None:
        with self._cerrojo:
            self._datasets.clear()

    def _caducado(self, dataset: Dataset) -> bool:
        return self._reloj() - dataset.ultimo_uso >= self.ttl_segundos

    def _purgar(self) -> int:
        caducados = [i for i, d in self._datasets.items() if self._caducado(d)]
        for dataset_id in caducados:
            del self._datasets[dataset_id]
        return len(caducados)
