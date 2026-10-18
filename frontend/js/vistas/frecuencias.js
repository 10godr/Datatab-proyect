// Pestaña «Frecuencias»: columna (con rangos opcionales) -> tabla, gráfico y «Cómo leerlo».

import { calcularFrecuencias, comoErrorApi } from '../api.js';
import { datasetActual, guardarResultado, ultimoResultado } from '../estado.js';
import { cantidad, citar, entero, pistaColumna, porcentaje } from '../formato.js';
import { clonar, rellenar } from '../plantillas.js';
import { pintarAvisos } from '../ui/avisos.js';
import { mostrarGrafico, vaciarGrafico } from '../ui/grafico.js';
import { describirFrecuencias } from '../ui/lectura.js';
import {
  anunciar, columnaElegida, llenarColumnas, mostrarEstado, plegarSegunPantalla, rellenarError, vigilarPantalla,
} from '../ui/panel.js';
import { montarRangos } from '../ui/rangos.js';

const PREFIJO = 'frec';
const ERRORES_DE_RANGOS = new Set(['RANGO_NO_VALIDO', 'RANGO_REPETIDO', 'DEMASIADOS_RANGOS']);

let el;
let rangos;
let alCaducar;
let columnas = [];
let generacion = 0; // cada cálculo toma un número; una respuesta con número viejo no se pinta

export function iniciarFrecuencias({ alCaducar: alCaducarArchivo }) {
  alCaducar = alCaducarArchivo;
  const porId = (id) => document.getElementById(id);
  el = {
    formulario: porId('frec-form'),
    controles: porId('frec-controles'),
    resumen: porId('frec-controles-resumen'),
    columna: porId('frec-columna'),
    pista: porId('frec-columna-pista'),
    calcular: porId('frec-calcular'),
    anuncio: porId('frec-anuncio'),
    cargando: porId('frec-cargando'),
    error: porId('frec-error'),
    sinDatos: porId('frec-sin-datos'),
    resultado: porId('frec-resultado'),
    titulo: porId('frec-titulo'),
    n: porId('frec-n'),
    excluidas: porId('frec-excluidas'),
    avisos: porId('frec-avisos'),
    caption: porId('frec-caption'),
    encabezadoValor: porId('frec-encabezado-valor'),
    cuerpo: porId('frec-cuerpo'),
    pieEtiqueta: porId('frec-pie-etiqueta'),
    pieFrecuencia: porId('frec-pie-frecuencia'),
    piePorcentaje: porId('frec-pie-porcentaje'),
    graficoDetalles: porId('frec-grafico-detalles'),
    lecturaMuestra: porId('frec-lectura-muestra'),
    lecturaLectura: porId('frec-lectura-lectura'),
    lecturaLimites: porId('frec-lectura-limites'),
  };
  rangos = montarRangos(document.querySelector(`[data-montaje-rangos="${PREFIJO}"]`));
  el.calcular.setAttribute('aria-describedby', 'frec-columna-pista');

  el.columna.addEventListener('change', alCambiarColumna);
  el.formulario.addEventListener('submit', (evento) => {
    evento.preventDefault();
    calcular();
  });
  for (const radio of document.querySelectorAll('input[name="frec-tipo-grafico"]')) {
    radio.addEventListener('change', () => {
      const ultimo = ultimoResultado('frecuencias');
      if (ultimo) mostrarGrafico(ultimo.respuesta);
    });
  }
  vigilarPantalla([el.controles, el.graficoDetalles]);
}

/** Prepara la pestaña para un archivo nuevo (o la deja vacía si `dataset` es null al cerrar el archivo). */
export function mostrarArchivo(dataset) {
  generacion += 1;
  columnas = dataset?.columnas ?? [];
  llenarColumnas(el.columna, columnas, 'Elige una columna');
  alCambiarColumna();
  limpiarResultado();
  mostrarEstado(PREFIJO, 'vacio');
}

/** Borra del DOM lo que quedó del archivo anterior. */
function limpiarResultado() {
  const textos = [
    el.titulo, el.n, el.excluidas, el.caption, el.resumen, el.pieFrecuencia, el.piePorcentaje,
    el.lecturaMuestra, el.lecturaLectura, el.lecturaLimites,
  ];
  for (const elemento of textos) elemento.textContent = '';
  el.cuerpo.replaceChildren();
  pintarAvisos(el.avisos, []);
  vaciarGrafico();
}

function alCambiarColumna() {
  const columna = columnaElegida(el.columna, columnas);
  // Un cálculo en marcha ya no corresponde a lo elegido: se descarta y se vuelve al estado inicial
  if (!el.cargando.hidden) {
    generacion += 1;
    mostrarEstado(PREFIJO, 'vacio');
  }
  el.pista.textContent = columna ? pistaColumna(columna) : 'Elige una columna para poder calcular.';
  el.calcular.disabled = !columna;
  rangos.reiniciar(columna ? columna.tipo : null);
}

async function calcular() {
  const columna = columnaElegida(el.columna, columnas);
  if (!columna || !rangos.confirmarPendiente()) return;
  const lista = rangos.valores();
  const clave = JSON.stringify([columna.nombre, lista]);

  // Mismo cálculo que ya está en pantalla: no se vuelve a pedir al servidor
  if (ultimoResultado('frecuencias')?.clave === clave && !el.resultado.hidden) {
    anunciar(el.anuncio, 'El resultado no ha cambiado.');
    el.titulo.focus();
    return;
  }

  const mio = ++generacion;
  mostrarEstado(PREFIJO, 'cargando');
  try {
    const respuesta = await calcularFrecuencias(datasetActual().dataset_id, columna.nombre, lista);
    if (mio !== generacion) return;
    pintar(respuesta);
    guardarResultado('frecuencias', clave, respuesta);
  } catch (error) {
    if (mio !== generacion) return;
    mostrarFallo(comoErrorApi(error), columna);
  }
}

function mostrarFallo(error, columna) {
  if (error.codigo === 'ARCHIVO_NO_ENCONTRADO') {
    alCaducar();
    return;
  }
  if (error.codigo === 'SIN_DATOS') {
    el.sinDatos.querySelector('[data-campo="columna"]').textContent = columna.nombre;
    mostrarEstado(PREFIJO, 'sin-datos');
    el.sinDatos.focus();
    return;
  }
  let sugerencia = error.sugerencia;
  if (error.codigo === 'DEMASIADAS_CATEGORIAS') {
    sugerencia = columna.tipo === 'numerica'
      ? 'Agrupa los valores en rangos, por ejemplo 30-39, o elige otra columna.'
      : 'Elige otra columna.';
  }
  if (ERRORES_DE_RANGOS.has(error.codigo)) rangos.mostrarError(error.mensaje);
  rellenarError(el.error, error, sugerencia);
  mostrarEstado(PREFIJO, 'error');
  el.error.focus();
}

function pintarFilas(r) {
  const maxima = r.filas.reduce((mayor, fila) => Math.max(mayor, fila.frecuencia), 0);
  const fragmento = document.createDocumentFragment();
  for (const fila of r.filas) {
    const tr = clonar('tpl-frec-fila');
    tr.dataset.tipo = fila.tipo;
    // La barra de teléfono parte de cero y la mayor frecuencia ocupa todo el ancho
    tr.style.setProperty('--ancho', `${maxima > 0 ? (fila.frecuencia / maxima) * 100 : 0}%`);
    rellenar(tr, {
      etiqueta: fila.etiqueta,
      frecuencia: entero(fila.frecuencia),
      porcentaje: porcentaje(fila.porcentaje),
    });
    fragmento.append(tr);
  }
  el.cuerpo.replaceChildren(fragmento);
}

function pintar(r) {
  const rangosCalculados = r.filas.filter((fila) => fila.tipo === 'rango').length;
  const total = entero(r.n);

  el.titulo.textContent = r.agrupado
    ? `${r.columna} agrupada en ${cantidad(rangosCalculados, 'rango', 'rangos')}`
    : `Frecuencias de ${r.columna}`;
  el.n.textContent = total;
  el.excluidas.textContent = r.vacios_excluidos > 0
    ? ` · ${cantidad(r.vacios_excluidos, 'fila sin dato excluida', 'filas sin dato excluidas')}`
    : '';
  pintarAvisos(el.avisos, r.avisos);

  el.caption.textContent = `Registros de cada ${r.agrupado ? 'rango' : 'valor'} de ${citar(r.columna)} y su porcentaje sobre n = ${total}.`;
  el.encabezadoValor.textContent = r.agrupado ? `Rango de ${citar(r.columna)}` : 'Valor';
  pintarFilas(r);
  el.pieEtiqueta.textContent = r.solapados > 0 ? 'Base de cálculo' : 'Total';
  el.pieFrecuencia.textContent = total;
  el.piePorcentaje.textContent = porcentaje(100);

  const lectura = describirFrecuencias(r);
  el.lecturaMuestra.textContent = lectura.muestra;
  el.lecturaLectura.textContent = lectura.lectura;
  el.lecturaLimites.textContent = lectura.limites;

  el.resumen.textContent = r.agrupado ? `${r.columna} · ${cantidad(rangosCalculados, 'rango', 'rangos')}` : r.columna;
  mostrarEstado(PREFIJO, 'resultado');
  plegarSegunPantalla([el.controles, el.graficoDetalles]);
  mostrarGrafico(r);

  el.titulo.focus();
  anunciar(el.anuncio, `Frecuencias calculadas: ${cantidad(r.filas.length, 'fila', 'filas')}, n = ${total}.`);
}
