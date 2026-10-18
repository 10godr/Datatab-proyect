// Rangos numéricos: interpretación de la sintaxis (idéntica a docs/api.md y al servidor) y pieza
// reutilizable de formulario. Las funciones puras no tocan el DOM; el servidor repite la validación.

import { citar, numero } from '../formato.js';
import { clonar, clonarConPrefijo, rellenar } from '../plantillas.js';

export const MAX_RANGOS = 50;
const MAX_LONGITUD = 40;
const PAUSA_VALIDACION_MS = 500;

const SIMBOLOS = { '≤': '<=', '≥': '>=', '＜': '<', '＞': '>', '–': '-', '—': '-', '−': '-' };
const NUM = String.raw`-?(?:[0-9]+(?:[.,][0-9]+)?|[.,][0-9]+)`;
const COMPARACION = new RegExp(String.raw`^(<=|>=|<|>)\s*(${NUM})$`);
const O_MAS = new RegExp(String.raw`^(${NUM})\s*\+$`);
const ENTRE = new RegExp(String.raw`^(${NUM})\s*-\s*(${NUM})$`);

const aNumero = (texto) => Number(texto.replace(',', '.'));

function entendido(texto, etiqueta, minimo, incluyeMinimo, maximo, incluyeMaximo) {
  // Dos rangos con la misma clave significan lo mismo (40+ y >=40)
  const clave = `${minimo}|${incluyeMinimo}|${maximo}|${incluyeMaximo}`;
  return { ok: true, texto, etiqueta, minimo, incluyeMinimo, maximo, incluyeMaximo, clave };
}

/**
 * Interpreta un rango escrito por la persona: <30, <=30 o ≤30, >60, >=60 o ≥60, 40+, 30-39 (o 30–39).
 * Devuelve { ok: true, texto, etiqueta, clave, ... } o { ok: false, motivo: 'vacio' | 'largo' | 'invertido' | 'no_valido', texto }.
 */
export function interpretarRango(entrada) {
  const texto = entrada.trim();
  if (texto === '') return { ok: false, motivo: 'vacio', texto };
  if ([...texto].length > MAX_LONGITUD) return { ok: false, motivo: 'largo', texto };
  const normalizado = texto.replace(/[≤≥＜＞–—−]/g, (simbolo) => SIMBOLOS[simbolo]);

  const comparacion = COMPARACION.exec(normalizado);
  if (comparacion) {
    const limite = aNumero(comparacion[2]);
    const n = numero(limite);
    switch (comparacion[1]) {
      case '<': return entendido(texto, `Menos de ${n}`, -Infinity, false, limite, false);
      case '<=': return entendido(texto, `${n} o menos`, -Infinity, false, limite, true);
      case '>': return entendido(texto, `Más de ${n}`, limite, false, Infinity, false);
      default: return entendido(texto, `${n} o más`, limite, true, Infinity, false);
    }
  }

  const oMas = O_MAS.exec(normalizado);
  if (oMas) {
    const limite = aNumero(oMas[1]);
    return entendido(texto, `${numero(limite)} o más`, limite, true, Infinity, false);
  }

  const entre = ENTRE.exec(normalizado);
  if (entre) {
    const desde = aNumero(entre[1]);
    const hasta = aNumero(entre[2]);
    if (desde > hasta) return { ok: false, motivo: 'invertido', texto };
    return entendido(texto, `${numero(desde)} a ${numero(hasta)}`, desde, true, hasta, true);
  }

  return { ok: false, motivo: 'no_valido', texto };
}

const recortar = (texto) => ([...texto].length > 24 ? `${[...texto].slice(0, 24).join('')}…` : texto);

const MENSAJES = {
  vacio: () => 'Escribe un rango, por ejemplo 30-39.',
  largo: () => 'El rango es demasiado largo. Escribe uno corto, como 30-39.',
  invertido: (texto) => `En ${citar(recortar(texto))} el primer número es mayor que el segundo. Escribe primero el menor, por ejemplo 30-39.`,
  no_valido: (texto) => `No se entiende ${citar(recortar(texto))}. Escribe un rango como 30-39, <30, >=60 o 40+.`,
};

/**
 * Valida un rango nuevo frente a los ya añadidos (por significado, no por texto).
 * Devuelve { ok: true, rango } o { ok: false, mensaje }.
 */
export function validarRango(entrada, existentes) {
  const rango = interpretarRango(entrada);
  if (!rango.ok) return { ok: false, mensaje: MENSAJES[rango.motivo](rango.texto) };
  if (existentes.length >= MAX_RANGOS) {
    return { ok: false, mensaje: `Ya hay ${MAX_RANGOS} rangos, que es el máximo.` };
  }
  const repetido = existentes.map(interpretarRango).find((r) => r.ok && r.clave === rango.clave);
  if (repetido) {
    const igual = repetido.texto === rango.texto ? '' : `: significa lo mismo que ${citar(repetido.texto)}`;
    return { ok: false, mensaje: `${citar(rango.texto)} ya está añadido${igual}.` };
  }
  return { ok: true, rango };
}

/**
 * Separa lo escrito en varios rangos: por ; , salto de línea, «coma y espacio» o « y ».
 * Una coma sin espacio puede ser un decimal (1,5), así que solo separa si el trozo no se entiende entero.
 */
export function separarRangos(entrada) {
  const trozos = entrada.split(/[;\n]+|,\s+|\s+y\s+/).map((t) => t.trim()).filter((t) => t !== '');
  return trozos.flatMap((trozo) => {
    if (trozo.includes(',') && !interpretarRango(trozo).ok) {
      const partes = trozo.split(',').map((t) => t.trim()).filter((t) => t !== '');
      if (partes.every((parte) => interpretarRango(parte).ok)) return partes;
    }
    return [trozo];
  });
}

/**
 * Monta la pieza de rangos en un elemento [data-montaje-rangos] y devuelve su controlador:
 * valores(), reiniciar(tipo), confirmarPendiente(), mostrarError(texto), contiene(texto), enfocar().
 */
export function montarRangos(punto) {
  punto.replaceChildren(clonarConPrefijo('tpl-rangos', punto.dataset.montajeRangos));
  const raiz = punto.querySelector('[data-rangos]');
  const lista = raiz.querySelector('[data-rangos-lista]');
  const entrada = raiz.querySelector('[data-rangos-entrada]');
  const boton = raiz.querySelector('[data-rangos-anadir]');
  const mensaje = raiz.querySelector('[data-rangos-mensaje]');
  const avisoTipo = raiz.querySelector('[data-rangos-aviso-tipo]');
  const textoAvisoTipo = avisoTipo.textContent;
  raiz.querySelector('[data-rangos-contexto]').textContent = punto.dataset.contexto ?? '';

  let rangos = [];
  let pausa = 0;

  function mostrar(texto, nivel) {
    mensaje.dataset.nivel = nivel;
    mensaje.textContent = texto;
  }

  function limpiarMensaje() {
    mensaje.textContent = '';
    delete mensaje.dataset.nivel;
    entrada.removeAttribute('aria-invalid');
  }

  function rechazar(texto) {
    mostrar(texto, 'error');
    entrada.setAttribute('aria-invalid', 'true');
  }

  function anadir() {
    clearTimeout(pausa);
    const trozos = separarRangos(entrada.value);
    if (trozos.length === 0) trozos.push('');
    const rechazados = [];
    let primerError = null;
    let ultimo = null;
    let anadidos = 0;
    for (const trozo of trozos) {
      const resultado = validarRango(trozo, rangos);
      if (!resultado.ok) {
        rechazados.push(trozo);
        primerError ??= resultado.mensaje;
        continue;
      }
      const { texto, etiqueta } = resultado.rango;
      rangos.push(texto);
      const item = clonar('tpl-rango-item');
      rellenar(item, { rango: texto });
      item.querySelector('[data-accion="quitar"]').setAttribute('aria-label', `Quitar el rango ${texto}`);
      lista.append(item);
      ultimo = etiqueta;
      anadidos += 1;
    }
    entrada.value = rechazados.join('; ');
    limpiarMensaje();
    if (primerError) {
      rechazar(anadidos > 0 ? `Se añadieron ${anadidos}; el resto no. ${primerError}` : primerError);
      entrada.focus();
      return false;
    }
    mostrar(anadidos === 1 ? `Añadido: ${ultimo}. Rangos en total: ${rangos.length}.` : `Añadidos ${anadidos} rangos. Rangos en total: ${rangos.length}.`, 'info');
    entrada.focus();
    return true;
  }

  function quitar(item) {
    const indice = [...lista.children].indexOf(item);
    const [texto] = rangos.splice(indice, 1);
    item.remove();
    // El botón pulsado desaparece: el foco pasa al vecino o, si no queda ninguno, al campo
    const vecino = lista.children[indice] ?? lista.children[indice - 1];
    (vecino ? vecino.querySelector('button') : entrada).focus();
    limpiarMensaje();
    mostrar(`Rango quitado: ${texto}.`, 'info');
  }

  function validarEnVivo() {
    const trozos = separarRangos(entrada.value);
    const resultados = trozos.map((trozo) => validarRango(trozo, rangos));
    const fallo = resultados.find((r) => !r.ok);
    if (fallo) rechazar(fallo.mensaje);
    else if (resultados.length === 1) mostrar(`Se entiende como: ${resultados[0].rango.etiqueta}. Pulsa Añadir o Intro.`, 'info');
    else mostrar(`Se entienden ${resultados.length} rangos. Pulsa Añadir o Intro.`, 'info');
  }

  entrada.addEventListener('input', () => {
    clearTimeout(pausa);
    limpiarMensaje();
    if (entrada.value.trim() !== '') pausa = setTimeout(validarEnVivo, PAUSA_VALIDACION_MS);
  });

  // Intro añade el rango: sin esto enviaría el formulario entero
  entrada.addEventListener('keydown', (evento) => {
    if (evento.key !== 'Enter' || evento.isComposing) return;
    evento.preventDefault();
    anadir();
  });

  boton.addEventListener('click', anadir);

  lista.addEventListener('click', (evento) => {
    const quitarRango = evento.target.closest('[data-accion="quitar"]');
    if (quitarRango) quitar(quitarRango.closest('li'));
  });

  return {
    valores: () => [...rangos],

    /** Vacía los rangos y los habilita solo para columnas numéricas (tipo null = aún sin columna). */
    reiniciar(tipo) {
      clearTimeout(pausa);
      rangos = [];
      lista.replaceChildren();
      entrada.value = '';
      limpiarMensaje();
      const disponible = tipo === 'numerica';
      raiz.disabled = !disponible;
      avisoTipo.hidden = disponible;
      avisoTipo.textContent = tipo === null ? 'Elige una columna para poder agrupar en rangos.' : textoAvisoTipo;
    },

    /** Antes de enviar: el texto escrito y no añadido se añade; si no vale, se avisa y no se envía. */
    confirmarPendiente() {
      return entrada.value.trim() === '' || anadir();
    },

    /** Error del servidor sobre un rango ya añadido: el campo de texto no es el culpable. */
    mostrarError(texto) {
      mostrar(texto, 'error');
    },

    contiene: (texto) => rangos.includes(texto),

    enfocar: () => entrada.focus(),
  };
}
