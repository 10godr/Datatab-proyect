import pytest

from app.errors import ErrorDataTab
from app.services.cruce import MAX_CELDAS, MAX_COLUMNAS, MAX_FILAS, calcular_tabla_cruzada
from ayudas import columna, leer_filas


def cruzar(filas, nombre_fila, nombre_columna, rangos_fila=None, rangos_columna=None):
    leida = leer_filas(filas)
    serie_f, perfil_f = columna(leida, nombre_fila)
    serie_c, perfil_c = columna(leida, nombre_columna)
    return calcular_tabla_cruzada(serie_f, perfil_f, rangos_fila, serie_c, perfil_c, rangos_columna)


def error_de(*args, **kwargs) -> ErrorDataTab:
    with pytest.raises(ErrorDataTab) as capturado:
        cruzar(*args, **kwargs)
    return capturado.value


def etiquetas(categorias) -> list[str]:
    return [c["etiqueta"] for c in categorias]


def comprobar_cuadre(resultado) -> None:
    """Cada registro cae en exactamente una fila y una columna."""
    n = resultado["n"]
    assert sum(f["total"] for f in resultado["filas"]) == n
    assert sum(t["frecuencia"] for t in resultado["totales_columna"]) == n
    for fila in resultado["filas"]:
        assert len(fila["celdas"]) == len(resultado["columnas"])
        assert sum(c["frecuencia"] for c in fila["celdas"]) == fila["total"]
    assert len(resultado["totales_columna"]) == len(resultado["columnas"])


PACIENTES = [
    ["Sexo", "Edad", "Dx"],
    ["F", 25, "A"], ["F", 28, "B"], ["M", 31, "A"], ["F", 35, "A"], ["M", 44, "B"],
    ["M", 47, "B"], ["F", 52, "A"], ["M", 66, "A"], ["F", None, "B"], [None, 70, "A"],
]  # fmt: skip


def test_cruce_basico_con_la_forma_del_contrato():
    resultado = cruzar(PACIENTES, "Sexo", "Dx")
    assert resultado["fila"] == {"columna": "Sexo", "agrupado": False}
    assert resultado["columna"] == {"columna": "Dx", "agrupado": False}
    assert (resultado["n"], resultado["vacios_excluidos"]) == (9, 1)  # una fila con Sexo vacío
    assert resultado["columnas"] == [
        {"tipo": "valor", "etiqueta": "A", "rango": None},
        {"tipo": "valor", "etiqueta": "B", "rango": None},
    ]
    assert etiquetas(resultado["filas"]) == ["F", "M"]
    fila_f = resultado["filas"][0]
    assert (fila_f["tipo"], fila_f["rango"], fila_f["total"]) == ("valor", None, 5)
    assert fila_f["celdas"] == [{"frecuencia": 3, "porcentaje": 60.0}, {"frecuencia": 2, "porcentaje": 40.0}]
    assert resultado["totales_columna"] == [{"frecuencia": 5, "porcentaje": 55.6}, {"frecuencia": 4, "porcentaje": 44.4}]
    assert resultado["avisos"] == []
    comprobar_cuadre(resultado)


def test_n_son_las_filas_con_las_dos_columnas_y_vacios_excluidos_el_resto():
    resultado = cruzar(PACIENTES, "Sexo", "Edad")
    assert (resultado["n"], resultado["vacios_excluidos"]) == (8, 2)  # un vacío en Sexo y otro en Edad
    assert resultado["n"] + resultado["vacios_excluidos"] == 10
    comprobar_cuadre(resultado)


def test_porcentaje_de_celda_sobre_su_fila_y_de_totales_sobre_n_con_un_decimal():
    filas = [["A", "B"]] + [["x", "p"]] * 1 + [["x", "q"]] * 2 + [["y", "p"]] * 2
    resultado = cruzar(filas, "A", "B")
    assert [c["porcentaje"] for c in resultado["filas"][0]["celdas"]] == [33.3, 66.7]
    assert [c["porcentaje"] for c in resultado["filas"][1]["celdas"]] == [100.0, 0.0]
    assert [t["porcentaje"] for t in resultado["totales_columna"]] == [60.0, 40.0]


def test_ejes_en_orden_natural():
    filas = [["Num", "Txt"]] + [[n, t] for n, t in [(10, "b"), (2, "Árbol"), (100, "a"), (2, "B"), (1.5, "a")]]
    resultado = cruzar(filas, "Num", "Txt")
    assert etiquetas(resultado["filas"]) == ["1.5", "2", "10", "100"]  # números, no texto
    assert etiquetas(resultado["columnas"]) == ["a", "Árbol", "B", "b"]  # sin distinguir tildes ni mayúsculas (en empate, por código)
    comprobar_cuadre(resultado)


def test_una_celda_con_varios_valores_cuenta_como_un_unico_valor():
    filas = [["Comorbilidad", "Sexo"], ["HTA y Diabetes", "F"], ["HTA", "M"], ["HTA y Diabetes", "M"], ["Diabetes", "F"]]
    resultado = cruzar(filas, "Comorbilidad", "Sexo")
    assert etiquetas(resultado["filas"]) == ["Diabetes", "HTA", "HTA y Diabetes"]
    assert resultado["filas"][2]["total"] == 2


# --- Rangos --------------------------------------------------------------------------------------


def test_rangos_en_el_eje_de_filas():
    resultado = cruzar(PACIENTES, "Edad", "Sexo", ["<30", "30-39", "40+"])
    assert resultado["fila"] == {"columna": "Edad", "agrupado": True}
    assert resultado["columna"]["agrupado"] is False
    assert [(f["tipo"], f["etiqueta"], f["rango"]) for f in resultado["filas"]] == [
        ("rango", "Menos de 30", "<30"), ("rango", "30 a 39", "30-39"), ("rango", "40 o más", "40+"),
    ]  # fmt: skip
    assert [f["total"] for f in resultado["filas"]] == [2, 2, 4]
    assert (resultado["n"], resultado["vacios_excluidos"]) == (8, 2)
    comprobar_cuadre(resultado)


def test_rangos_en_el_eje_de_columnas():
    resultado = cruzar(PACIENTES, "Sexo", "Edad", None, ["<30", "30+"])
    assert resultado["columna"]["agrupado"] is True
    assert [(c["tipo"], c["etiqueta"], c["rango"]) for c in resultado["columnas"]] == [
        ("rango", "Menos de 30", "<30"), ("rango", "30 o más", "30+"),
    ]  # fmt: skip
    comprobar_cuadre(resultado)


def test_rangos_en_ambos_ejes():
    filas = [["P", "Q"]] + [[p, q] for p in (5, 15, 25, 35) for q in (1, 2, 3, 4) for _ in range(p // 5)]
    resultado = cruzar(filas, "P", "Q", ["<10", "10-29", ">=30"], ["1-2", "3-4"])
    assert resultado["fila"]["agrupado"] and resultado["columna"]["agrupado"]
    assert etiquetas(resultado["filas"]) == ["Menos de 10", "10 a 29", "30 o más"]
    assert etiquetas(resultado["columnas"]) == ["1 a 2", "3 a 4"]
    assert resultado["filas"][0]["celdas"] == [{"frecuencia": 2, "porcentaje": 50.0}, {"frecuencia": 2, "porcentaje": 50.0}]
    comprobar_cuadre(resultado)


def test_un_rango_sin_registros_aparece_con_ceros():
    resultado = cruzar(PACIENTES, "Edad", "Sexo", ["<10", "20-90"])
    assert resultado["filas"][0]["total"] == 0
    assert all(c == {"frecuencia": 0, "porcentaje": 0.0} for c in resultado["filas"][0]["celdas"])
    comprobar_cuadre(resultado)


def test_fuera_de_rango_y_sin_valor_numerico_como_categorias_propias():
    valores = [25, 35, 39.5, 50, 45, 25, 35, 45, 25, 35, 45, 35, 25, 45, 25, 35, 45, 35, 25, 45, "N/D"]
    filas = [["Edad", "Sexo"]] + [[v, "F" if i % 2 else "M"] for i, v in enumerate(valores)]
    resultado = cruzar(filas, "Edad", "Sexo", ["<30", "30-39", "40-49"])
    assert [f["tipo"] for f in resultado["filas"]] == ["rango", "rango", "rango", "fuera_de_rango", "sin_valor_numerico"]
    assert etiquetas(resultado["filas"])[-2:] == ["Fuera de los rangos", "Sin valor numérico"]
    assert [f["total"] for f in resultado["filas"]][-2:] == [2, 1]  # 39,5 y 50 / "N/D"
    assert resultado["avisos"][0]["codigo"] == "VALORES_NO_NUMERICOS"
    assert sum(f["total"] for f in resultado["filas"]) == resultado["n"] == len(valores)
    comprobar_cuadre(resultado)


def test_las_categorias_especiales_no_aparecen_si_estan_vacias():
    resultado = cruzar(PACIENTES, "Edad", "Sexo", ["<50", "50+"])
    assert [f["tipo"] for f in resultado["filas"]] == ["rango", "rango"]


def test_rangos_solapados_en_un_cruce_son_un_error():
    error = error_de(PACIENTES, "Edad", "Sexo", ["30-39", "35-45"])
    assert (error.codigo, error.estado) == ("RANGOS_SOLAPADOS_EN_CRUCE", 422)
    assert error.detalle["rangos"] == ["30-39", "35-45"]
    assert error_de(PACIENTES, "Sexo", "Edad", None, ["<=30", ">=30"]).codigo == "RANGOS_SOLAPADOS_EN_CRUCE"
    assert cruzar(PACIENTES, "Edad", "Sexo", ["<30", ">=30"])["n"] == 8  # tocarse sin compartir valores sí vale


def test_rangos_en_columna_no_numerica_son_un_error():
    assert error_de(PACIENTES, "Sexo", "Dx", ["<30"]).codigo == "RANGOS_EN_COLUMNA_NO_NUMERICA"
    assert error_de(PACIENTES, "Dx", "Sexo", None, ["<30"]).codigo == "RANGOS_EN_COLUMNA_NO_NUMERICA"


def test_errores_de_sintaxis_de_rangos_en_un_eje():
    assert error_de(PACIENTES, "Edad", "Sexo", ["abc"]).codigo == "RANGO_NO_VALIDO"
    assert error_de(PACIENTES, "Edad", "Sexo", ["40+", ">=40"]).codigo == "RANGO_REPETIDO"


# --- Sin datos y límites -----------------------------------------------------------------------------


def test_sin_filas_con_las_dos_columnas_es_sin_datos():
    filas = [["A", "B"], ["x", None], [None, "y"]]
    error = error_de(filas, "A", "B")
    assert (error.codigo, error.estado) == ("SIN_DATOS", 422)


def test_limite_de_filas_y_columnas_del_cruce():
    base = [["F", "C"]] + [[i, "c"] for i in range(MAX_FILAS)]
    assert len(cruzar(base, "F", "C")["filas"]) == MAX_FILAS  # 100 filas: aún cabe
    error = error_de(base + [[MAX_FILAS, "c"]], "F", "C")
    assert (error.codigo, error.estado) == ("DEMASIADAS_CATEGORIAS", 422)
    assert error.detalle["filas"] == 101 and error.detalle["max_filas"] == 100
    ancho = [["F", "C"]] + [["f", f"c{i}"] for i in range(MAX_COLUMNAS + 1)]
    assert error_de(ancho, "F", "C").codigo == "DEMASIADAS_CATEGORIAS"


def test_limite_de_celdas_del_cruce():
    def malla(lado):
        return [["F", "C"]] + [[f, c] for f in range(lado) for c in range(lado)]

    assert len(cruzar(malla(50), "F", "C")["filas"]) == 50  # 50 x 50 = 2 500: aún cabe
    error = error_de(malla(51), "F", "C")  # 2 601 celdas
    assert error.codigo == "DEMASIADAS_CATEGORIAS" and error.detalle["max_celdas"] == MAX_CELDAS


def test_agrupar_en_rangos_evita_el_limite_de_categorias():
    filas = [["Edad", "Sexo"]] + [[i, "F"] for i in range(200)]
    assert error_de(filas, "Edad", "Sexo").codigo == "DEMASIADAS_CATEGORIAS"
    assert len(cruzar(filas, "Edad", "Sexo", ["<100", "100+"])["filas"]) == 2
