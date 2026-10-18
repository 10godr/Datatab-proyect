import datetime as dt

import numpy as np
import pandas as pd
import pytest

from app.services.columnas import (
    clave_texto,
    es_fecha,
    formatear_numero,
    normalizar_valor,
    numero_canonico,
    orden_natural,
    parsear_numero,
    perfilar_columna,
    valores_numericos,
)


def serie(*valores) -> pd.Series:
    return pd.Series(list(valores), dtype="str")


# --- Valor normalizado -----------------------------------------------------------------------


@pytest.mark.parametrize(
    "valor, esperado",
    [
        ("  Femenino  ", "Femenino"),
        ("Dos   espacios\ty\ntabulador", "Dos espacios y tabulador"),
        ("con espacio duro", "con espacio duro"),
        ("", None),
        ("   ", None),
        (None, None),
        (30, "30"),
        (30.0, "30"),
        (1.5, "1.5"),
        (0.1 + 0.2, "0.3"),
        (-0.0, "0"),
        (1e-7, "0.0000001"),
        (1.5e20, "150000000000000000000"),
        (12345.678, "12345.678"),
        (float("nan"), None),
        (float("inf"), None),
        (True, "Verdadero"),
        (False, "Falso"),
        (dt.date(2024, 5, 1), "2024-05-01"),
        (dt.datetime(2024, 5, 1), "2024-05-01"),
        (dt.datetime(2024, 5, 1, 13, 5, 59), "2024-05-01 13:05"),
        (dt.time(9, 5), "09:05"),
        (dt.timedelta(hours=30, minutes=7), "30:07"),
    ],
)
def test_valor_normalizado(valor, esperado):
    assert normalizar_valor(valor) == esperado


def test_mayusculas_y_tildes_no_se_unifican():
    assert normalizar_valor("Masculino") != normalizar_valor("masculino")
    assert normalizar_valor("Sí") != normalizar_valor("Si")


@pytest.mark.parametrize(
    "numero, esperado", [(30.0, "30"), (1.5, "1.5"), (100, "100"), (1e15, "1000000000000000"), (2.5e-5, "0.000025")]
)
def test_formatear_numero_sin_notacion_cientifica(numero, esperado):
    assert formatear_numero(numero) == esperado


@pytest.mark.parametrize(
    "texto, numero",
    [("34", 34.0), ("1,5", 1.5), ("-2.5", -2.5), ("+7", 7.0), (".5", 0.5), (",5", 0.5), ("007", 7.0), ("0", 0.0)],
)
def test_textos_que_parecen_numeros(texto, numero):
    assert parsear_numero(texto) == numero


@pytest.mark.parametrize(
    "texto", ["N/D", "31-40", "", "1e5", "nan", "inf", "-inf", "1.234,5", "1,234.5", "1 5", "5.", "--5", "٣٤", "0x10", "9" * 400]
)
def test_textos_que_no_son_numeros(texto):
    assert parsear_numero(texto) is None


@pytest.mark.parametrize(
    "texto, canonico", [("007", "7"), ("1,50", "1.5"), ("-0", "0"), ("+5", "5"), (".5", "0.5"), ("100", "100"), ("1.0", "1")]
)
def test_numero_canonico_no_pierde_cifras(texto, canonico):
    assert numero_canonico(texto) == canonico
    assert numero_canonico("12345678901234567890") == "12345678901234567890"  # un float lo estropearía


@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("2024-05-01", True),
        ("2024-05-01 13:45", True),
        ("2024-02-30", False),
        ("2024-13-01", False),
        ("2024-05-01 25:00", False),
        ("2024-05-01 13:45:10", False),
        ("01/05/2024", False),
        ("20240501", False),
        ("2024-5-1", False),
    ],
)
def test_es_fecha(texto, esperado):
    assert es_fecha(texto) is esperado


# --- Tipos de columna -------------------------------------------------------------------------------


def test_columna_numerica_con_minimo_y_maximo_enteros():
    _, perfil, avisos = perfilar_columna("Edad", serie("30", "45", None, "18", "92", "45"))
    assert (perfil.tipo, perfil.vacios, perfil.distintos, perfil.no_numericos) == ("numerica", 1, 4, 0)
    assert (perfil.minimo, perfil.maximo) == (18, 92)
    assert isinstance(perfil.minimo, int) and avisos == []


def test_columna_numerica_con_decimales():
    _, perfil, _ = perfilar_columna("Peso", serie("72,5", "61.25", "80"))
    assert (perfil.tipo, perfil.minimo, perfil.maximo) == ("numerica", 61.25, 80)


def test_umbral_del_90_por_ciento():
    # 9 de 10 son números: exactamente el 90 %, es numérica
    _, perfil, _ = perfilar_columna("X", serie(*["1"] * 9, "N/D"))
    assert (perfil.tipo, perfil.no_numericos) == ("numerica", 1)
    # 8 de 10: es texto
    _, perfil, _ = perfilar_columna("X", serie(*["1"] * 8, "N/D", "N/D"))
    assert (perfil.tipo, perfil.no_numericos) == ("texto", 0)


def test_el_umbral_cuenta_registros_no_valores_distintos():
    _, perfil, _ = perfilar_columna("X", serie(*["1"] * 95, "N/D", "x", "y", "z", "w"))
    assert perfil.tipo == "numerica" and perfil.no_numericos == 5


def test_numeros_guardados_como_texto_cuentan_igual_que_los_numeros():
    resultado, perfil, _ = perfilar_columna("Edad", serie("45", "45.0", "45,0", "007", "7", "1,5", "N/D", *["2"] * 9))
    assert perfil.tipo == "numerica"
    assert sorted(resultado.dropna().unique()) == sorted(["45", "7", "1.5", "N/D", "2"])
    assert perfil.distintos == 5  # 45, 7, 1.5, 2 y "N/D"
    assert perfil.minimo == 1.5 and perfil.maximo == 45


def test_rango_no_es_numero():
    _, perfil, _ = perfilar_columna("Grupo", serie("31-40", "41-50", "51-60"))
    assert perfil.tipo == "texto"


def test_columna_de_fechas():
    _, perfil, _ = perfilar_columna("Ingreso", serie("2024-05-01", "2024-05-01 13:45", None, "2023-12-31"))
    assert (perfil.tipo, perfil.vacios, perfil.distintos, perfil.minimo, perfil.maximo) == ("fecha", 1, 3, None, None)


def test_una_fecha_inexistente_no_hace_fecha_la_columna():
    _, perfil, _ = perfilar_columna("X", serie("2024-05-01", "2024-02-31"))
    assert perfil.tipo == "texto"


def test_columna_de_texto():
    _, perfil, _ = perfilar_columna("Sexo", serie("F", "M", "F", None))
    assert (perfil.tipo, perfil.vacios, perfil.distintos, perfil.minimo, perfil.maximo) == ("texto", 1, 2, None, None)


def test_columna_totalmente_vacia():
    _, perfil, avisos = perfilar_columna("Notas", pd.Series([None, None, None], dtype="str"))
    assert (perfil.tipo, perfil.vacios, perfil.distintos) == ("texto", 3, 0) and avisos == []


# --- VALORES_PARECIDOS --------------------------------------------------------------------------------


def test_valores_parecidos_por_mayusculas():
    _, _, avisos = perfilar_columna("Sexo", serie("Masculino", "masculino", "Femenino", "Masculino"))
    assert len(avisos) == 1 and avisos[0]["codigo"] == "VALORES_PARECIDOS" and avisos[0]["nivel"] == "info"
    assert "«Masculino» y «masculino» parecen el mismo valor pero se cuentan por separado." in avisos[0]["mensaje"]
    assert "«Sexo»" in avisos[0]["mensaje"]


def test_valores_parecidos_por_tildes_y_espacios():
    _, _, avisos = perfilar_columna("Dx", serie("Infección", "Infeccion", "Infección  de herida", "infección de herida"))
    mensaje = avisos[0]["mensaje"]
    assert "«Infección» y «Infeccion»" in mensaje or "«Infeccion» y «Infección»" in mensaje
    assert "de herida" in mensaje


def test_valores_parecidos_muestra_hasta_tres_ejemplos():
    valores = [v for letra in "abcde" for v in (letra, letra.upper())]
    _, _, avisos = perfilar_columna("X", serie(*valores))
    mensaje = avisos[0]["mensaje"]
    assert mensaje.count(" y ") == 3 and "Hay 2 casos más." in mensaje


def test_sin_valores_parecidos_no_hay_aviso():
    _, _, avisos = perfilar_columna("Sexo", serie("Femenino", "Masculino"))
    assert avisos == []


def test_valores_parecidos_no_se_busca_en_columnas_numericas():
    _, _, avisos = perfilar_columna("Edad", serie(*["1"] * 20, "N/D", "n/d"))
    assert avisos == []


def test_clave_texto():
    assert clave_texto("  ÁRBOL   Grande ") == clave_texto("arbol grande") == "arbol grande"


# --- Valores numéricos y orden ---------------------------------------------------------------------------


def test_valores_numericos():
    resultado = valores_numericos(serie("1", "2.5", None, "N/D", "-3"))
    assert np.array_equal(resultado, [1.0, 2.5, np.nan, np.nan, -3.0], equal_nan=True)
    assert np.isnan(valores_numericos(pd.Series([None, None], dtype="str"))).all()


def test_orden_natural():
    assert orden_natural(["10", "2", "N/D", "1.5", "-1", "abc"], "numerica") == ["-1", "1.5", "2", "10", "abc", "N/D"]
    assert orden_natural(["2024-05-01", "2023-12-31", "2024-05-01 10:00"], "fecha") == [
        "2023-12-31", "2024-05-01", "2024-05-01 10:00",
    ]  # fmt: skip
    assert orden_natural(["b", "Árbol", "a", "B", "Ab"], "texto") == ["a", "Ab", "Árbol", "B", "b"]
