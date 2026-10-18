// Arranque: configuración del servidor, recuperación de la sesión, vistas y pestañas.

import { borrarDataset, comoErrorApi, obtenerConfiguracion, recuperarDataset } from './api.js';
import { abrirSesion, cerrarSesion, datasetActual, idRecordado } from './estado.js';
import { cantidad, entero, numero } from './formato.js';
import { pintarAvisos } from './ui/avisos.js';
import { anunciar } from './ui/panel.js';
import { iniciarPestanas } from './ui/pestanas.js';
import {
  iniciarCarga, mostrarAvisoDeCarga, mostrarErrorDeCarga, mostrarLeyendo, reiniciarCarga,
} from './vistas/carga.js';
import { iniciarCruce, mostrarArchivo as mostrarArchivoEnCruce } from './vistas/cruce.js';
import { alAbrirDatos, iniciarDatos, mostrarArchivo as mostrarArchivoEnDatos } from './vistas/datos.js';
import { iniciarFrecuencias, mostrarArchivo as mostrarArchivoEnFrecuencias } from './vistas/frecuencias.js';

// Valores del contrato por si /api/configuracion no responde: la validación del servidor manda igualmente
const CONFIGURACION_POR_DEFECTO = {
  max_mb: 5,
  max_bytes: 5 * 1024 * 1024,
  formatos: ['xlsx', 'xls', 'csv'],
  minutos_inactividad: 30,
  ejemplo_disponible: false,
};

const TITULO_CARGA = document.title;
const TITULO_ANALISIS = 'DataTab · Análisis de tu archivo';

const porId = (id) => document.getElementById(id);
const el = {
  vistaCarga: porId('vista-carga'),
  vistaAnalisis: porId('vista-analisis'),
  barraArchivo: porId('archivo-barra'),
  tituloCarga: porId('carga-titulo'),
  avisos: porId('archivo-avisos'),
  anuncio: porId('anuncio-general'),
  dialogo: porId('dialogo-cerrar'),
};

let configuracion = CONFIGURACION_POR_DEFECTO;
let pestanas;

function mostrarVista(vista) {
  const analisis = vista === 'analisis';
  el.vistaCarga.hidden = analisis;
  el.vistaAnalisis.hidden = !analisis;
  el.barraArchivo.hidden = !analisis;
  document.title = analisis ? TITULO_ANALISIS : TITULO_CARGA;
}

function pintarCabecera(dataset) {
  porId('archivo-nombre').textContent = dataset.nombre;
  porId('archivo-filas').textContent = entero(dataset.filas);
  porId('archivo-filas-unidad').textContent = dataset.filas === 1 ? 'fila' : 'filas';
  porId('archivo-columnas').textContent = entero(dataset.columnas.length);
  porId('archivo-columnas-unidad').textContent = dataset.columnas.length === 1 ? 'columna' : 'columnas';
}

function reiniciarVistas(dataset) {
  mostrarArchivoEnFrecuencias(dataset);
  mostrarArchivoEnCruce(dataset);
  mostrarArchivoEnDatos(dataset);
}

function abrirAnalisis(dataset, { recuperado = false } = {}) {
  abrirSesion(dataset);
  pintarCabecera(dataset);
  pintarAvisos(el.avisos, dataset.avisos);
  reiniciarVistas(dataset);
  pestanas.activar('frecuencias');
  mostrarVista('analisis');
  alAbrirDatos();
  if (recuperado) return; // al recargar la página no se mueve el foco ni se anuncia nada

  porId('tab-frecuencias').focus();
  const avisos = dataset.avisos.length > 0 ? ` ${cantidad(dataset.avisos.length, 'aviso', 'avisos')} sobre el archivo.` : '';
  anunciar(
    el.anuncio,
    `Archivo cargado: ${dataset.nombre}, ${cantidad(dataset.filas, 'fila', 'filas')} y ${cantidad(dataset.columnas.length, 'columna', 'columnas')}.${avisos}`,
  );
}

function volverACarga(aviso = '') {
  cerrarSesion();
  reiniciarVistas(null);
  pintarAvisos(el.avisos, []);
  reiniciarCarga();
  mostrarVista('carga');
  if (aviso) mostrarAvisoDeCarga(aviso);
  el.tituloCarga.focus();
}

function archivoCaducado() {
  if (!datasetActual()) return; // varias peticiones pueden fallar a la vez
  volverACarga(`Tu archivo ya no está disponible: DataTab cierra los archivos tras ${numero(configuracion.minutos_inactividad)} minutos sin uso. Vuelve a cargarlo.`);
}

function conectarCierre() {
  porId('btn-cerrar-archivo').addEventListener('click', () => {
    porId('dialogo-cerrar-nombre').textContent = datasetActual().nombre;
    el.dialogo.returnValue = '';
    el.dialogo.showModal();
  });

  el.dialogo.addEventListener('close', () => {
    const confirmado = el.dialogo.returnValue === 'cerrar';
    el.dialogo.returnValue = '';
    if (!confirmado) return; // Cancelar o Escape: el navegador devuelve el foco al botón
    const { dataset_id: id } = datasetActual();
    volverACarga();
    borrarDataset(id).catch(() => {
      mostrarAvisoDeCarga(`No se pudo avisar a DataTab de que cerraste el archivo. Se eliminará solo tras ${numero(configuracion.minutos_inactividad)} minutos sin uso.`);
    });
  });
}

async function recuperarSesion() {
  const id = idRecordado();
  if (!id) return;
  mostrarLeyendo(true);
  try {
    const dataset = await recuperarDataset(id);
    mostrarLeyendo(false);
    abrirAnalisis(dataset, { recuperado: true });
  } catch (error) {
    mostrarLeyendo(false);
    const fallo = comoErrorApi(error);
    if (fallo.codigo === 'ARCHIVO_NO_ENCONTRADO') {
      cerrarSesion();
      mostrarAvisoDeCarga('Tu archivo anterior ya no está disponible. Vuelve a cargarlo.');
    } else {
      mostrarErrorDeCarga(fallo);
    }
  }
}

async function arrancar() {
  let falloDeConfiguracion = null;
  try {
    configuracion = await obtenerConfiguracion();
  } catch (error) {
    falloDeConfiguracion = comoErrorApi(error);
  }

  const contexto = { alCaducar: archivoCaducado };
  iniciarCarga(configuracion, abrirAnalisis);
  iniciarFrecuencias(contexto);
  iniciarCruce(contexto);
  iniciarDatos(contexto);
  pestanas = iniciarPestanas(document.querySelector('[role="tablist"]'), () => {});
  conectarCierre();

  if (falloDeConfiguracion) mostrarErrorDeCarga(falloDeConfiguracion);
  await recuperarSesion();
}

arrancar();
