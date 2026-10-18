// Estado de la sesión: el archivo abierto y el último resultado de cada análisis.
// Solo el dataset_id se recuerda entre recargas (sessionStorage); el archivo vive en el servidor.

const CLAVE_ALMACEN = 'datatab.dataset_id';

const sesion = { dataset: null, resultados: {} };

function leerAlmacen() {
  try {
    return sessionStorage.getItem(CLAVE_ALMACEN);
  } catch {
    return null; // almacenamiento bloqueado: la app funciona igual, solo que sin recuperar la sesión
  }
}

function escribirAlmacen(id) {
  try {
    if (id === null) sessionStorage.removeItem(CLAVE_ALMACEN);
    else sessionStorage.setItem(CLAVE_ALMACEN, id);
  } catch {
    // sin almacenamiento no se puede recordar el archivo; no es un error para la persona
  }
}

export const idRecordado = leerAlmacen;

export function abrirSesion(dataset) {
  sesion.dataset = dataset;
  sesion.resultados = {};
  escribirAlmacen(dataset.dataset_id);
}

export function cerrarSesion() {
  sesion.dataset = null;
  sesion.resultados = {};
  escribirAlmacen(null);
}

export const datasetActual = () => sesion.dataset;

/** Último resultado calculado de un análisis ('frecuencias' o 'cruce'): { clave, respuesta } o undefined. */
export const ultimoResultado = (analisis) => sesion.resultados[analisis];

export function guardarResultado(analisis, clave, respuesta) {
  sesion.resultados[analisis] = { clave, respuesta };
}
