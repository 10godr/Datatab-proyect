// Vista de carga: validar el archivo en el navegador, enviarlo y mostrar errores o avisos.

import { cargarEjemplo, comoErrorApi, subirArchivo } from '../api.js';
import { listaDeFormatos, numero, tamanoEnMB } from '../formato.js';
import { rellenar } from '../plantillas.js';

const MAX_EXTENSION_MOSTRADA = 12;

/** Extensión en minúsculas sin el punto, o '' si el nombre no tiene. */
function extensionDe(nombre) {
  const punto = nombre.lastIndexOf('.');
  return punto < 0 ? '' : nombre.slice(punto + 1).toLowerCase();
}

/**
 * Comprueba lo que se puede saber sin el servidor: uno solo, formato permitido, no vacío y no demasiado grande.
 * Devuelve { mensaje, sugerencia } con el primer problema, o null si el archivo puede enviarse.
 * `archivos` es una lista de File (o de objetos con name y size).
 */
export function validarArchivos(archivos, config) {
  if (archivos.length === 0) {
    return { mensaje: 'Lo que soltaste no es un archivo.', sugerencia: 'Elige un archivo desde tu equipo.' };
  }
  if (archivos.length > 1) {
    return { mensaje: 'Has soltado más de un archivo.', sugerencia: 'Carga un archivo cada vez.' };
  }
  const [archivo] = archivos;
  const extension = extensionDe(archivo.name);
  if (!config.formatos.includes(extension)) {
    const sugerencia = `Guarda tu archivo como ${listaDeFormatos(config.formatos, 'o')} y vuelve a cargarlo.`;
    return extension === ''
      ? { mensaje: 'El archivo no tiene extensión, así que no se sabe de qué tipo es.', sugerencia }
      : { mensaje: `El formato .${extension.slice(0, MAX_EXTENSION_MOSTRADA)} no es compatible.`, sugerencia };
  }
  if (archivo.size === 0) {
    return { mensaje: 'El archivo está vacío.', sugerencia: 'Elige un archivo que tenga datos.' };
  }
  if (archivo.size > config.max_bytes) {
    return {
      mensaje: `El archivo pesa ${tamanoEnMB(archivo.size)} MB. El máximo es ${numero(config.max_mb)} MB.`,
      sugerencia: 'Elimina hojas o columnas que no necesites y vuelve a intentarlo.',
    };
  }
  return null;
}

let config;
let alCargar;
let enCurso = false;
let el;

function ocupar(ocupado) {
  enCurso = ocupado;
  el.zona.setAttribute('aria-busy', String(ocupado));
  el.entrada.disabled = ocupado;
  el.ejemplo.disabled = ocupado;
  el.leyendo.hidden = !ocupado;
}

/** Quita el error y el aviso anteriores. */
export function limpiarMensajes() {
  el.error.hidden = true;
  el.aviso.hidden = true;
}

export function mostrarErrorDeCarga({ mensaje, sugerencia = '' }) {
  rellenar(el.error, { mensaje, sugerencia });
  el.error.hidden = false;
}

/** Aviso que no es un error de carga (el archivo caducó, se cerró...). */
export function mostrarAvisoDeCarga(mensaje) {
  rellenar(el.aviso, { mensaje });
  el.aviso.hidden = false;
}

/** Deja la zona de carga lista para un archivo nuevo. */
export function reiniciarCarga() {
  limpiarMensajes();
  el.entrada.value = '';
  ocupar(false);
}

/** Muestra «Leyendo el archivo…» (también al recuperar la sesión al recargar). */
export function mostrarLeyendo(leyendo) {
  ocupar(leyendo);
}

async function enviar(peticion) {
  if (enCurso) return;
  limpiarMensajes();
  ocupar(true);
  try {
    const dataset = await peticion();
    el.entrada.value = '';
    ocupar(false);
    alCargar(dataset);
  } catch (error) {
    mostrarErrorDeCarga(comoErrorApi(error));
    el.entrada.value = '';
    ocupar(false);
    el.entrada.focus();
  }
}

function procesar(archivos) {
  if (enCurso) return;
  limpiarMensajes();
  const problema = validarArchivos(archivos, config);
  if (problema) {
    mostrarErrorDeCarga(problema);
    el.entrada.value = '';
    return;
  }
  enviar(() => subirArchivo(archivos[0]));
}

function conectarArrastre() {
  let profundidad = 0; // dragenter/dragleave se disparan también al cruzar los hijos de la zona
  const traeArchivos = (evento) => evento.dataTransfer?.types?.includes('Files');

  el.zona.addEventListener('dragenter', (evento) => {
    if (!traeArchivos(evento)) return;
    evento.preventDefault();
    profundidad += 1;
    el.zona.dataset.arrastrando = 'true';
  });
  el.zona.addEventListener('dragover', (evento) => {
    if (!traeArchivos(evento)) return;
    evento.preventDefault();
    evento.dataTransfer.dropEffect = 'copy';
  });
  el.zona.addEventListener('dragleave', () => {
    profundidad = Math.max(0, profundidad - 1);
    if (profundidad === 0) delete el.zona.dataset.arrastrando;
  });
  el.zona.addEventListener('drop', (evento) => {
    evento.preventDefault();
    profundidad = 0;
    delete el.zona.dataset.arrastrando;
    procesar([...evento.dataTransfer.files]);
  });

  // Un archivo soltado fuera de la zona abriría el archivo en el navegador y se perdería la pantalla
  for (const nombre of ['dragover', 'drop']) {
    window.addEventListener(nombre, (evento) => {
      if (traeArchivos(evento)) evento.preventDefault();
    });
  }
}

/** Conecta la vista de carga. `alTerminar(dataset)` se llama cuando el servidor acepta el archivo. */
export function iniciarCarga(configuracion, alTerminar) {
  config = configuracion;
  alCargar = alTerminar;
  const porId = (id) => document.getElementById(id);
  el = {
    zona: porId('zona-carga'),
    entrada: porId('archivo-input'),
    ejemplo: porId('btn-ejemplo'),
    leyendo: porId('carga-leyendo'),
    error: porId('carga-error-contenido'),
    aviso: porId('carga-aviso-contenido'),
  };

  for (const elemento of document.querySelectorAll('[data-config="formatos"]')) {
    elemento.textContent = listaDeFormatos(config.formatos);
  }
  for (const elemento of document.querySelectorAll('[data-config="max-mb"]')) {
    elemento.textContent = numero(config.max_mb);
  }
  for (const elemento of document.querySelectorAll('[data-config="minutos-inactividad"]')) {
    elemento.textContent = numero(config.minutos_inactividad);
  }
  el.entrada.accept = config.formatos.map((formato) => `.${formato}`).join(',');
  el.ejemplo.hidden = !config.ejemplo_disponible;

  el.entrada.addEventListener('change', () => {
    if (el.entrada.files.length > 0) procesar([...el.entrada.files]);
  });
  el.ejemplo.addEventListener('click', () => enviar(cargarEjemplo));
  conectarArrastre();
}
