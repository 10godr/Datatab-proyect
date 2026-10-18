import numpy as np
import pytest

from app.errors import ErrorDataTab
from app.services.columnas import PerfilColumna
from app.services.rangos import (
    MAX_RANGOS,
    asignar,
    pares_solapados,
    parsear_rango,
    parsear_rangos,
    rangos_de_columna,
    se_solapan,
)


def error_de(funcion, *args) -> ErrorDataTab:
    with pytest.raises(ErrorDataTab) as capturado:
        funcion(*args)
    return capturado.value


# --- Sintaxis y etiquetas ---------------------------------------------------------------


@pytest.mark.parametrize(
    "texto, etiqueta, dentro, fuera",
    [
        ("<30", "Menos de 30", [29, 29.99, -5], [30, 31]),
        ("<=30", "30 o menos", [30, 29], [30.01, 31]),
        ("≤30", "30 o menos", [30, 29], [30.01]),
        (">60", "Más de 60", [60.01, 61], [60, 59]),
        (">=60", "60 o más", [60, 61], [59.99]),
        ("≥60", "60 o más", [60, 61], [59.99]),
        ("40+", "40 o más", [40, 41, 1000], [39.99]),
        ("30-39", "30 a 39", [30, 35, 39], [29.99, 39.01]),
        ("30–39", "30 a 39", [30, 39], [40]),  # raya (–)
    ],
)
def test_cada_sintaxis_con_sus_limites_incluidos(texto, etiqueta, dentro, fuera):
    rango = parsear_rango(texto)
    assert rango.etiqueta == etiqueta
    assert rango.texto == texto
    assert rango.contiene(np.array(dentro, dtype=float)).all()
    assert not rango.contiene(np.array(fuera, dtype=float)).any()


def test_los_nan_nunca_caen_dentro_de_un_rango():
    valores = np.array([np.nan, 1.0])
    for texto in ("<30", ">=0", "0-9", "1+", "<=100", ">-5"):
        assert list(parsear_rango(texto).contiene(valores)) == [False, True], texto


@pytest.mark.parametrize("texto", ["  <30  ", "< 30", "30 - 39", " 40 + ", ">= 60", "≥ 60", "30 – 39"])
def test_los_espacios_alrededor_se_ignoran(texto):
    assert parsear_rango(texto).texto == texto.strip()


def test_decimales_con_coma_o_punto():
    assert parsear_rango("1,5-2,5").etiqueta == "1.5 a 2.5"
    assert parsear_rango("1.5-2.5").equivalencia == parsear_rango("1,5-2,5").equivalencia
    assert parsear_rango("<1,5").etiqueta == "Menos de 1.5"
    assert parsear_rango(">=0.25").etiqueta == "0.25 o más"
    assert parsear_rango(",5+").etiqueta == "0.5 o más"


def test_negativos():
    assert (parsear_rango("-5-10").minimo, parsear_rango("-5-10").maximo) == (-5, 10)
    assert (parsear_rango("-10--5").minimo, parsear_rango("-10--5").maximo) == (-10, -5)
    assert parsear_rango("<-3").etiqueta == "Menos de -3"
    assert parsear_rango(">= -2").minimo == -2
    assert parsear_rango("-5+").etiqueta == "-5 o más"
    assert parsear_rango("−5−10").minimo == -5  # signo menos tipográfico


def test_un_rango_de_un_solo_valor_es_valido():
    rango = parsear_rango("30-30")
    assert rango.contiene(np.array([30.0])).all() and not rango.contiene(np.array([30.1])).any()


@pytest.mark.parametrize("texto", ["39-30", "5--10", "10-5"])
def test_rangos_invertidos(texto):
    error = error_de(parsear_rango, texto)
    assert error.codigo == "RANGO_NO_VALIDO" and error.detalle == {"rango": texto}


@pytest.mark.parametrize(
    "texto",
    [
        "", "abc", "30", "30-", "-", "+", "<", "<>5", "=30", "<<5", ">=", "1e5", "<1e3", "30-39-45",
        "30 39", "3 0-39", "1.2.3", "<30; DROP TABLE", "<script>alert(1)</script>", "%s%s%s", "../../etc/passwd",
        "٣٠-٣٩", "30-39\n40+", "NaN", "inf", "<inf", "30..39",
    ],
)  # fmt: skip
def test_basura_es_rango_no_valido(texto):
    error = error_de(parsear_rango, texto)
    assert error.codigo == "RANGO_NO_VALIDO"
    assert error.estado == 422


def test_texto_largo_se_rechaza_y_se_recorta_en_el_error():
    error = error_de(parsear_rango, "9" * 5000)
    assert error.codigo == "RANGO_NO_VALIDO"
    assert len(error.detalle["rango"]) <= 41 and len(error.mensaje) < 200


# --- Listas de rangos -------------------------------------------------------------------


def test_lista_conserva_el_orden_enviado_e_ignora_textos_vacios():
    rangos = parsear_rangos(["40-59", "", "  ", "<30"])
    assert [r.texto for r in rangos] == ["40-59", "<30"]
    assert parsear_rangos(None) == [] and parsear_rangos([]) == [] and parsear_rangos([" "]) == []


@pytest.mark.parametrize("a, b", [("40+", ">=40"), ("30-39", "30–39"), ("<30", "< 30"), ("1,5-2", "1.5-2")])
def test_rangos_repetidos(a, b):
    error = error_de(parsear_rangos, [a, "0-1", b])
    assert error.codigo == "RANGO_REPETIDO"
    assert error.detalle["rango"] == b


def test_no_son_repetidos_rangos_parecidos_pero_distintos():
    assert len(parsear_rangos(["<30", "<=30", ">30", ">=30"])) == 4


def test_demasiados_rangos():
    cincuenta = [f"{i}-{i}" for i in range(MAX_RANGOS)]
    assert len(parsear_rangos(cincuenta)) == MAX_RANGOS
    error = error_de(parsear_rangos, cincuenta + ["99-99"])
    assert error.codigo == "DEMASIADOS_RANGOS"
    assert error.detalle == {"max_rangos": 50, "recibidos": 51}


def test_los_rangos_solo_se_admiten_en_columnas_numericas():
    texto = PerfilColumna("Sexo", "texto", 0, 2, 0, None, None)
    numerica = PerfilColumna("Edad", "numerica", 0, 2, 0, 1, 2)
    assert error_de(rangos_de_columna, texto, ["<30"]).codigo == "RANGOS_EN_COLUMNA_NO_NUMERICA"
    assert rangos_de_columna(texto, None) == [] and rangos_de_columna(texto, [" "]) == []
    assert len(rangos_de_columna(numerica, ["<30"])) == 1


# --- Solapes -----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "a, b, solapan",
    [
        ("30-39", "35-45", True),
        ("30-39", "39-45", True),  # el 39 está en los dos
        ("30-39", "40-59", False),
        ("<30", ">=30", False),
        ("<=30", ">=30", True),
        ("<30", "<=30", True),
        ("<30", ">30", False),
        (">60", "<=60", False),
        (">60", "<=61", True),
        ("40+", ">=60", True),
        ("40+", "<40", False),
        ("0-10", "2-3", True),
        ("0-10", "10,5-12", False),
        ("-5-5", "5-9", True),
        ("<10", "<20", True),
    ],
)
def test_solapes_segun_los_limites(a, b, solapan):
    assert se_solapan(parsear_rango(a), parsear_rango(b)) is solapan
    assert se_solapan(parsear_rango(b), parsear_rango(a)) is solapan


def test_pares_solapados():
    rangos = parsear_rangos(["<30", "30-39", "35-45", "40+"])
    assert pares_solapados(rangos) == [(1, 2), (2, 3)]
    assert pares_solapados(parsear_rangos(["<30", "30-39", "40+"])) == []


# --- Asignación --------------------------------------------------------------------------------


def test_asignar_separa_dentro_fuera_y_no_numericos():
    rangos = parsear_rangos(["<30", "30-39"])
    valores = np.array([10.0, 30.0, 39.0, 39.5, 50.0, np.nan])
    asignacion = asignar(valores, rangos)
    assert asignacion.por_rango[0].tolist() == [True, False, False, False, False, False]
    assert asignacion.por_rango[1].tolist() == [False, True, True, False, False, False]
    assert asignacion.fuera.tolist() == [False, False, False, True, True, False]  # 39,5 queda fuera
    assert asignacion.sin_valor.tolist() == [False, False, False, False, False, True]
