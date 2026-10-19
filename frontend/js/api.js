// Única puerta al servidor. Todo fallo (red caída, tiempo agotado, respuesta que no es JSON o error
// del contrato) sale como un ErrorApi con código, mensaje en español y sugerencia: nunca texto técnico.

const TIEMPO_SUBIDA_MS = 60_000;
const TIEMPO_NORMAL_MS = 30_000;

export class ErrorApi extends Error {
  constructor({ codigo, mensaje, sugerencia = '', detalle = null, estado = 0 }) {
    super(mensaje);
    this.name = 'ErrorApi';
    this.codigo = codigo;
    this.mensaje = mensaje;
    this.sugerencia = sugerencia;
    this.detalle = detalle;
    this.estado = estado;
  }
}

const ERRORES_PROPIOS = {
  SIN_CONEXION: {
    mensaje: 'No se pudo conectar con DataTab.',
    sugerencia: 'Comprueba que DataTab sigue en marcha y vuelve a intentarlo.',
  },
  TIEMPO_AGOTADO: {
    mensaje: 'DataTab tardó demasiado en responder.',
    sugerencia: 'Vuelve a intentarlo. Si el archivo es muy grande, prueba con uno más pequeño.',
  },
  RESPUESTA_NO_VALIDA: {
    mensaje: 'DataTab recibió una respuesta que no esperaba.',
    sugerencia: 'Vuelve a intentarlo. Si sigue igual, recarga la página.',
  },
  ERROR_INESPERADO: {
    mensaje: 'Algo no salió como se esperaba.',
    sugerencia: 'Vuelve a intentarlo. Si sigue igual, recarga la página.',
  },
};

const errorPropio = (codigo, estado = 0) => new ErrorApi({ codigo, estado, ...ERRORES_PROPIOS[codigo] });

/** Convierte cualquier cosa que se haya lanzado en un ErrorApi presentable. */
export function comoErrorApi(error) {
  return error instanceof ErrorApi ? error : errorPropio('ERROR_INESPERADO');
}

function errorDelContrato(datos, estado) {
  const error = datos?.error;
  if (typeof error?.codigo === 'string' && typeof error?.mensaje === 'string') {
    return new ErrorApi({
      codigo: error.codigo,
      mensaje: error.mensaje,
      sugerencia: typeof error.sugerencia === 'string' ? error.sugerencia : '',
      detalle: error.detalle ?? null,
      estado,
    });
  }
  return errorPropio(estado >= 500 ? 'RESPUESTA_NO_VALIDA' : 'ERROR_INESPERADO', estado);
}

async function solicitar(metodo, ruta, { cuerpo, formulario, tiempo = TIEMPO_NORMAL_MS } = {}) {
  const control = new AbortController();
  const temporizador = setTimeout(() => control.abort(), tiempo);
  const opciones = { method: metodo, signal: control.signal, cache: 'no-store', headers: { Accept: 'application/json' } };
  if (formulario) {
    opciones.body = formulario;
  } else if (cuerpo !== undefined) {
    opciones.body = JSON.stringify(cuerpo);
    opciones.headers['Content-Type'] = 'application/json';
  }

  try {
    const respuesta = await fetch(ruta, opciones);
    if (respuesta.status === 204) return null;
    const texto = await respuesta.text();
    let datos;
    try {
      datos = JSON.parse(texto);
    } catch {
      datos = undefined;
    }
    if (!respuesta.ok) throw errorDelContrato(datos, respuesta.status);
    if (datos === null || typeof datos !== 'object') throw errorPropio('RESPUESTA_NO_VALIDA', respuesta.status);
    return datos;
  } catch (error) {
    if (error instanceof ErrorApi) throw error;
    throw errorPropio(error?.name === 'AbortError' ? 'TIEMPO_AGOTADO' : 'SIN_CONEXION');
  } finally {
    clearTimeout(temporizador);
  }
}

const rutaDataset = (id) => `/api/datasets/${encodeURIComponent(id)}`;

export const obtenerConfiguracion = () => solicitar('GET', '/api/configuracion');

export function subirArchivo(archivo) {
  const formulario = new FormData();
  formulario.append('archivo', archivo);
  return solicitar('POST', '/api/datasets', { formulario, tiempo: TIEMPO_SUBIDA_MS });
}

export const recuperarDataset = (id) => solicitar('GET', rutaDataset(id));

export const obtenerFilas = (id, desde, cantidad) =>
  solicitar('GET', `${rutaDataset(id)}/filas?desde=${desde}&cantidad=${cantidad}`);

export const calcularFrecuencias = (id, columna, rangos) =>
  solicitar('POST', `${rutaDataset(id)}/frecuencias`, { cuerpo: { columna, rangos } });

export const calcularCruce = (id, fila, columna) =>
  solicitar('POST', `${rutaDataset(id)}/tabla-cruzada`, { cuerpo: { fila, columna } });

export const borrarDataset = (id) => solicitar('DELETE', rutaDataset(id));
