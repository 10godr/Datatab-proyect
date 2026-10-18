#!/usr/bin/env python
"""Genera los archivos "golden" de la prueba de caracterización con el código de la v3.

Qué hace
--------
Toma unos conjuntos de datos ficticios y deterministas (semilla fija), los escribe como
.xlsx/.csv, los lee con el código ORIGINAL de la v3 (`excel_service.read_file`) y guarda en
`golden/*.json` los datos de entrada y lo que la v3 calculó con ellos: frecuencias, frecuencias
con rangos y tablas cruzadas. `tests/test_caracterizacion.py` rehace los mismos archivos en
memoria, los pasa por la API nueva y comprueba que los números coinciden con la v3.

De dónde sale el código de la v3
--------------------------------
La v3 es el estado del repositorio en el tag git `v3-antes-del-rediseno`. Para usarla sin tocar
el árbol de trabajo:

    git worktree add ../datatab-v3 v3-antes-del-rediseno
    cd backend
    python tests/fixtures/generar_golden.py --legacy-dir ../../datatab-v3

`--legacy-dir` es la carpeta que contiene `app/services/stats_service.py` y
`app/services/excel_service.py` (también se puede dar con la variable DATATAB_LEGACY_DIR).
Los módulos se cargan por ruta, con importlib, para que no choquen con el paquete `app` actual.
Con `--verificar` no se escribe nada: se vuelve a calcular y se comprueba que los archivos
guardados siguen siendo exactamente lo que da la v3.

Los archivos golden están versionados: solo hace falta volver a generarlos si se cambian los
conjuntos de datos o los casos de este script (el resultado es byte a byte reproducible con la
misma versión de pandas).

Diferencias INTENCIONADAS entre la v3 y la versión 4 (la prueba las comprueba una a una)
----------------------------------------------------------------------------------------
1. Orden. v3 ordena siempre por frecuencia descendente. v4: columnas numéricas y fechas de menor
   a mayor; texto por frecuencia descendente y, en empate, alfabético sin tildes ni mayúsculas.
   Las tablas cruzadas ordenan los ejes de forma natural (v3: orden de `pd.crosstab`).
2. Etiquetas numéricas. v3 escribe "30.0" cuando la columna tiene celdas vacías (pandas la
   convierte a decimales); v4 escribe "30". La prueba normaliza "30.0" a "30" antes de comparar.
3. Espacios. v4 quita los espacios de los extremos y reduce los internos a uno: "Femenino " y
   "Femenino" son un solo valor (v3 los cuenta aparte). Un texto de solo espacios es un valor
   vacío en v4 (v3 lo cuenta como categoría " ").
4. Fechas. v3: "2024-03-05 00:00:00". v4: "2024-03-05" (con hora solo si la tiene).
5. Booleanos. v3: "True"/"False". v4: "Verdadero"/"Falso".
6. Columna numérica con unos pocos textos ("N/D"). v3 la trata como texto (ignora los rangos y
   cuenta cada valor). v4 la considera numérica si al menos el 90 % de los valores lo son, agrupa
   en rangos y añade la fila "Sin valor numérico".
7. Rangos. v3 ignora en silencio un rango que no entiende (frecuencia 0). v4 responde 422
   RANGO_NO_VALIDO. v4 añade las filas "Fuera de los rangos" y "Sin valor numérico", que v3 no
   tiene, y admite `<=`, `≤`, negativos y coma decimal. La base de los porcentajes (valores no
   vacíos) es la misma.
8. Tablas cruzadas con rangos: v3 no las tiene. La prueba usa como referencia las frecuencias con
   rangos de v3 calculadas sobre cada subconjunto (las filas de cada valor de la otra variable).
9. Cabeceras. v4 recorta los espacios de los nombres de columna y numera las repetidas.
10. CSV. v3 solo entendía UTF-8 con coma como separador y punto decimal. v4 detecta además `;` y
    tabulador, Windows-1252 y la coma decimal ("1,5"). Con el formato que v3 sí entendía los
    resultados son los mismos (la prueba sube cada golden también como CSV).
11. Errores. v3: `{"error": "..."}` con 400. v4: `{"error": {"codigo", "mensaje", ...}}`.
"""

import argparse
import csv
import importlib.util
import io
import json
import os
import random
import re
import sys
import tempfile
from collections.abc import Callable, Sequence
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import openpyxl
import pandas as pd

AQUI = Path(__file__).resolve().parent
GOLDEN = AQUI / "golden"
TAG_V3 = "v3-antes-del-rediseno"


# --- Escritura de los archivos de entrada (la usa también la prueba) -----------------------------------------------


def _celda(valor: Any, fecha: bool) -> Any:
    if fecha and isinstance(valor, str):
        return datetime.fromisoformat(valor)
    return valor


def filas_a_xlsx(dataset: dict[str, Any], destino: Path | Any) -> None:
    """Escribe el dataset del golden como .xlsx (números como números, fechas como fechas)."""
    libro = openpyxl.Workbook()
    hoja = libro.active
    hoja.title = "Datos"
    hoja.append(dataset["columnas"])
    columnas_fecha = [i for i, nombre in enumerate(dataset["columnas"]) if nombre in dataset.get("fechas", [])]
    for fila in dataset["filas"]:
        hoja.append([_celda(v, i in columnas_fecha) for i, v in enumerate(fila)])
    libro.save(destino)


def filas_a_csv(dataset: dict[str, Any], destino: Path | Any) -> None:
    """Escribe el dataset del golden como CSV UTF-8 con coma (vacío = campo vacío)."""
    salida = io.StringIO()
    escritor = csv.writer(salida, lineterminator="\n")
    escritor.writerow(dataset["columnas"])
    for fila in dataset["filas"]:
        escritor.writerow(["" if valor is None else valor for valor in fila])
    contenido = salida.getvalue().encode("utf-8")
    if isinstance(destino, Path):
        destino.write_bytes(contenido)
    else:
        destino.write(contenido)


# --- Conjuntos de datos ficticios -----------------------------------------------------------------------------------


def _con_vacios(valores: list[Any], cuantos: int, azar: random.Random) -> list[Any]:
    for posicion in azar.sample(range(len(valores)), cuantos):
        valores[posicion] = None
    return valores


def _repartir(cantidades: dict[str, int], azar: random.Random) -> list[str]:
    valores = [valor for valor, veces in cantidades.items() for _ in range(veces)]
    azar.shuffle(valores)
    return valores


def dataset_clinica() -> dict[str, Any]:
    azar = random.Random(20240601)
    n = 240
    edad = [int(min(95, max(1, round(azar.gauss(48, 22))))) for _ in range(n)]
    peso = [round(min(160.0, max(3.0, azar.gauss(72, 14))), 1) for _ in range(n)]
    sexo = [azar.choices(["Femenino", "Masculino"], weights=[55, 45])[0] for _ in range(n)]
    # Dos servicios con 30 casos cada uno: un empate que fija el orden alfabético de v4
    servicio = _repartir({"Urgencias": 80, "Consulta externa": 60, "Cirugía": 40, "Pediatría": 30, "Hospitalización": 30}, azar)
    diagnostico = [azar.choices(["HTA", "Diabetes", "Asma", "EPOC", "Migraña", "Otro"], weights=[30, 22, 18, 12, 10, 8])[0] for _ in range(n)]
    hijos = [azar.randint(0, 6) for _ in range(n)]
    filas = [
        [i + 1, edad[i], sexo[i], servicio[i], peso[i], hijos[i], diagnostico[i]] for i in range(n)
    ]
    for columna, cuantos in ((1, 7), (4, 5)):  # Edad y Peso con celdas vacías: pandas las convierte a decimales
        valores = _con_vacios([f[columna] for f in filas], cuantos, azar)
        for fila, valor in zip(filas, valores, strict=True):
            fila[columna] = valor
    return {
        "nombre": "clinica",
        "descripcion": "240 pacientes ficticios: Edad y Peso con vacíos, texto con empate, enteros sin vacíos.",
        "columnas": ["Id", "Edad", "Sexo", "Servicio", "Peso", "Hijos", "Diagnostico"],
        "filas": filas,
    }


def dataset_encuesta() -> dict[str, Any]:
    azar = random.Random(20240602)
    n = 150
    respuesta = _repartir(
        {"Muy de acuerdo": 40, "De acuerdo": 35, "Neutral": 30, "En desacuerdo": 25, "Muy en desacuerdo": 20}, azar
    )
    grupo = [azar.choice(["A", "B", "C"]) for _ in range(n)]
    turno = [azar.choice(["Mañana", "Tarde"]) for _ in range(n)]
    puntaje = [azar.randint(1, 10) for _ in range(n)]
    filas = [[respuesta[i], grupo[i], turno[i], puntaje[i]] for i in range(n)]
    valores = _con_vacios([f[3] for f in filas], 9, azar)
    for fila, valor in zip(filas, valores, strict=True):
        fila[3] = valor
    return {
        "nombre": "encuesta",
        "descripcion": "150 respuestas ficticias: texto con tildes y ñ, escala 1 a 10 con vacíos.",
        "columnas": ["Respuesta", "Grupo", "Turno", "Puntaje"],
        "filas": filas,
    }


def dataset_sucio() -> dict[str, Any]:
    """Datos con los problemas de captura que v4 trata distinto de v3."""
    azar = random.Random(20240603)
    sexos = ["Femenino"] * 12 + ["Femenino "] * 3 + [" Femenino"] * 2 + ["Masculino"] * 14 + ["masculino"] * 3 + ["Masculino  "] * 2 + ["  "] * 2 + [None] * 2
    azar.shuffle(sexos)
    n = len(sexos)
    edades: list[Any] = [azar.randint(5, 90) for _ in range(n)]
    edades[3] = edades[17] = "N/D"
    edades[29] = None
    inicio = datetime(2024, 3, 1)
    fechas = [(inicio + timedelta(days=azar.randint(0, 6))).isoformat(timespec="seconds") for _ in range(n)]
    activo = [azar.choice([True, False]) for _ in range(n)]
    return {
        "nombre": "sucio",
        "descripcion": "Espacios, mayúsculas, un 'N/D' en una columna numérica, fechas y booleanos.",
        "columnas": ["Sexo", "Edad", "Fecha", "Activo"],
        "fechas": ["Fecha"],
        "filas": [[sexos[i], edades[i], fechas[i], activo[i]] for i in range(n)],
    }


# --- Casos que se calculan con la v3 -------------------------------------------------------------------------------

EDAD_PARTICION = ["<18", "18-39", "40-64", "65+"]

CASOS = {
    "clinica": {
        "frecuencias": [
            ("Sexo", None),
            ("Servicio", None),
            ("Diagnostico", None),
            ("Hijos", None),
            ("Edad", None),
            ("Peso", None),
            ("Edad", EDAD_PARTICION),
            ("Edad", ["<30", ">=60"]),  # hueco en medio: quedan valores fuera de los rangos
            ("Edad", ["<=40"]),  # v3 no entiende "<=": se omite en la comparación
            ("Edad", ["30-39", "40+", ">80"]),  # 40+ y >80 se solapan
            ("Edad", ["＜30", "30–39", "≥60"]),  # símbolos tipográficos
            ("Edad", [">=65", "<65"]),
            ("Edad", [" 18 - 39 ", ">18"]),  # espacios alrededor
            ("Peso", ["<50", "50-69.5", "70-89.5", "90+"]),
            ("Hijos", ["<1", "1-2", "3+"]),
        ],
        "cruces": [
            ("Sexo", "Servicio"),
            ("Servicio", "Sexo"),
            ("Edad", "Sexo"),
            ("Diagnostico", "Servicio"),
            ("Hijos", "Sexo"),
            ("Servicio", "Hijos"),
        ],
        # (eje con rangos, columna numérica, rangos, otra columna de texto)
        "cruces_con_rangos": [
            ("fila", "Edad", EDAD_PARTICION, "Sexo"),
            ("columna", "Edad", ["<30", "30-59", "60+"], "Sexo"),
            ("fila", "Edad", ["<18", "18-39", "40-64", "65+"], "Servicio"),
            ("fila", "Peso", ["<60", "60-79.9", "80+"], "Sexo"),
            ("columna", "Hijos", ["<1", "1-3", "4+"], "Diagnostico"),
        ],
    },
    "encuesta": {
        "frecuencias": [
            ("Respuesta", None),
            ("Grupo", None),
            ("Turno", None),
            ("Puntaje", None),
            ("Puntaje", ["1-3", "4-7", "8-10"]),
            ("Puntaje", ["<5", ">=5"]),
            ("Puntaje", ["3-6", "5-8"]),  # solape
        ],
        "cruces": [("Respuesta", "Grupo"), ("Grupo", "Turno"), ("Puntaje", "Respuesta"), ("Turno", "Respuesta")],
        "cruces_con_rangos": [("fila", "Puntaje", ["1-3", "4-7", "8-10"], "Respuesta"), ("columna", "Puntaje", ["<4", "4+"], "Grupo")],
    },
}

RANGOS_SUCIO_EDAD = ["<18", "18-39", "40-64", "65+"]


# --- Carga de la v3 ----------------------------------------------------------------------------------------------


def cargar_v3(directorio: Path):
    sys.dont_write_bytecode = True  # no dejar archivos .pyc dentro de la carpeta de la v3
    def cargar(nombre: str, ruta: Path):
        especificacion = importlib.util.spec_from_file_location(nombre, ruta)
        modulo = importlib.util.module_from_spec(especificacion)
        especificacion.loader.exec_module(modulo)
        return modulo

    servicios = directorio / "app" / "services"
    for archivo in ("stats_service.py", "excel_service.py"):
        if not (servicios / archivo).is_file():
            raise SystemExit(f"No encuentro {servicios / archivo}. Revisa --legacy-dir (tag git {TAG_V3}).")
    return cargar("v3_stats_service", servicios / "stats_service.py"), cargar("v3_excel_service", servicios / "excel_service.py")


def nativo(valor: Any) -> Any:
    """Convierte lo que devuelve pandas/numpy a tipos de JSON."""
    if isinstance(valor, dict):
        return {str(k): nativo(v) for k, v in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [nativo(v) for v in valor]
    if hasattr(valor, "item"):
        return nativo(valor.item())
    if isinstance(valor, float) and valor != valor:
        return None
    return valor


def _leer_v3(excel, dataset: dict[str, Any], carpeta: Path, formato: str) -> pd.DataFrame:
    ruta = carpeta / f"{dataset['nombre']}.{formato}"
    (filas_a_xlsx if formato == "xlsx" else filas_a_csv)(dataset, ruta)
    return excel.read_file(str(ruta))


def _es_numerica(df: pd.DataFrame, columna: str) -> bool:
    return bool(pd.api.types.is_numeric_dtype(df[columna].dropna()))


def _frecuencias_v3(stats, df: pd.DataFrame, columna: str, rangos: list[str] | None) -> dict[str, Any]:
    """Igual que la ruta /api/analizar de la v3: los rangos solo se aplican a columnas numéricas."""
    if rangos and _es_numerica(df, columna):
        return stats.calcular_frecuencias_con_rangos(df, columna, rangos)
    return stats.calcular_frecuencias(df, columna)


def calcular_golden(nombre: str, dataset: dict[str, Any], stats, excel, carpeta: Path) -> dict[str, Any]:
    df = _leer_v3(excel, dataset, carpeta, "xlsx")
    if nombre in CASOS:
        # El CSV debe dar lo mismo que el xlsx: la prueba usa los dos formatos con la misma referencia
        df_csv = _leer_v3(excel, dataset, carpeta, "csv")
        pd.testing.assert_frame_equal(df, df_csv, check_dtype=True)
    resultado: dict[str, Any] = {
        "version_v3": TAG_V3,
        "pandas": pd.__version__,
        "dataset": dataset,
    }
    if nombre == "sucio":
        resultado["casos"] = _casos_sucio(stats, df)
        return resultado

    casos = CASOS[nombre]
    resultado["frecuencias"] = [
        {"columna": c, "rangos": r, "v3": nativo(_frecuencias_v3(stats, df, c, r))} for c, r in casos["frecuencias"]
    ]
    resultado["cruces"] = [
        {"fila": f, "columna": c, "v3": nativo(stats.calcular_tabla_cruzada(df, f, c))} for f, c in casos["cruces"]
    ]
    resultado["cruces_con_rangos"] = [
        _cruce_con_rangos(stats, df, eje, columna, rangos, otra) for eje, columna, rangos, otra in casos["cruces_con_rangos"]
    ]
    return resultado


def _cruce_con_rangos(stats, df: pd.DataFrame, eje: str, columna: str, rangos: list[str], otra: str) -> dict[str, Any]:
    """Referencia de v3 para un cruce con rangos: las frecuencias con rangos de cada subconjunto.

    La celda (rango i, valor v de `otra`) es cuántos registros con `otra == v` caen en el rango i,
    que es justo lo que cuenta `calcular_frecuencias_con_rangos` sobre ese subconjunto.
    """
    por_categoria = {}
    for categoria in sorted(df[otra].dropna().unique(), key=str):
        subconjunto = df[df[otra] == categoria]
        por_categoria[str(categoria)] = nativo(stats.calcular_frecuencias_con_rangos(subconjunto, columna, rangos))
    return {"eje_con_rangos": eje, "columna_numerica": columna, "rangos": rangos, "otra_columna": otra, "v3_por_categoria": por_categoria}


def _casos_sucio(stats, df: pd.DataFrame) -> dict[str, Any]:
    edad_numerica = df.assign(Edad=pd.to_numeric(df["Edad"], errors="coerce"))
    return {
        "sexo": nativo(stats.calcular_frecuencias(df, "Sexo")),
        "edad_sin_rangos": nativo(stats.calcular_frecuencias(df, "Edad")),
        "edad_es_numerica_para_v3": _es_numerica(df, "Edad"),
        "edad_rangos": RANGOS_SUCIO_EDAD,
        # v3 ignoraría los rangos (la columna tiene texto): como referencia se aplica su cálculo a los números
        "edad_con_rangos_solo_numeros": nativo(stats.calcular_frecuencias_con_rangos(edad_numerica, "Edad", RANGOS_SUCIO_EDAD)),
        "fecha": nativo(stats.calcular_frecuencias(df, "Fecha")),
        "activo": nativo(stats.calcular_frecuencias(df, "Activo")),
        "rango_que_v3_no_entiende": nativo(stats.calcular_frecuencias_con_rangos(edad_numerica, "Edad", ["<18", "mayores de 60"])),
    }


# --- Salida JSON legible y reproducible -----------------------------------------------------------------------------

_ESCALAR = r'(?:"(?:[^"\\]|\\.)*"|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?|true|false|null)'
_LISTA_DE_ESCALARES = re.compile(r"\[\s*(" + _ESCALAR + r"(?:\s*,\s*" + _ESCALAR + r")*)\s*\]")


def a_json(objeto: Any) -> str:
    """JSON con sangría, pero con cada lista de valores simples (una fila de datos) en una sola línea."""
    texto = json.dumps(objeto, ensure_ascii=False, indent=1)
    return _LISTA_DE_ESCALARES.sub(lambda m: "[" + re.sub(r"\s*,\s*", ", ", m.group(1)) + "]", texto) + "\n"


def datasets() -> dict[str, Callable[[], dict[str, Any]]]:
    return {"clinica": dataset_clinica, "encuesta": dataset_encuesta, "sucio": dataset_sucio}


def main(argumentos: Sequence[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description="Genera tests/fixtures/golden/*.json con el código de la v3.")
    analizador.add_argument(
        "--legacy-dir",
        default=os.environ.get("DATATAB_LEGACY_DIR"),
        help=f"Carpeta con el código de la v3 (tag git {TAG_V3}): la que contiene app/services/stats_service.py.",
    )
    analizador.add_argument("--verificar", action="store_true", help="No escribe: comprueba que los golden guardados coinciden con la v3.")
    opciones = analizador.parse_args(argumentos)
    if not opciones.legacy_dir:
        analizador.error(f"falta --legacy-dir (o DATATAB_LEGACY_DIR). Ver el docstring: git worktree add ../datatab-v3 {TAG_V3}")

    stats, excel = cargar_v3(Path(opciones.legacy_dir).resolve())
    GOLDEN.mkdir(exist_ok=True)
    distintos = []
    with tempfile.TemporaryDirectory() as temporal:
        for nombre, construir in datasets().items():
            texto = a_json(calcular_golden(nombre, construir(), stats, excel, Path(temporal)))
            destino = GOLDEN / f"{nombre}.json"
            if opciones.verificar:
                if not destino.is_file() or destino.read_text(encoding="utf-8") != texto:
                    distintos.append(destino.name)
            else:
                destino.write_text(texto, encoding="utf-8", newline="\n")
                print(f"escrito {destino.relative_to(AQUI.parent.parent)} ({len(texto) // 1024 + 1} KB)")
    if opciones.verificar:
        if distintos:
            print("Distintos de lo que da la v3 ahora:", ", ".join(distintos))
            return 1
        print("Los golden coinciden con la v3.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
