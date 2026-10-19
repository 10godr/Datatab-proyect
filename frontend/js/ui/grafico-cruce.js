// Gráfico de barras agrupadas del cruce: una serie por categoría de la columna, una agrupación por categoría de la fila.
// El canvas se describe con aria-label y la tabla trae los mismos datos completos.

import { cantidad, citar, porcentajeConSigno } from '../formato.js';
import { acortar, COLORES_BARRAS, esperarFuentes } from './grafico.js';

const MAX_FILAS_DIBUJABLES = 12;
const MAX_COLUMNAS_DIBUJABLES = 8;

let instancia = null;
let generacion = 0; // descarta dibujos que quedaron obsoletos mientras se esperaba a las fuentes
let elementos = null;

function buscarElementos() {
  elementos ??= {
    figura: document.getElementById('cruce-grafico'),
    titulo: document.getElementById('cruce-grafico-titulo'),
    lienzo: document.getElementById('cruce-lienzo'),
  };
  return elementos;
}

export function vaciarGraficoCruce() {
  const el = buscarElementos();
  generacion += 1;
  instancia?.destroy();
  instancia = null;
  el.titulo.textContent = '';
  el.lienzo.setAttribute('aria-label', 'Gráfico con los mismos datos que la tabla');
}

function crearGrafico(lienzo, r) {
  const estilos = getComputedStyle(document.documentElement);
  const color = (variable) => estilos.getPropertyValue(variable).trim();
  const quieto = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  Chart.defaults.font.family = color('--font-ui');
  Chart.defaults.font.size = 12;
  Chart.defaults.color = color('--text-2');

  return new Chart(lienzo, {
    type: 'bar',
    data: {
      labels: r.filas.map((fila) => fila.etiqueta),
      datasets: r.columnas.map((columna, j) => ({
        label: columna.etiqueta,
        data: r.filas.map((fila) => fila.celdas[j].frecuencia),
        backgroundColor: color(COLORES_BARRAS[j % COLORES_BARRAS.length]),
        borderRadius: 6,
        borderSkipped: false,
        animation: quieto ? false : { delay: (contexto) => contexto.dataIndex * 90 + j * 60 },
      })),
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: quieto ? false : { duration: 1000, easing: 'easeOutQuart' },
      layout: { padding: { top: 4 } },
      plugins: {
        legend: { position: 'top', align: 'start', labels: { boxWidth: 10, boxHeight: 10, padding: 14, color: color('--text-2') } },
        tooltip: {
          backgroundColor: color('--ink-1'),
          borderColor: color('--moss-500'),
          borderWidth: 1,
          cornerRadius: 10,
          titleColor: color('--text'),
          bodyColor: color('--text'),
          padding: 10,
          callbacks: {
            title: ([punto]) => `${r.fila.columna}: ${r.filas[punto.dataIndex].etiqueta}`,
            label: (punto) => {
              const celda = r.filas[punto.dataIndex].celdas[punto.datasetIndex];
              return `${punto.dataset.label}: ${cantidad(celda.frecuencia, 'registro', 'registros')} (${porcentajeConSigno(celda.porcentaje)} de la fila)`;
            },
          },
        },
      },
      scales: {
        x: { border: { display: false }, grid: { display: false }, ticks: { color: color('--text-2'), callback(valor) { return acortar(this.getLabelForValue(valor)); } } },
        y: {
          beginAtZero: true,
          border: { display: false },
          grid: { color: color('--line') },
          title: { display: true, text: 'Registros', color: color('--text-3') },
          ticks: { color: color('--text-3'), precision: 0, font: { family: color('--font-num') } },
        },
      },
    },
  });
}

/** Pinta el gráfico de un cruce; si hay demasiadas categorías para leerlo, lo oculta y la tabla sigue completa. */
export async function mostrarGraficoCruce(r) {
  const el = buscarElementos();
  vaciarGraficoCruce();
  const mia = generacion;

  const legible = r.filas.length <= MAX_FILAS_DIBUJABLES && r.columnas.length <= MAX_COLUMNAS_DIBUJABLES;
  el.figura.hidden = !legible;
  if (!legible) return;

  el.titulo.textContent = `Registros por ${r.fila.columna}, según ${r.columna.columna}`;
  el.lienzo.setAttribute(
    'aria-label',
    `Barras agrupadas: ${citar(r.fila.columna)} en el eje horizontal y una barra por cada valor de ${citar(r.columna.columna)}. Los datos completos están en la tabla.`,
  );

  await esperarFuentes();
  if (mia !== generacion) return;
  try {
    instancia = crearGrafico(el.lienzo, r);
  } catch {
    el.figura.hidden = true;
  }
}
