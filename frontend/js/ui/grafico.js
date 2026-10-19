// Gráfico de frecuencias con Chart.js (variable global `Chart`, que carga index.html antes de los módulos).
// El canvas se describe con aria-label y la tabla trae los mismos datos completos.

import { cantidad, citar, entero, porcentajeConSigno } from '../formato.js';

const MAX_VALORES_DIBUJABLES = 60;
const MAX_CATEGORIAS_VERTICAL = 5; // con más categorías las barras van en horizontal
const LARGO_MAXIMO_ETIQUETA = 28;
// Orden de colores de las categorías: rosa suave primero. Una sola serie va en --signal.
export const COLORES_BARRAS = ['--c-green', '--c-rose', '--c-blue', '--c-ochre', '--c-violet', '--c-teal', '--c-coral', '--c-lime'];
const COLORES_CATEGORIAS = ['--c-rose', '--c-white', '--c-blue', '--c-ochre', '--c-violet', '--c-gray'];

let instancia = null;
let generacion = 0; // descarta dibujos que quedaron obsoletos mientras se esperaba a las fuentes
let fuentes = null;
let elementos = null;
let textoPistaOriginal = '';

function buscarElementos() {
  if (!elementos) {
    const porId = (id) => document.getElementById(id);
    const radio = (valor) => document.querySelector(`input[name="frec-tipo-grafico"][value="${valor}"]`);
    elementos = {
      figura: porId('frec-grafico'),
      selector: porId('frec-grafico-tipo'),
      lienzo: porId('frec-lienzo'),
      titulo: porId('frec-grafico-titulo'),
      muchas: porId('frec-grafico-muchas'),
      cantidad: porId('frec-grafico-muchas').querySelector('[data-campo="cantidad"]'),
      pista: porId('frec-circular-pista'),
      barras: radio('barras'),
      circular: radio('circular'),
    };
    textoPistaOriginal = elementos.pista.textContent;
  }
  return elementos;
}

/** Espera a que estén cargadas las fuentes Atkinson: el canvas no repinta solo cuando llegan. */
export function esperarFuentes() {
  fuentes ??= Promise.all([
    document.fonts.load('400 12px "Atkinson Hyperlegible Next"'),
    document.fonts.load('500 12px "Atkinson Hyperlegible Mono"'),
  ]).catch(() => {}); // sin fuentes se dibuja con la de reserva
  return fuentes;
}

export function destruirGrafico() {
  generacion += 1;
  instancia?.destroy();
  instancia = null;
}

/** Deja el gráfico sin rastro del archivo anterior. */
export function vaciarGrafico() {
  const el = buscarElementos();
  destruirGrafico();
  el.titulo.textContent = '';
  el.lienzo.setAttribute('aria-label', 'Gráfico con los mismos datos que la tabla');
}

export const acortar = (texto) => (texto.length > LARGO_MAXIMO_ETIQUETA ? `${texto.slice(0, LARGO_MAXIMO_ETIQUETA - 1)}…` : texto);

function descripcion(r, tipo) {
  const mayor = r.filas.reduce((a, fila) => (fila.frecuencia > a.frecuencia ? fila : a));
  const clase = tipo === 'circular' ? 'Gráfico circular' : 'Gráfico de barras';
  return `${clase} de ${citar(r.columna)} con ${cantidad(r.filas.length, 'categoría', 'categorías')}. `
    + `La mayor es ${citar(mayor.etiqueta)}, con ${cantidad(mayor.frecuencia, 'registro', 'registros')} (${porcentajeConSigno(mayor.porcentaje)}). `
    + 'Los mismos datos están en la tabla.';
}

/** Dibuja la cifra de cada barra en su extremo (Chart.js no trae etiquetas de valor). */
const etiquetasDeValor = {
  id: 'etiquetasDeValor',
  afterDatasetsDraw(grafico) {
    const { ctx, data } = grafico;
    const horizontal = grafico.options.indexAxis === 'y';
    const estilos = getComputedStyle(document.documentElement);
    ctx.save();
    ctx.font = `500 12px ${estilos.getPropertyValue('--font-num')}`;
    ctx.fillStyle = estilos.getPropertyValue('--text');
    ctx.textAlign = horizontal ? 'left' : 'center';
    ctx.textBaseline = horizontal ? 'middle' : 'bottom';
    grafico.getDatasetMeta(0).data.forEach((barra, indice) => {
      const texto = entero(data.datasets[0].data[indice]);
      if (horizontal) ctx.fillText(texto, barra.x + 6, barra.y);
      else ctx.fillText(texto, barra.x, barra.y - 4);
    });
    ctx.restore();
  },
};

function crearGrafico(lienzo, tipo, r) {
  const estilos = getComputedStyle(document.documentElement);
  const color = (variable) => estilos.getPropertyValue(variable).trim();
  const filas = r.filas;
  const etiquetas = filas.map((fila) => fila.etiqueta);
  const valores = filas.map((fila) => fila.frecuencia);

  Chart.defaults.font.family = color('--font-ui');
  Chart.defaults.font.size = 12;
  Chart.defaults.color = color('--text-2');

  const tooltip = {
    backgroundColor: color('--ink-1'),
    borderColor: color('--moss-500'),
    cornerRadius: 10,
    borderWidth: 1,
    titleColor: color('--text'),
    bodyColor: color('--text'),
    padding: 10,
    displayColors: tipo === 'circular',
    callbacks: {
      title: ([punto]) => filas[punto.dataIndex].etiqueta,
      label: (punto) => {
        const fila = filas[punto.dataIndex];
        return `${cantidad(fila.frecuencia, 'registro', 'registros')} (${porcentajeConSigno(fila.porcentaje)})`;
      },
    },
  };
  const quieto = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const base = { responsive: true, maintainAspectRatio: false, animation: quieto ? false : { duration: 1100, easing: 'easeOutQuart' } };

  if (tipo === 'circular') {
    return new Chart(lienzo, {
      type: 'doughnut',
      data: {
        labels: etiquetas,
        datasets: [{
          data: valores,
          backgroundColor: COLORES_CATEGORIAS.slice(0, filas.length).map(color),
          borderColor: color('--ink-1'),
          borderWidth: 3,
          hoverOffset: 10,
        }],
      },
      options: {
        ...base,
        cutout: '58%',
        animation: quieto ? false : { duration: 1200, easing: 'easeOutQuart', animateRotate: true, animateScale: true },
        plugins: {
          tooltip,
          legend: {
            position: 'bottom',
            onClick: () => {}, // ocultar una parte haría que las demás dejaran de sumar el total
            labels: {
              color: color('--text-2'),
              boxWidth: 10,
              boxHeight: 10,
              padding: 14,
              generateLabels(grafico) {
                const elementos = Chart.overrides.doughnut.plugins.legend.labels.generateLabels(grafico);
                for (const elemento of elementos) {
                  elemento.text = `${acortar(filas[elemento.index].etiqueta)} · ${porcentajeConSigno(filas[elemento.index].porcentaje)}`;
                }
                return elementos;
              },
            },
          },
        },
      },
    });
  }

  const horizontal = filas.length > MAX_CATEGORIAS_VERTICAL;
  const margenCifra = entero(Math.max(...valores)).length * 8 + 14;
  const ejeValores = {
    beginAtZero: true,
    border: { display: false },
    grid: { color: color('--line') },
    title: { display: true, text: 'Registros', color: color('--text-3') },
    ticks: { color: color('--text-3'), precision: 0, font: { family: color('--font-num') } },
  };
  const ejeCategorias = {
    border: { display: false },
    grid: { display: false },
    ticks: {
      color: color('--text-2'),
      callback(valor) { return acortar(this.getLabelForValue(valor)); },
    },
  };
  return new Chart(lienzo, {
    type: 'bar',
    plugins: [etiquetasDeValor],
    data: {
      labels: etiquetas,
      datasets: [{
        data: valores,
        backgroundColor: valores.map((_, i) => color(COLORES_BARRAS[i % COLORES_BARRAS.length])),
        borderRadius: 8,
        borderSkipped: false,
        barPercentage: 0.68,
        categoryPercentage: 1,
        animation: quieto ? false : { delay: (contexto) => contexto.dataIndex * 110 },
      }],
    },
    options: {
      ...base,
      indexAxis: horizontal ? 'y' : 'x',
      layout: { padding: horizontal ? { right: margenCifra } : { top: 22 } },
      plugins: { legend: { display: false }, tooltip },
      scales: horizontal ? { x: ejeValores, y: ejeCategorias } : { x: ejeCategorias, y: ejeValores },
    },
  });
}

/** Alto del gráfico según el tipo y el número de categorías (variable --alto-grafico). */
function altoDelGrafico(tipo, categorias) {
  if (tipo === 'circular') return '20rem';
  return categorias > MAX_CATEGORIAS_VERTICAL ? `calc(${categorias} * 2.6rem + 3.5rem)` : '18rem';
}

/**
 * Pinta el gráfico de una respuesta de frecuencias, o el aviso de «muchas categorías» si no se puede leer.
 * Lee el tipo de los radios; el circular se deshabilita cuando no corresponde.
 */
export async function mostrarGrafico(r) {
  const el = buscarElementos();
  destruirGrafico();
  const mia = generacion;

  const demasiados = r.filas.length > MAX_VALORES_DIBUJABLES;
  el.figura.hidden = demasiados;
  el.selector.hidden = true; // el tipo no se elige: 2 categorías = circular, el resto = barras
  el.muchas.hidden = !demasiados;
  if (demasiados) {
    el.cantidad.textContent = entero(r.filas.length);
    return;
  }

  const tipo = r.filas.length === 2 && r.solapados === 0 ? 'circular' : 'barras';

  el.titulo.textContent = `Registros por ${r.agrupado ? 'rango' : 'valor'} de ${r.columna}`;
  el.lienzo.setAttribute('aria-label', descripcion(r, tipo));
  el.lienzo.parentElement.style.setProperty('--alto-grafico', altoDelGrafico(tipo, r.filas.length));

  await esperarFuentes();
  if (mia !== generacion) return;
  try {
    instancia = crearGrafico(el.lienzo, tipo, r);
  } catch {
    el.figura.hidden = true; // la tabla sigue completa
  }
}
