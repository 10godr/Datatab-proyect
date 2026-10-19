// Pestaña «Cruce de variables»: dos columnas (con rangos opcionales en cada una) -> tabla cruzada.

import { calcularCruce, comoErrorApi } from '../api.js';
import { datasetActual, guardarResultado, ultimoResultado } from '../estado.js';
import { cantidad, citar, entero, pistaColumna, porcentaje } from '../formato.js';
import { clonar, rellenar } from '../plantillas.js';
import { mostrarGraficoCruce, vaciarGraficoCruce } from '../ui/grafico-cruce.js';
import { pintarAvisos } from '../ui/avisos.js';
import { describirCruce } from '../ui/lectura.js';
import {
  anunciar, columnaElegida, conPausaMinima, llenarColumnas, mostrarEstado, plegarSegunPantalla, rellenarError, vigilarDesborde, vigilarPantalla,
} from '../ui/panel.js';
import { montarRangos } from '../ui/rangos.js';

const PREFIJO = 'cruce';
const ERRORES_DE_RANGOS = new Set(['RANGO_NO_VALIDO', 'RANGO_REPETIDO', 'DEMASIADOS_RANGOS']);
const PISTA_SIN_ELEGIR = 'Elige una variable para poder generar la tabla.';

let el;
let ejes; // [{ select, pista, rangos }]: filas y columnas
let alCaducar;
let columnas = [];
let generacion = 0; // una respuesta con número viejo no se pinta

export function iniciarCruce({ alCaducar: alCaducarArchivo }) {
  alCaducar = alCaducarArchivo;
  const porId = (id) => document.getElementById(id);
  el = {
    formulario: porId('cruce-form'),
    controles: porId('cruce-controles'),
    resumen: porId('cruce-controles-resumen'),
    generar: porId('cruce-generar'),
    anuncio: porId('cruce-anuncio'),
    cargando: porId('cruce-cargando'),
    error: porId('cruce-error'),
    sinDatos: porId('cruce-sin-datos'),
    resultado: porId('cruce-resultado'),
    titulo: porId('cruce-titulo'),
    n: porId('cruce-n'),
    excluidas: porId('cruce-excluidas'),
    avisos: porId('cruce-avisos'),
    caption: porId('cruce-caption'),
    variableFila: porId('cruce-variable-fila'),
    variableColumna: porId('cruce-variable-columna'),
    encabezado: porId('cruce-encabezado'),
    subencabezado: porId('cruce-subencabezado'),
    cuerpo: porId('cruce-cuerpo'),
    pie: porId('cruce-pie'),
    lecturaMuestra: porId('cruce-lectura-muestra'),
    lecturaLectura: porId('cruce-lectura-lectura'),
    lecturaLimites: porId('cruce-lectura-limites'),
  };
  ejes = ['cruce-fila', 'cruce-columna'].map((prefijo) => ({
    select: porId(`${prefijo}-columna`),
    pista: porId(`${prefijo}-pista`),
    rangos: montarRangos(document.querySelector(`[data-montaje-rangos="${prefijo}"]`)),
  }));
  el.generar.setAttribute('aria-describedby', ejes.map((eje) => eje.pista.id).join(' '));

  for (const eje of ejes) eje.select.addEventListener('change', () => alCambiarColumna(eje));
  el.formulario.addEventListener('submit', (evento) => {
    evento.preventDefault();
    calcular();
  });
  vigilarPantalla([el.controles]);
  vigilarDesborde(porId('cruce-tabla').closest('.tabla-scroll'), porId('cruce-desliza'));
}

/** Prepara la pestaña para un archivo nuevo (o la deja vacía si `dataset` es null al cerrar el archivo). */
export function mostrarArchivo(dataset) {
  generacion += 1;
  columnas = dataset?.columnas ?? [];
  for (const eje of ejes) {
    llenarColumnas(eje.select, columnas, 'Elige una columna');
    actualizarEje(eje);
  }
  actualizarBoton();
  limpiarResultado();
  mostrarEstado(PREFIJO, 'vacio');
}

/** Borra del DOM lo que quedó del archivo anterior. */
function limpiarResultado() {
  const textos = [
    el.titulo, el.n, el.excluidas, el.caption, el.resumen, el.variableFila, el.variableColumna,
    el.lecturaMuestra, el.lecturaLectura, el.lecturaLimites,
  ];
  for (const elemento of textos) elemento.textContent = '';
  el.encabezado.replaceChildren();
  el.subencabezado.replaceChildren();
  el.cuerpo.replaceChildren();
  quitarCeldasDelPie();
  vaciarGraficoCruce();
  pintarAvisos(el.avisos, []);
}

function quitarCeldasDelPie() {
  for (const celda of el.pie.querySelectorAll('td')) celda.remove();
}

function actualizarEje(eje) {
  const columna = columnaElegida(eje.select, columnas);
  eje.pista.textContent = columna ? pistaColumna(columna) : PISTA_SIN_ELEGIR;
  eje.rangos.reiniciar(columna ? columna.tipo : null);
}

function actualizarBoton() {
  el.generar.disabled = ejes.some((eje) => !columnaElegida(eje.select, columnas));
}

function alCambiarColumna(eje) {
  // Un cálculo en marcha ya no corresponde a lo elegido: se descarta y se vuelve al estado inicial
  if (!el.cargando.hidden) {
    generacion += 1;
    mostrarEstado(PREFIJO, 'vacio');
  }
  actualizarEje(eje);
  actualizarBoton();
}

async function calcular() {
  const [fila, columna] = ejes.map((eje) => columnaElegida(eje.select, columnas));
  if (!fila || !columna) return;
  if (fila.nombre === columna.nombre) {
    mostrarFallo({
      codigo: 'COLUMNAS_IGUALES',
      mensaje: `Has elegido ${citar(fila.nombre)} como variable de las filas y de las columnas.`,
      sugerencia: 'Elige dos variables distintas para cruzarlas.',
    });
    return;
  }
  if (!ejes.every((eje) => eje.rangos.confirmarPendiente())) return;

  const [rangosFila, rangosColumna] = ejes.map((eje) => eje.rangos.valores());
  const clave = JSON.stringify([fila.nombre, rangosFila, columna.nombre, rangosColumna]);

  // Mismo cálculo que ya está en pantalla: no se vuelve a pedir al servidor
  if (ultimoResultado('cruce')?.clave === clave && !el.resultado.hidden) {
    anunciar(el.anuncio, 'El resultado no ha cambiado.');
    el.titulo.focus();
    return;
  }

  const mio = ++generacion;
  mostrarEstado(PREFIJO, 'cargando');
  try {
    const respuesta = await conPausaMinima(calcularCruce(
      datasetActual().dataset_id,
      { columna: fila.nombre, rangos: rangosFila },
      { columna: columna.nombre, rangos: rangosColumna },
    ));
    if (mio !== generacion) return;
    pintar(respuesta);
    guardarResultado('cruce', clave, respuesta);
  } catch (error) {
    if (mio !== generacion) return;
    mostrarFallo(comoErrorApi(error));
  }
}

function mostrarFallo(error) {
  if (error.codigo === 'ARCHIVO_NO_ENCONTRADO') {
    alCaducar();
    return;
  }
  if (error.codigo === 'SIN_DATOS') {
    mostrarEstado(PREFIJO, 'sin-datos');
    el.sinDatos.focus();
    return;
  }
  if (ERRORES_DE_RANGOS.has(error.codigo)) {
    for (const eje of ejes) if (eje.rangos.contiene(error.detalle?.rango)) eje.rangos.mostrarError(error.mensaje);
  }
  rellenarError(el.error, error);
  mostrarEstado(PREFIJO, 'error');
  el.error.focus();
}

function celda(texto, clase = 'n') {
  const td = document.createElement('td');
  td.className = clase;
  td.textContent = texto;
  return td;
}

function cabecera(texto, { colSpan = 1, tipo, clase = 'n' } = {}) {
  const th = document.createElement('th');
  th.scope = colSpan > 1 ? 'colgroup' : 'col';
  th.className = clase;
  th.colSpan = colSpan;
  if (tipo) th.dataset.tipo = tipo;
  th.textContent = texto;
  return th;
}

/** Frecuencia y porcentaje en celdas separadas, como en una tabla de tesis. */
function celdasFrPct(celdaDatos) {
  return [celda(entero(celdaDatos.frecuencia)), celda(porcentaje(celdaDatos.porcentaje), 'n n--pct')];
}

function pintarTabla(r) {
  el.variableFila.textContent = r.fila.columna;
  el.variableColumna.textContent = r.columna.columna;
  el.variableColumna.colSpan = (r.columnas.length + 1) * 2;

  const categorias = [...r.columnas.map((c) => ({ texto: c.etiqueta, tipo: c.tipo })), { texto: 'Total' }];
  el.encabezado.replaceChildren(...categorias.map((c) => cabecera(c.texto, { colSpan: 2, tipo: c.tipo })));
  el.subencabezado.replaceChildren(...categorias.flatMap(() => [cabecera('Fr'), cabecera('%')]));

  const filas = document.createDocumentFragment();
  for (const fila of r.filas) {
    const tr = clonar('tpl-cruce-fila');
    tr.dataset.tipo = fila.tipo;
    rellenar(tr, { etiqueta: fila.etiqueta });
    tr.append(...fila.celdas.flatMap(celdasFrPct), celda(entero(fila.total)), celda('100,0', 'n n--pct'));
    filas.append(tr);
  }
  el.cuerpo.replaceChildren(filas);

  quitarCeldasDelPie();
  el.pie.append(...r.totales_columna.flatMap(celdasFrPct), celda(entero(r.n)), celda('100,0', 'n n--pct'));
}

function pintar(r) {
  const total = entero(r.n);
  el.titulo.textContent = `Cruce de ${r.fila.columna} y ${r.columna.columna}`;
  el.n.textContent = total;
  el.excluidas.textContent = r.vacios_excluidos > 0
    ? ` · ${cantidad(r.vacios_excluidos, 'fila sin dato excluida', 'filas sin dato excluidas')}`
    : '';
  pintarAvisos(el.avisos, r.avisos);
  el.caption.textContent = `Registros según ${citar(r.fila.columna)} (filas) y ${citar(r.columna.columna)} (columnas). `
    + `Cada porcentaje es la parte de su fila; en el total, del conjunto. n = ${total}.`;
  pintarTabla(r);
  mostrarGraficoCruce(r);

  const lectura = describirCruce(r);
  el.lecturaMuestra.textContent = lectura.muestra;
  el.lecturaLectura.textContent = lectura.lectura;
  el.lecturaLimites.textContent = lectura.limites;

  el.resumen.textContent = `${r.fila.columna} × ${r.columna.columna}`;
  mostrarEstado(PREFIJO, 'resultado');
  plegarSegunPantalla([el.controles]);
  el.titulo.focus();
  anunciar(
    el.anuncio,
    `Tabla calculada: ${cantidad(r.filas.length, 'fila', 'filas')} por ${cantidad(r.columnas.length, 'columna', 'columnas')}, n = ${total}.`,
  );
}
