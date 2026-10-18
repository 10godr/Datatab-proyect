// Piezas comunes de las vistas con resultados: estados, anuncios, plegables y aviso de tablas que se desplazan.

const ESTADOS = ['vacio', 'cargando', 'error', 'sin-datos', 'resultado'];
const CONSULTA_TELEFONO = '(max-width: 640px)';

export const esTelefono = () => window.matchMedia(CONSULTA_TELEFONO).matches;

/** Muestra uno de los cinco estados del panel (#PREFIJO-vacio, -cargando, -error, -sin-datos, -resultado). */
export function mostrarEstado(prefijo, activo) {
  for (const estado of ESTADOS) {
    document.getElementById(`${prefijo}-${estado}`).hidden = estado !== activo;
  }
}

/** Escribe mensaje y sugerencia de un error en su bloque ([data-campo]). */
export function rellenarError(bloque, error, sugerencia = error.sugerencia) {
  bloque.querySelector('[data-campo="mensaje"]').textContent = error.mensaje;
  bloque.querySelector('[data-campo="sugerencia"]').textContent = sugerencia ?? '';
}

/** Escribe un anuncio en una región aria-live. Si el texto no cambia, la vacía antes para que se vuelva a leer. */
export function anunciar(region, texto) {
  if (region.textContent === texto) {
    region.textContent = '';
    setTimeout(() => { region.textContent = texto; }, 50);
  } else {
    region.textContent = texto;
  }
}

/** En teléfono pliega los <details> (controles y gráfico) tras calcular; en escritorio los abre. */
export function plegarSegunPantalla(detalles) {
  const abrir = !esTelefono();
  for (const detalle of detalles) detalle.open = abrir;
}

/** Al pasar a escritorio abre los <details>: sin ::details-content algunos navegadores los dejarían cerrados. */
export function vigilarPantalla(detalles) {
  window.matchMedia(CONSULTA_TELEFONO).addEventListener('change', (evento) => {
    if (!evento.matches) for (const detalle of detalles) detalle.open = true;
  });
}

/** Muestra la pista de desplazamiento solo mientras la tabla no cabe en su región (se recalcula al cambiar cualquiera de las dos). */
export function vigilarDesborde(region, pista) {
  const observador = new ResizeObserver(() => {
    pista.hidden = region.scrollWidth <= region.clientWidth;
  });
  observador.observe(region);
  observador.observe(region.querySelector('table'));
}

/** Rellena un <select> con una opción inicial vacía y una por columna (los nombres entran como texto). */
export function llenarColumnas(select, columnas, textoInicial) {
  select.replaceChildren(new Option(textoInicial, ''), ...columnas.map((columna) => new Option(columna.nombre, columna.nombre)));
}

/** La columna elegida en el select (o undefined si sigue la opción inicial). */
export const columnaElegida = (select, columnas) => columnas[select.selectedIndex - 1];
