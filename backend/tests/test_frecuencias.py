import datetime as dt

import pytest

from app.config import Configuracion
from app.errors import ErrorDataTab
from app.services.frecuencias import calcular_frecuencias
from ayudas import columna, leer_filas


MAXIMO = Configuracion().max_valores_distintos


def frecuencias(filas, nombre, rangos=None, maximo=MAXIMO):
    serie, perfil = columna(leer_filas(filas), nombre)
    return calcular_frecuencias(serie, perfil, rangos, maximo)


def etiquetas(resultado) -> list[str]:
    return [f["etiqueta"] for f in resultado["filas"]]


def error_de(filas, nombre, rangos=None, maximo=MAXIMO) -> ErrorDataTab:
    with pytest.raises(ErrorDataTab) as capturado:
        frecuencias(filas, nombre, rangos, maximo)
    return capturado.value


def tabla(nombre: str, valores) -> list[list]:
    """Una columna con los valores dados y otra de números de fila (así las filas con vacíos se conservan)."""
    return [["Fila", nombre]] + [[i, valor] for i, valor in enumerate(valores, 1)]


EDADES = tabla("Edad", [25, 34, 35, 41, 41, 58, 60, 72, None, None])


# --- Sin rangos -------------------------------------------------------------------------------


def test_texto_ordena_por_frecuencia_y_en_empate_alfabeticamente_sin_tildes():
    resultado = frecuencias(tabla("Dx", ["Zeta"] * 2 + ["Árbol"] * 2 + ["Beta"] * 2 + ["Única"] * 3 + ["alfa"]), "Dx")
    assert etiquetas(resultado) == ["Única", "Árbol", "Beta", "Zeta", "alfa"]
    assert [f["frecuencia"] for f in resultado["filas"]] == [3, 2, 2, 2, 1]


def test_numerica_ordena_de_menor_a_mayor_como_numeros_y_sin_decimales_sobrantes():
    resultado = frecuencias(tabla("Dias", [10, 2, 2.0, 100, 1.5, 10, 2]), "Dias")
    assert etiquetas(resultado) == ["1.5", "2", "10", "100"]  # no "10" antes de "2", ni "2.0"
    assert [f["frecuencia"] for f in resultado["filas"]] == [1, 3, 2, 1]


def test_valores_como_30_y_no_30_punto_0_aunque_haya_vacios():
    resultado = frecuencias(EDADES, "Edad")  # con vacíos pandas habría convertido a float
    assert "34" in etiquetas(resultado) and "34.0" not in etiquetas(resultado)


def test_numerica_con_no_numericos_los_deja_al_final():
    resultado = frecuencias(tabla("Edad", [5, 3, 5, 4, 3, 3, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, "N/D"]), "Edad")
    assert etiquetas(resultado) == ["3", "4", "5", "N/D"]
    assert resultado["tipo"] == "numerica"


def test_fecha_de_menor_a_mayor():
    resultado = frecuencias(tabla("Dia", [dt.date(2024, 5, d) for d in (3, 1, 2, 1)]), "Dia")
    assert etiquetas(resultado) == ["2024-05-01", "2024-05-02", "2024-05-03"] and resultado["tipo"] == "fecha"


def test_sin_rangos_el_resultado_tiene_la_forma_del_contrato():
    resultado = frecuencias(EDADES, "Edad")
    assert (resultado["columna"], resultado["tipo"], resultado["agrupado"]) == ("Edad", "numerica", False)
    assert (resultado["n"], resultado["vacios_excluidos"], resultado["solapados"], resultado["avisos"]) == (8, 2, 0, [])
    assert resultado["filas"][0] == {"tipo": "valor", "etiqueta": "25", "rango": None, "frecuencia": 1, "porcentaje": 12.5}


def test_porcentajes_sobre_los_no_vacios_con_dos_decimales():
    resultado = frecuencias(tabla("X", ["a", "b", "b"] + [None] * 5), "X")
    assert resultado["n"] == 3 and resultado["vacios_excluidos"] == 5
    assert [f["porcentaje"] for f in resultado["filas"]] == [66.67, 33.33]


def test_un_texto_con_numeros_y_texto_conserva_cada_valor():
    resultado = frecuencias(tabla("Dato", ["a", "a", 1, "b"]), "Dato")
    assert resultado["tipo"] == "texto" and etiquetas(resultado)[0] == "a"


def test_columna_sin_valores_es_sin_datos():
    error = error_de(tabla("B", [None, None]), "B")
    assert (error.codigo, error.estado) == ("SIN_DATOS", 422)


# --- Con rangos -----------------------------------------------------------------------------------


def test_rangos_en_el_orden_enviado_con_etiquetas_y_porcentajes():
    resultado = frecuencias(EDADES, "Edad", ["40-59", "<30", ">=60", "30-39"])
    assert resultado["agrupado"] is True and (resultado["n"], resultado["vacios_excluidos"]) == (8, 2)
    assert etiquetas(resultado) == ["40 a 59", "Menos de 30", "60 o más", "30 a 39"]
    assert [f["rango"] for f in resultado["filas"]] == ["40-59", "<30", ">=60", "30-39"]
    assert [f["frecuencia"] for f in resultado["filas"]] == [3, 1, 2, 2]
    assert [f["porcentaje"] for f in resultado["filas"]] == [37.5, 12.5, 25.0, 25.0]
    assert all(f["tipo"] == "rango" for f in resultado["filas"])
    assert resultado["solapados"] == 0 and resultado["avisos"] == []


def test_rangos_con_limites_incluidos():
    resultado = frecuencias(tabla("X", [29, 30, 39, 40, 59, 60]), "X", ["<30", "30-39", "40-59", "60+"])
    assert [f["frecuencia"] for f in resultado["filas"]] == [1, 2, 2, 1]


def test_decimales_entre_rangos_enteros_van_a_fuera_de_los_rangos():
    resultado = frecuencias(tabla("X", [35, 39.5, 40, 100]), "X", ["30-39", "40-59"])
    assert etiquetas(resultado) == ["30 a 39", "40 a 59", "Fuera de los rangos"]
    assert resultado["filas"][2] == {"tipo": "fuera_de_rango", "etiqueta": "Fuera de los rangos", "rango": None,
                                     "frecuencia": 2, "porcentaje": 50.0}  # fmt: skip


def test_fuera_de_rango_solo_aparece_si_hay_alguno():
    resultado = frecuencias(EDADES, "Edad", ["<30", "30+"])
    assert all(f["tipo"] == "rango" for f in resultado["filas"])


def test_no_numericos_en_columna_numerica_van_a_sin_valor_numerico_y_avisan():
    resultado = frecuencias(tabla("Edad", [25, 35, 45, 55, 65, 75, 85, 25, 35, 45] * 3 + ["N/D", "N/D"]), "Edad", ["<30", "30-59", "60+"])
    assert resultado["n"] == 32
    assert resultado["filas"][-1] == {"tipo": "sin_valor_numerico", "etiqueta": "Sin valor numérico", "rango": None,
                                      "frecuencia": 2, "porcentaje": 6.25}  # fmt: skip
    assert sum(f["frecuencia"] for f in resultado["filas"]) == 32
    aviso = resultado["avisos"][0]
    assert (aviso["codigo"], aviso["nivel"]) == ("VALORES_NO_NUMERICOS", "info") and "«Edad»" in aviso["mensaje"]


def test_sin_rangos_no_hay_aviso_de_no_numericos():
    assert frecuencias(tabla("Edad", [25] * 20 + ["N/D"]), "Edad")["avisos"] == []


def test_rangos_solapados_se_calculan_y_avisan():
    resultado = frecuencias(tabla("X", [31, 36, 37, 38, 44, 50, 20]), "X", ["30-39", "35-45"])
    assert [f["frecuencia"] for f in resultado["filas"][:2]] == [4, 4]
    assert resultado["solapados"] == 3  # 36, 37 y 38 caen en los dos
    aviso = resultado["avisos"][0]
    assert aviso["codigo"] == "RANGOS_SOLAPADOS" and aviso["nivel"] == "atencion"
    assert aviso["mensaje"] == "Los rangos 30-39 y 35-45 se solapan: 3 registros se cuentan dos veces."
    # la suma de las filas supera n, como dice el contrato
    assert sum(f["frecuencia"] for f in resultado["filas"]) > resultado["n"]


def test_rangos_que_se_tocan_en_los_limites_pero_sin_registros_compartidos_no_avisan():
    filas = tabla("X", [10, 20, 50])
    resultado = frecuencias(filas, "X", ["0-30", "20-40"])  # solapan como intervalos...
    assert resultado["solapados"] == 1  # ...y el 20 sí está en los dos
    resultado = frecuencias(filas, "X", ["0-15", "12-18"])
    assert resultado["solapados"] == 0 and resultado["avisos"] == []


def test_aviso_de_un_solo_registro_compartido_en_singular():
    resultado = frecuencias(tabla("X", [35, 1, 2]), "X", ["30-39", "35-45"])
    assert resultado["avisos"][0]["mensaje"].endswith("1 registro se cuenta dos veces.")


def test_muchas_parejas_solapadas_limitan_los_avisos():
    resultado = frecuencias(tabla("X", [5]), "X", [f"0-{i}" for i in range(10, 20)])  # 10 rangos que contienen el 5
    assert resultado["solapados"] == 1
    assert len(resultado["avisos"]) == 6 and "parejas de rangos más" in resultado["avisos"][-1]["mensaje"]


def test_rangos_vacios_o_en_blanco_equivalen_a_no_pedir_rangos():
    assert frecuencias(EDADES, "Edad", [])["agrupado"] is False
    assert frecuencias(EDADES, "Edad", [" ", ""])["agrupado"] is False
    assert frecuencias(EDADES, "Edad", None)["agrupado"] is False


def test_rangos_en_columna_de_texto_o_fecha_es_error():
    assert error_de(tabla("Sexo", ["F", "M"]), "Sexo", ["<30"]).codigo == "RANGOS_EN_COLUMNA_NO_NUMERICA"
    assert error_de(tabla("D", [dt.date(2024, 1, 1)]), "D", ["<30"]).codigo == "RANGOS_EN_COLUMNA_NO_NUMERICA"


def test_errores_de_rangos():
    assert error_de(EDADES, "Edad", ["abc"]).codigo == "RANGO_NO_VALIDO"
    assert error_de(EDADES, "Edad", ["40+", ">=40"]).codigo == "RANGO_REPETIDO"
    assert error_de(EDADES, "Edad", [f"{i}-{i}" for i in range(51)]).codigo == "DEMASIADOS_RANGOS"


def test_numeros_como_texto_entran_en_los_rangos():
    resultado = frecuencias(tabla("Edad", ["25", 26, "27,5", 40, "N/D"] + [30] * 20), "Edad", ["<30", "30+"])
    assert [f["frecuencia"] for f in resultado["filas"]][:2] == [3, 21]


# --- Tope de valores distintos (solo sin rangos) -----------------------------------------------------------


def codigos(cantidad: int, repeticiones: int = 1) -> list[str]:
    return [f"C{i:04d}" for i in range(cantidad)] * repeticiones


def test_el_tope_por_defecto_es_mil():
    assert MAXIMO == 1000


def test_con_exactamente_el_maximo_de_valores_distintos_se_calcula():
    resultado = frecuencias(tabla("Codigo", codigos(1000)), "Codigo")
    assert len(resultado["filas"]) == 1000 and resultado["n"] == 1000


def test_con_un_valor_distinto_por_encima_del_maximo_es_demasiadas_categorias():
    error = error_de(tabla("Codigo", codigos(1001)), "Codigo")
    assert (error.codigo, error.estado) == ("DEMASIADAS_CATEGORIAS", 422)
    assert error.mensaje == "«Codigo» tiene 1.001 valores distintos; son demasiados para una tabla de frecuencias."
    assert error.sugerencia == "Elige otra columna o limpia el archivo para unificar valores parecidos."
    assert error.detalle == {"valores_distintos": 1001, "maximo": 1000}


def test_en_una_columna_numerica_la_sugerencia_es_agrupar_en_rangos():
    error = error_de(tabla("Peso", [i + 0.5 for i in range(1001)]), "Peso")
    assert error.codigo == "DEMASIADAS_CATEGORIAS"
    assert error.mensaje == "«Peso» tiene 1.001 valores distintos; son demasiados para una tabla de frecuencias."
    assert error.sugerencia == "Agrúpalos en rangos, por ejemplo 0-9, 10-19…"


def test_en_una_columna_de_fechas_no_se_sugieren_rangos():
    dias = [dt.date(2020, 1, 1) + dt.timedelta(days=i) for i in range(1001)]
    error = error_de(tabla("Dia", dias), "Dia")
    assert error.codigo == "DEMASIADAS_CATEGORIAS" and error.sugerencia.startswith("Elige otra columna")


def test_el_tope_cuenta_valores_distintos_y_no_filas():
    resultado = frecuencias(tabla("Codigo", codigos(1000, repeticiones=3)), "Codigo")
    assert len(resultado["filas"]) == 1000 and resultado["n"] == 3000


def test_los_vacios_no_cuentan_para_el_tope():
    resultado = frecuencias(tabla("Codigo", codigos(1000) + [None] * 50), "Codigo")
    assert len(resultado["filas"]) == 1000 and resultado["vacios_excluidos"] == 50


def test_los_no_numericos_de_una_columna_numerica_cuentan_como_valores_distintos():
    valores = [i for i in range(998)] + ["N/D", "S/D", "ND"]  # 1001 valores distintos, casi todos números
    error = error_de(tabla("Edad", valores), "Edad")
    assert error.codigo == "DEMASIADAS_CATEGORIAS" and error.detalle["valores_distintos"] == 1001


def test_con_rangos_el_tope_no_aplica():
    filas = tabla("Dias", list(range(1001)))
    resultado = frecuencias(filas, "Dias", ["<500", "500-999", "1000+"])
    assert resultado["agrupado"] is True and [f["frecuencia"] for f in resultado["filas"]] == [500, 500, 1]


def test_el_maximo_se_puede_cambiar():
    assert len(frecuencias(tabla("Codigo", codigos(3)), "Codigo", maximo=3)["filas"]) == 3
    error = error_de(tabla("Codigo", codigos(4)), "Codigo", maximo=3)
    assert error.detalle == {"valores_distintos": 4, "maximo": 3}


def test_una_columna_sin_valores_sigue_siendo_sin_datos_y_no_demasiadas_categorias():
    assert error_de(tabla("B", [None, None]), "B", maximo=1).codigo == "SIN_DATOS"


def test_los_rangos_no_validos_se_detectan_antes_que_el_tope():
    assert error_de(tabla("Codigo", codigos(1001)), "Codigo", ["<30"]).codigo == "RANGOS_EN_COLUMNA_NO_NUMERICA"
