// Pestaña «Ver datos»: las filas del archivo, de 50 en 50.

import { comoErrorApi, obtenerFilas } from '../api.js';
import { datasetActual } from '../estado.js';
import { entero } from '../formato.js';
import { clonar } from '../plantillas.js';
import { anunciar, rellenarError, vigilarDesborde } from '../ui/panel.js';

const FILAS_POR_PAGINA = 50;

let el;
let alCaducar;
let generacion = 0; // una respuesta con número viejo no se pinta
let cargada = false; // ya hay una página en pantalla
let desde = 0;
let total = 0;

export function iniciarDatos({ alCaducar: alCaducarArchivo }) {
  alCaducar = alCaducarArchivo;
  const porId = (id) => document.getElementById(id);
  el = {
    anuncio: porId('datos-anuncio'),
    cargando: porId('datos-cargando'),
    error: porId('datos-error'),
    contenido: porId('datos-contenido'),
    desde: porId('datos-desde'),
    hasta: porId('datos-hasta'),
    total: porId('datos-total'),
    anterior: porId('datos-anterior'),
    siguiente: porId('datos-siguiente'),
    region: porId('datos-tabla').closest('.tabla-scroll'),
    caption: porId('datos-caption'),
    encabezado: porId('datos-encabezado'),
    cuerpo: porId('datos-cuerpo'),
  };
  vigilarDesborde(el.region, porId('datos-desliza'));
  // Los botones deshabilitados se explican con «Mostrando 1–50 de 200»
  for (const boton of [el.anterior, el.siguiente]) boton.setAttribute('aria-describedby', 'datos-rango');
  el.anterior.addEventListener('click', () => cargarPagina(desde - FILAS_POR_PAGINA));
  el.siguiente.addEventListener('click', () => cargarPagina(desde + FILAS_POR_PAGINA));
}

/** Prepara la pestaña para un archivo nuevo: no se pide nada hasta que se abra. */
export function mostrarArchivo() {
  generacion += 1;
  cargada = false;
  desde = 0;
  total = 0;
  el.cuerpo.replaceChildren();
  el.encabezado.replaceChildren(el.encabezado.firstElementChild); // queda solo «Fila»
  for (const texto of [el.desde, el.hasta, el.total]) texto.textContent = '';
  el.error.hidden = true;
  el.cargando.hidden = true;
  el.contenido.hidden = false;
}

/** Al abrir la pestaña: carga la primera página solo la primera vez (o si la anterior falló). */
export function alAbrirDatos() {
  if (!cargada) cargarPagina(0);
}

async function cargarPagina(inicio) {
  const mio = ++generacion;
  el.error.hidden = true;
  // La primera carga muestra el indicador; al cambiar de página se conserva la tabla hasta que llegue la nueva
  if (!cargada) {
    el.contenido.hidden = true;
    el.cargando.hidden = false;
  }
  el.region.setAttribute('aria-busy', 'true');
  try {
    const respuesta = await obtenerFilas(datasetActual().dataset_id, Math.max(0, inicio), FILAS_POR_PAGINA);
    if (mio !== generacion) return;
    pintar(respuesta);
  } catch (error) {
    if (mio !== generacion) return;
    mostrarFallo(comoErrorApi(error));
  } finally {
    if (mio === generacion) el.region.removeAttribute('aria-busy');
  }
}

function mostrarFallo(error) {
  if (error.codigo === 'ARCHIVO_NO_ENCONTRADO') {
    alCaducar();
    return;
  }
  rellenarError(el.error, error);
  el.cargando.hidden = true;
  el.contenido.hidden = !cargada;
  el.error.hidden = false;
  el.error.focus();
}

function pintarEncabezado(nombres) {
  if (el.encabezado.children.length === nombres.length + 1) return; // las columnas no cambian dentro de un archivo
  const fragmento = document.createDocumentFragment();
  for (const nombre of nombres) {
    const th = clonar('tpl-datos-columna');
    th.textContent = nombre;
    fragmento.append(th);
  }
  el.encabezado.replaceChildren(el.encabezado.firstElementChild, fragmento);
}

function pintarFilas(respuesta) {
  const fragmento = document.createDocumentFragment();
  respuesta.filas.forEach((celdas, indice) => {
    const tr = clonar('tpl-datos-fila');
    tr.firstElementChild.textContent = entero(respuesta.desde + indice + 1);
    for (const valor of celdas) {
      const td = clonar('tpl-datos-celda');
      td.textContent = valor; // una celda vacía queda sin texto: el CSS pinta la raya
      tr.append(td);
    }
    fragmento.append(tr);
  });
  el.cuerpo.replaceChildren(fragmento);
}

function pintar(respuesta) {
  const enfocado = document.activeElement;
  desde = respuesta.desde;
  total = respuesta.total;
  const hasta = desde + respuesta.cantidad;

  pintarEncabezado(respuesta.columnas);
  pintarFilas(respuesta);
  el.region.scrollTop = 0;
  el.desde.textContent = entero(respuesta.cantidad > 0 ? desde + 1 : 0);
  el.hasta.textContent = entero(hasta);
  el.total.textContent = entero(total);
  el.caption.textContent = `Filas ${entero(desde + 1)} a ${entero(hasta)} del archivo, de ${FILAS_POR_PAGINA} en ${FILAS_POR_PAGINA}`;
  el.anterior.disabled = desde === 0;
  el.siguiente.disabled = hasta >= total;

  el.cargando.hidden = true;
  el.contenido.hidden = false;
  cargada = true;

  // Si el botón pulsado queda deshabilitado (primera o última página) se perdería el foco: pasa al otro botón
  if ((enfocado === el.anterior || enfocado === el.siguiente) && enfocado.disabled) {
    const otro = enfocado === el.anterior ? el.siguiente : el.anterior;
    (otro.disabled ? el.region : otro).focus();
  }
  const paginas = Math.max(1, Math.ceil(total / FILAS_POR_PAGINA));
  anunciar(el.anuncio, `Página ${entero(Math.floor(desde / FILAS_POR_PAGINA) + 1)} de ${entero(paginas)}: filas ${entero(desde + 1)} a ${entero(hasta)} de ${entero(total)}.`);
}
