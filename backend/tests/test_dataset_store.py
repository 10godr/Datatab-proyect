import threading

import pandas as pd
import pytest

from app.errors import ErrorDataTab
from app.services.columnas import PerfilColumna
from app.services.dataset_store import AlmacenDatasets
from conftest import RelojFalso


def tabla_minima() -> tuple[pd.DataFrame, list[PerfilColumna]]:
    return pd.DataFrame({"A": pd.Series(["x", "y"], dtype="str")}), [PerfilColumna("A", "texto", 0, 2, 0, None, None)]


def guardar(almacen: AlmacenDatasets, nombre: str = "a.csv"):
    tabla, perfiles = tabla_minima()
    return almacen.guardar(nombre, "csv", tabla, perfiles)


@pytest.fixture
def reloj() -> RelojFalso:
    return RelojFalso()


@pytest.fixture
def almacen(reloj) -> AlmacenDatasets:
    return AlmacenDatasets(ttl_segundos=1800, max_datasets=3, reloj=reloj)


def test_guardar_y_obtener(almacen):
    dataset = guardar(almacen, "pacientes.csv")
    assert almacen.obtener(dataset.id) is dataset
    assert dataset.nombre == "pacientes.csv" and len(almacen) == 1


def test_ids_aleatorios_largos_y_seguros_para_urls(almacen):
    ids = {guardar(AlmacenDatasets(1800, 100)).id for _ in range(200)}
    assert len(ids) == 200
    for dataset_id in ids:
        assert len(dataset_id) == 22 and all(c.isalnum() or c in "-_" for c in dataset_id)


def test_un_id_inventado_no_existe(almacen):
    for dataset_id in ("inventado", "", "../../etc/passwd", "x" * 10_000, "\x00", "<script>"):
        with pytest.raises(ErrorDataTab) as capturado:
            almacen.obtener(dataset_id)
        assert capturado.value.codigo == "ARCHIVO_NO_ENCONTRADO" and capturado.value.estado == 404


def test_caduca_tras_el_tiempo_de_inactividad(almacen, reloj):
    dataset = guardar(almacen)
    reloj.avanzar(1799)
    assert almacen.obtener(dataset.id) is dataset  # aún vivo
    reloj.avanzar(1800)  # exactamente el plazo desde el último uso
    with pytest.raises(ErrorDataTab) as capturado:
        almacen.obtener(dataset.id)
    assert capturado.value.codigo == "ARCHIVO_NO_ENCONTRADO"
    assert len(almacen) == 0


def test_cada_uso_renueva_el_plazo(almacen, reloj):
    dataset = guardar(almacen)
    for _ in range(5):
        reloj.avanzar(1000)
        assert almacen.obtener(dataset.id) is dataset  # 5000 s en total, pero nunca 1800 sin usar
    reloj.avanzar(1800)
    with pytest.raises(ErrorDataTab):
        almacen.obtener(dataset.id)


def test_purgar_caducados_elimina_solo_los_caducados(almacen, reloj):
    viejo = guardar(almacen)
    reloj.avanzar(1000)
    reciente = guardar(almacen)
    reloj.avanzar(900)  # el viejo lleva 1900 s sin uso; el reciente, 900
    assert almacen.purgar_caducados() == 1
    assert len(almacen) == 1 and almacen.obtener(reciente.id) is reciente
    with pytest.raises(ErrorDataTab):
        almacen.obtener(viejo.id)
    assert almacen.purgar_caducados() == 0


def test_al_llegar_al_tope_se_elimina_el_menos_recientemente_usado(almacen):
    primero, segundo, tercero = (guardar(almacen, f"{i}.csv") for i in range(3))
    almacen.obtener(primero.id)  # el segundo pasa a ser el menos reciente
    cuarto = guardar(almacen, "3.csv")
    assert len(almacen) == 3
    with pytest.raises(ErrorDataTab):
        almacen.obtener(segundo.id)
    for dataset in (primero, tercero, cuarto):
        assert almacen.obtener(dataset.id) is dataset


def test_al_guardar_se_purgan_primero_los_caducados_antes_que_expulsar_vigentes(almacen, reloj):
    viejo = guardar(almacen)
    reloj.avanzar(1000)
    medio, reciente = guardar(almacen), guardar(almacen)
    reloj.avanzar(800)  # solo el viejo ha caducado
    nuevo = guardar(almacen)
    assert len(almacen) == 3
    for dataset in (medio, reciente, nuevo):
        assert almacen.obtener(dataset.id) is dataset
    with pytest.raises(ErrorDataTab):
        almacen.obtener(viejo.id)


def test_eliminar_es_idempotente(almacen):
    dataset = guardar(almacen)
    almacen.eliminar(dataset.id)
    almacen.eliminar(dataset.id)
    almacen.eliminar("nunca-existio")
    assert len(almacen) == 0
    with pytest.raises(ErrorDataTab):
        almacen.obtener(dataset.id)


def test_vaciar(almacen):
    for _ in range(3):
        guardar(almacen)
    almacen.vaciar()
    assert len(almacen) == 0


def test_columna_devuelve_serie_y_perfil_o_error(almacen):
    dataset = guardar(almacen)
    serie, perfil = dataset.columna("A")
    assert serie.tolist() == ["x", "y"] and perfil.nombre == "A"
    with pytest.raises(ErrorDataTab) as capturado:
        dataset.columna("No existe")
    assert capturado.value.codigo == "COLUMNA_NO_ENCONTRADA" and capturado.value.estado == 422


def test_uso_concurrente_no_rompe_el_almacen():
    almacen = AlmacenDatasets(ttl_segundos=1800, max_datasets=5)
    fallos = []

    def trabajar():
        try:
            for _ in range(200):
                dataset = guardar(almacen)
                almacen.obtener(dataset.id) if len(almacen) else None
                almacen.purgar_caducados()
        except ErrorDataTab:
            pass  # otro hilo pudo expulsarlo por el tope: es normal
        except Exception as error:  # noqa: BLE001
            fallos.append(error)

    hilos = [threading.Thread(target=trabajar) for _ in range(8)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join()
    assert fallos == [] and len(almacen) <= 5
