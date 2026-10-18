"""Caracterización: la API nueva da los mismos números que la v3 (tag git `v3-antes-del-rediseno`).

Los archivos `fixtures/golden/*.json` guardan unos datos ficticios y lo que la v3 calculó con
ellos (frecuencias, frecuencias con rangos y tablas cruzadas). Aquí se rehace cada archivo en
memoria (.xlsx y .csv), se sube a la API nueva y se compara. Para regenerar los golden, ver
`fixtures/generar_golden.py`.

Se compara el CONTENIDO (qué cuenta cada valor y qué porcentaje le toca), no el orden de las
filas ni la forma de la respuesta, porque eso cambió a propósito. Diferencias intencionadas
que esta prueba da por buenas (cada una tiene su comprobación explícita más abajo):

 1. Orden: v3 ordena por frecuencia; v4, numérico/fecha de menor a mayor, texto por frecuencia y
    desempate alfabético, y los ejes de los cruces en orden natural.
 2. Etiquetas numéricas: v3 "30.0" (columna con vacíos), v4 "30". Se normaliza antes de comparar.
 3. Espacios: v4 los recorta y los junta; un texto de solo espacios es un valor vacío.
 4. Fechas: v3 "2024-03-05 00:00:00", v4 "2024-03-05".
 5. Booleanos: v3 "True"/"False", v4 "Verdadero"/"Falso".
 6. Columna numérica con pocos textos ("N/D"): v3 la trata como texto, v4 como numérica con la
    fila "Sin valor numérico".
 7. Rango que no se entiende: v3 lo ignora (0), v4 responde 422. v4 añade "Fuera de los rangos"
    y admite `<=`, que v3 no entendía.
 8. Cruces con rangos: no existen en v3; se contrastan con las frecuencias con rangos de v3
    calculadas sobre cada subconjunto.
 9. Errores: v3 `{"error": "texto"}`, v4 `{"error": {"codigo": ...}}`.
"""

import io
import json
import re
import unicodedata
from pathlib import Path

import pytest

from fixtures.generar_golden import TAG_V3, filas_a_csv, filas_a_xlsx

GOLDEN = Path(__file__).parent / "fixtures" / "golden"
NOMBRES = ["clinica", "encuesta"]
FORMATOS = ["xlsx", "csv"]


def cargar(nombre: str) -> dict:
    return json.loads((GOLDEN / f"{nombre}.json").read_text(encoding="utf-8"))


DATOS = {nombre: cargar(nombre) for nombre in [*NOMBRES, "sucio"]}


def casos(clave: str):
    """Un caso de prueba por cada entrada del golden: (dataset, formato, índice)."""
    return [
        pytest.param(nombre, formato, i, id=f"{nombre}-{formato}-{i}")
        for nombre in NOMBRES
        for formato in FORMATOS
        for i in range(len(DATOS[nombre][clave]))
    ]


# --- Apoyo ----------------------------------------------------------------------------------------------------------


def subir_golden(cliente, nombre: str, formato: str):
    dataset = DATOS[nombre]["dataset"]
    contenido = io.BytesIO()
    (filas_a_xlsx if formato == "xlsx" else filas_a_csv)(dataset, contenido)
    respuesta = cliente.post("/api/datasets", files={"archivo": (f"{nombre}.{formato}", contenido.getvalue(), "application/octet-stream")})
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def tipos(subida: dict) -> dict[str, str]:
    return {c["nombre"]: c["tipo"] for c in subida["columnas"]}


def etiqueta_v3(valor: str, numerica: bool) -> str:
    """v3 escribe '30.0' para los números de una columna con vacíos: v4 escribe '30'."""
    return valor[:-2] if numerica and re.fullmatch(r"-?\d+\.0", valor) else valor


def sin_tildes(texto: str) -> str:
    return unicodedata.normalize("NFD", texto).encode("ascii", "ignore").decode().casefold()


def valores_de(nombre: str, columna: str) -> list:
    """Valores no vacíos de una columna del golden, tal como se escribieron en el archivo."""
    dataset = DATOS[nombre]["dataset"]
    posicion = dataset["columnas"].index(columna)
    return [fila[posicion] for fila in dataset["filas"] if fila[posicion] is not None]


def pertenece(valor: float, rango: str) -> bool:
    """Qué significa cada rango, escrito aparte del código de la app (sintaxis de v3 más `<=`)."""
    texto = rango.strip().replace("＜", "<").replace("≥", ">=").replace("≤", "<=").replace("–", "-")
    if m := re.fullmatch(r"<=\s*([\d.]+)", texto):
        return valor <= float(m[1])
    if m := re.fullmatch(r"<\s*([\d.]+)", texto):
        return valor < float(m[1])
    if m := re.fullmatch(r">=\s*([\d.]+)", texto):
        return valor >= float(m[1])
    if m := re.fullmatch(r">\s*([\d.]+)", texto):
        return valor > float(m[1])
    if m := re.fullmatch(r"([\d.]+)\s*\+", texto):
        return valor >= float(m[1])
    if m := re.fullmatch(r"([\d.]+)\s*-\s*([\d.]+)", texto):
        return float(m[1]) <= valor <= float(m[2])
    raise AssertionError(f"rango de prueba no previsto: {rango}")


# --- Metadatos del golden ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize("nombre", [*NOMBRES, "sucio"])
def test_los_golden_vienen_de_la_v3(nombre):
    assert DATOS[nombre]["version_v3"] == TAG_V3 == "v3-antes-del-rediseno"
    assert DATOS[nombre]["dataset"]["filas"]


@pytest.mark.parametrize("nombre", NOMBRES)
@pytest.mark.parametrize("formato", FORMATOS)
def test_el_archivo_rehecho_se_lee_con_las_dimensiones_del_golden(cliente, nombre, formato):
    subida = subir_golden(cliente, nombre, formato)
    dataset = DATOS[nombre]["dataset"]
    assert subida["filas"] == len(dataset["filas"])
    assert [c["nombre"] for c in subida["columnas"]] == dataset["columnas"]
    assert subida["avisos"] == []


# --- Frecuencias ----------------------------------------------------------------------------------------------------


SIN_RANGOS = [p for p in casos("frecuencias") if DATOS[p.values[0]]["frecuencias"][p.values[2]]["rangos"] is None]
CON_RANGOS = [p for p in casos("frecuencias") if DATOS[p.values[0]]["frecuencias"][p.values[2]]["rangos"] is not None]


@pytest.mark.parametrize(("nombre", "formato", "indice"), SIN_RANGOS)
def test_frecuencias_sin_rangos_coinciden_con_v3(cliente, nombre, formato, indice):
    caso = DATOS[nombre]["frecuencias"][indice]
    v3 = caso["v3"]
    subida = subir_golden(cliente, nombre, formato)
    respuesta = cliente.post(f"/api/datasets/{subida['dataset_id']}/frecuencias", json={"columna": caso["columna"]})
    assert respuesta.status_code == 200, respuesta.text
    nueva = respuesta.json()

    numerica = nueva["tipo"] == "numerica"
    assert numerica == v3["es_numerica"]
    esperado = {etiqueta_v3(f["valor"], numerica): (f["frecuencia"], f["porcentaje"]) for f in v3["frecuencias"]}
    obtenido = {f["etiqueta"]: (f["frecuencia"], f["porcentaje"]) for f in nueva["filas"]}
    assert obtenido == esperado
    assert len(nueva["filas"]) == len(esperado)  # ninguna etiqueta repetida
    assert nueva["n"] == v3["total"]
    assert nueva["vacios_excluidos"] == subida["filas"] - v3["total"]
    assert nueva["agrupado"] is False and nueva["solapados"] == 0 and nueva["avisos"] == []


@pytest.mark.parametrize(("nombre", "formato", "indice"), SIN_RANGOS)
def test_frecuencias_sin_rangos_siguen_el_orden_nuevo(cliente, nombre, formato, indice):
    caso = DATOS[nombre]["frecuencias"][indice]
    subida = subir_golden(cliente, nombre, formato)
    nueva = cliente.post(f"/api/datasets/{subida['dataset_id']}/frecuencias", json={"columna": caso["columna"]}).json()
    etiquetas = [f["etiqueta"] for f in nueva["filas"]]
    if nueva["tipo"] == "numerica":
        assert etiquetas == sorted(etiquetas, key=float)
    else:
        frecuencia = {f["etiqueta"]: f["frecuencia"] for f in nueva["filas"]}
        assert etiquetas == sorted(etiquetas, key=lambda e: (-frecuencia[e], sin_tildes(e), e))


@pytest.mark.parametrize(("nombre", "formato", "indice"), CON_RANGOS)
def test_frecuencias_con_rangos_coinciden_con_v3(cliente, nombre, formato, indice):
    caso = DATOS[nombre]["frecuencias"][indice]
    v3, rangos, columna = caso["v3"], caso["rangos"], caso["columna"]
    subida = subir_golden(cliente, nombre, formato)
    respuesta = cliente.post(f"/api/datasets/{subida['dataset_id']}/frecuencias", json={"columna": columna, "rangos": rangos})
    assert respuesta.status_code == 200, respuesta.text
    nueva = respuesta.json()
    n = v3["total"]
    valores = valores_de(nombre, columna)

    assert nueva["n"] == n and nueva["agrupado"] is True and nueva["tipo"] == "numerica"
    por_rango = [f for f in nueva["filas"] if f["tipo"] == "rango"]
    assert [f["rango"] for f in por_rango] == [r.strip() for r in rangos]  # mismo orden que se enviaron
    assert [f["rango"] for f in por_rango] == [f["valor"] for f in v3["frecuencias"]]

    for fila, referencia, texto in zip(por_rango, v3["frecuencias"], rangos, strict=True):
        directo = sum(pertenece(v, texto) for v in valores)
        if re.match(r"\s*(<=|≤)", texto):  # v3 no entendía "<=": respondía 0 sin avisar
            assert referencia["frecuencia"] == 0
            assert fila["frecuencia"] == directo > 0
            esperado_pct = round(directo / n * 100, 2)
        else:
            assert fila["frecuencia"] == referencia["frecuencia"] == directo
            esperado_pct = referencia["porcentaje"]
        assert fila["porcentaje"] == esperado_pct

    # Lo que v3 no enseñaba: registros fuera de todos los rangos y registros en más de un rango
    en_alguno = sum(any(pertenece(v, t) for t in rangos) for v in valores)
    en_varios = sum(sum(pertenece(v, t) for t in rangos) > 1 for v in valores)
    fuera = [f for f in nueva["filas"] if f["tipo"] == "fuera_de_rango"]
    assert (fuera[0]["frecuencia"] if fuera else 0) == n - en_alguno
    assert len(fuera) == (1 if n - en_alguno else 0)
    assert nueva["solapados"] == en_varios
    assert any(a["codigo"] == "RANGOS_SOLAPADOS" for a in nueva["avisos"]) == bool(en_varios)
    assert not [f for f in nueva["filas"] if f["tipo"] == "sin_valor_numerico"]


# --- Tablas cruzadas -------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(("nombre", "formato", "indice"), casos("cruces"))
def test_tablas_cruzadas_coinciden_con_v3(cliente, nombre, formato, indice):
    caso = DATOS[nombre]["cruces"][indice]
    v3 = caso["v3"]
    subida = subir_golden(cliente, nombre, formato)
    columnas = tipos(subida)
    respuesta = cliente.post(
        f"/api/datasets/{subida['dataset_id']}/tabla-cruzada",
        json={"fila": {"columna": caso["fila"]}, "columna": {"columna": caso["columna"]}},
    )
    assert respuesta.status_code == 200, respuesta.text
    nueva = respuesta.json()
    num_fila, num_col = columnas[caso["fila"]] == "numerica", columnas[caso["columna"]] == "numerica"

    assert nueva["n"] == v3["total"]
    assert nueva["vacios_excluidos"] == subida["filas"] - v3["total"]
    etiquetas_col = [c["etiqueta"] for c in nueva["columnas"]]
    assert sorted(etiquetas_col) == sorted(etiqueta_v3(c, num_col) for c in v3["columnas"])

    esperado = {
        (etiqueta_v3(f["etiqueta"], num_fila), etiqueta_v3(c["columna"], num_col)): (c["frecuencia"], c["porcentaje"])
        for f in v3["filas"]
        for c in f["celdas"]
    }
    obtenido = {
        (f["etiqueta"], etiquetas_col[j]): (c["frecuencia"], c["porcentaje"]) for f in nueva["filas"] for j, c in enumerate(f["celdas"])
    }
    assert obtenido == esperado
    assert {f["etiqueta"]: f["total"] for f in nueva["filas"]} == {etiqueta_v3(f["etiqueta"], num_fila): f["total_fila"] for f in v3["filas"]}
    assert {etiquetas_col[j]: t["frecuencia"] for j, t in enumerate(nueva["totales_columna"])} == {
        etiqueta_v3(c, num_col): total for c, total in v3["totales_col"].items()
    }
    assert [t["porcentaje"] for t in nueva["totales_columna"]] == [round(t["frecuencia"] / nueva["n"] * 100, 1) for t in nueva["totales_columna"]]
    assert sum(f["total"] for f in nueva["filas"]) == nueva["n"] == sum(t["frecuencia"] for t in nueva["totales_columna"])
    assert nueva["avisos"] == [] and nueva["fila"]["agrupado"] is False and nueva["columna"]["agrupado"] is False


@pytest.mark.parametrize(("nombre", "formato", "indice"), casos("cruces"))
def test_los_ejes_de_la_tabla_cruzada_van_en_orden_natural(cliente, nombre, formato, indice):
    caso = DATOS[nombre]["cruces"][indice]
    subida = subir_golden(cliente, nombre, formato)
    columnas = tipos(subida)
    nueva = cliente.post(
        f"/api/datasets/{subida['dataset_id']}/tabla-cruzada",
        json={"fila": {"columna": caso["fila"]}, "columna": {"columna": caso["columna"]}},
    ).json()
    for etiquetas, columna in (([f["etiqueta"] for f in nueva["filas"]], caso["fila"]), ([c["etiqueta"] for c in nueva["columnas"]], caso["columna"])):
        if columnas[columna] == "numerica":
            assert etiquetas == sorted(etiquetas, key=float)
        else:
            assert etiquetas == sorted(etiquetas, key=lambda e: (sin_tildes(e), e))


@pytest.mark.parametrize(("nombre", "formato", "indice"), casos("cruces_con_rangos"))
def test_tablas_cruzadas_con_rangos_coinciden_con_las_frecuencias_con_rangos_de_v3(cliente, nombre, formato, indice):
    caso = DATOS[nombre]["cruces_con_rangos"][indice]
    rangos, otra, numerica = caso["rangos"], caso["otra_columna"], caso["columna_numerica"]
    en_fila = caso["eje_con_rangos"] == "fila"
    subida = subir_golden(cliente, nombre, formato)
    eje_rangos = {"columna": numerica, "rangos": rangos}
    cuerpo = {"fila": eje_rangos, "columna": {"columna": otra}} if en_fila else {"fila": {"columna": otra}, "columna": eje_rangos}
    respuesta = cliente.post(f"/api/datasets/{subida['dataset_id']}/tabla-cruzada", json=cuerpo)
    assert respuesta.status_code == 200, respuesta.text
    nueva = respuesta.json()

    por_categoria = caso["v3_por_categoria"]
    categorias_rangos = nueva["filas"] if en_fila else nueva["columnas"]
    categorias_otra = nueva["columnas"] if en_fila else nueva["filas"]
    assert sorted(c["etiqueta"] for c in categorias_otra) == sorted(por_categoria)
    assert [c["rango"] for c in categorias_rangos if c["tipo"] == "rango"] == [r.strip() for r in rangos]

    def celda(i_rango: int, categoria_otra: int) -> dict:
        fila = nueva["filas"][i_rango if en_fila else categoria_otra]
        return fila["celdas"][categoria_otra if en_fila else i_rango]

    n_esperado = 0
    for j, categoria in enumerate(categorias_otra):
        referencia = por_categoria[categoria["etiqueta"]]
        n_esperado += referencia["total"]
        suma_rangos = 0
        for i, fila_v3 in enumerate(referencia["frecuencias"]):
            assert categorias_rangos[i]["rango"] == fila_v3["valor"]
            assert celda(i, j)["frecuencia"] == fila_v3["frecuencia"], (categoria["etiqueta"], fila_v3["valor"])
            suma_rangos += fila_v3["frecuencia"]
        resto = referencia["total"] - suma_rangos  # registros de esta categoría que no entran en ningún rango
        indice_fuera = next((i for i, c in enumerate(categorias_rangos) if c["tipo"] == "fuera_de_rango"), None)
        assert (celda(indice_fuera, j)["frecuencia"] if indice_fuera is not None else 0) == resto

    assert nueva["n"] == n_esperado
    assert not [c for c in categorias_rangos if c["tipo"] == "sin_valor_numerico"]
    assert nueva["avisos"] == []
    assert sum(f["total"] for f in nueva["filas"]) == nueva["n"] == sum(t["frecuencia"] for t in nueva["totales_columna"])
    for fila in nueva["filas"]:  # porcentaje de cada celda sobre el total de su fila
        for c in fila["celdas"]:
            assert c["porcentaje"] == (round(c["frecuencia"] / fila["total"] * 100, 1) if fila["total"] else 0.0)
    assert nueva["fila" if en_fila else "columna"]["agrupado"] is True
    assert nueva["columna" if en_fila else "fila"]["agrupado"] is False


# --- Datos sucios: las diferencias intencionadas con v3 ---------------------------------------------------------------


@pytest.fixture
def sucio(cliente):
    subida = subir_golden(cliente, "sucio", "xlsx")
    return cliente, subida


def frecuencias(cliente, subida, columna, rangos=None):
    cuerpo = {"columna": columna} if rangos is None else {"columna": columna, "rangos": rangos}
    return cliente.post(f"/api/datasets/{subida['dataset_id']}/frecuencias", json=cuerpo)


def test_dif_3_los_espacios_se_recortan_y_los_textos_de_solo_espacios_son_vacios(sucio):
    cliente, subida = sucio
    v3 = DATOS["sucio"]["casos"]["sexo"]
    nueva = frecuencias(cliente, subida, "Sexo").json()

    juntos: dict[str, int] = {}
    for f in v3["frecuencias"]:
        etiqueta = " ".join(f["valor"].split())
        if etiqueta:  # "  " (solo espacios) era una categoría en v3
            juntos[etiqueta] = juntos.get(etiqueta, 0) + f["frecuencia"]
    assert len(v3["frecuencias"]) == 7 and len(juntos) == 3  # v3 los contaba aparte
    n = sum(juntos.values())
    assert {f["etiqueta"]: (f["frecuencia"], f["porcentaje"]) for f in nueva["filas"]} == {
        etiqueta: (cuenta, round(cuenta / n * 100, 2)) for etiqueta, cuenta in juntos.items()
    }
    assert nueva["n"] == n == v3["total"] - 2
    assert nueva["vacios_excluidos"] == subida["filas"] - n == 4  # 2 celdas vacías y 2 de solo espacios
    # Mayúsculas y minúsculas no se unen (como en v3), pero se avisa
    assert {"Masculino", "masculino"} <= {f["etiqueta"] for f in nueva["filas"]}
    assert [a["codigo"] for a in subida["avisos"]] == ["VALORES_PARECIDOS"]
    assert "«Masculino» y «masculino»" in subida["avisos"][0]["mensaje"]


def test_dif_6_una_columna_con_pocos_textos_es_numerica_y_agrupa_en_rangos(sucio):
    cliente, subida = sucio
    casos_v3 = DATOS["sucio"]["casos"]
    assert casos_v3["edad_es_numerica_para_v3"] is False  # v3 la trataba como texto y habría ignorado los rangos
    edad = next(c for c in subida["columnas"] if c["nombre"] == "Edad")
    assert (edad["tipo"], edad["no_numericos"], edad["vacios"]) == ("numerica", 2, 1)

    # Sin rangos: los mismos valores y recuentos que v3 (con "N/D" al final por ser texto en una columna numérica)
    sin = frecuencias(cliente, subida, "Edad").json()
    v3_sin = casos_v3["edad_sin_rangos"]
    assert {f["etiqueta"]: (f["frecuencia"], f["porcentaje"]) for f in sin["filas"]} == {
        f["valor"]: (f["frecuencia"], f["porcentaje"]) for f in v3_sin["frecuencias"]
    }
    assert sin["filas"][-1]["etiqueta"] == "N/D" and sin["n"] == v3_sin["total"] == 39

    # Con rangos: los recuentos son los de v3 sobre los números; el porcentaje es sobre los 39 valores
    con = frecuencias(cliente, subida, "Edad", casos_v3["edad_rangos"]).json()
    referencia = casos_v3["edad_con_rangos_solo_numeros"]
    assert referencia["total"] == 37
    assert [(f["rango"], f["frecuencia"]) for f in con["filas"] if f["tipo"] == "rango"] == [
        (f["valor"], f["frecuencia"]) for f in referencia["frecuencias"]
    ]
    sin_valor = [f for f in con["filas"] if f["tipo"] == "sin_valor_numerico"]
    assert [(f["etiqueta"], f["frecuencia"]) for f in sin_valor] == [("Sin valor numérico", 2)]
    assert con["n"] == 39 and sum(f["frecuencia"] for f in con["filas"]) == 39
    assert all(f["porcentaje"] == round(f["frecuencia"] / 39 * 100, 2) for f in con["filas"])
    assert [a["codigo"] for a in con["avisos"]] == ["VALORES_NO_NUMERICOS"]


def test_dif_4_las_fechas_salen_como_aaaa_mm_dd(sucio):
    cliente, subida = sucio
    v3 = DATOS["sucio"]["casos"]["fecha"]
    assert all(f["valor"].endswith(" 00:00:00") for f in v3["frecuencias"])
    nueva = frecuencias(cliente, subida, "Fecha").json()
    assert nueva["tipo"] == "fecha"
    assert {f["etiqueta"]: (f["frecuencia"], f["porcentaje"]) for f in nueva["filas"]} == {
        f["valor"][:10]: (f["frecuencia"], f["porcentaje"]) for f in v3["frecuencias"]
    }
    etiquetas = [f["etiqueta"] for f in nueva["filas"]]
    assert etiquetas == sorted(etiquetas) and all(re.fullmatch(r"\d{4}-\d{2}-\d{2}", e) for e in etiquetas)


def test_dif_5_los_booleanos_salen_como_verdadero_y_falso(sucio):
    cliente, subida = sucio
    v3 = DATOS["sucio"]["casos"]["activo"]
    assert {f["valor"] for f in v3["frecuencias"]} == {"True", "False"}
    nueva = frecuencias(cliente, subida, "Activo").json()
    traduccion = {"True": "Verdadero", "False": "Falso"}
    assert {f["etiqueta"]: (f["frecuencia"], f["porcentaje"]) for f in nueva["filas"]} == {
        traduccion[f["valor"]]: (f["frecuencia"], f["porcentaje"]) for f in v3["frecuencias"]
    }


def test_dif_7_un_rango_que_no_se_entiende_es_un_error_y_no_un_cero_silencioso(sucio):
    cliente, subida = sucio
    v3 = DATOS["sucio"]["casos"]["rango_que_v3_no_entiende"]
    assert v3["frecuencias"][1] == {"valor": "mayores de 60", "frecuencia": 0, "porcentaje": 0.0}
    respuesta = frecuencias(cliente, subida, "Edad", ["<18", "mayores de 60"])
    assert respuesta.status_code == 422
    error = respuesta.json()["error"]
    assert error["codigo"] == "RANGO_NO_VALIDO" and error["detalle"] == {"rango": "mayores de 60"}


def test_dif_9_la_forma_de_los_errores_cambia(cliente):
    respuesta = cliente.post("/api/datasets/no-existe/frecuencias", json={"columna": "Edad"})
    assert respuesta.status_code == 404
    error = respuesta.json()["error"]
    assert isinstance(error, dict) and error["codigo"] == "ARCHIVO_NO_ENCONTRADO"  # v3: {"error": "texto"} con 400


def test_dif_1_el_orden_ya_no_es_el_de_v3(cliente):
    # En la columna Edad (numérica) v3 ordenaba por frecuencia y v4 de menor a mayor
    v3 = next(c["v3"] for c in DATOS["clinica"]["frecuencias"] if c["columna"] == "Edad" and c["rangos"] is None)
    etiquetas_v3 = [float(f["valor"]) for f in v3["frecuencias"]]
    assert etiquetas_v3 != sorted(etiquetas_v3)
    subida = subir_golden(cliente, "clinica", "xlsx")
    nueva = frecuencias(cliente, subida, "Edad").json()
    etiquetas = [float(f["etiqueta"]) for f in nueva["filas"]]
    assert etiquetas == sorted(etiquetas)
    assert sorted(etiquetas_v3) == etiquetas  # mismos valores
