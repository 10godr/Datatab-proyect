// Plantillas <template>: se clonan y se rellenan con textContent. Nunca se construye HTML con cadenas.

const moldes = new Map();

function molde(id) {
  let elemento = moldes.get(id);
  if (!elemento) {
    elemento = document.getElementById(id).content.firstElementChild;
    moldes.set(id, elemento);
  }
  return elemento;
}

/** Copia del elemento raíz de la plantilla. */
export function clonar(id) {
  return molde(id).cloneNode(true);
}

/** El elemento marcado con data-campo="nombre"; puede ser la propia raíz (querySelector no la encuentra). */
export function campo(raiz, nombre) {
  return raiz.dataset.campo === nombre ? raiz : raiz.querySelector(`[data-campo="${nombre}"]`);
}

/** Escribe cada valor como texto en su campo: rellenar(fila, { etiqueta: 'Mujer', frecuencia: '12' }). */
export function rellenar(raiz, valores) {
  for (const [nombre, valor] of Object.entries(valores)) {
    campo(raiz, nombre).textContent = valor;
  }
}

/** Copia del contenido de una plantilla cuyos ids llevan la palabra PREFIJO, para que sean únicos. */
export function clonarConPrefijo(id, prefijo) {
  const fragmento = document.getElementById(id).content.cloneNode(true);
  for (const elemento of fragmento.querySelectorAll('[id], [for], [aria-describedby]')) {
    for (const atributo of ['id', 'for', 'aria-describedby']) {
      if (elemento.hasAttribute(atributo)) {
        elemento.setAttribute(atributo, elemento.getAttribute(atributo).replaceAll('PREFIJO', prefijo));
      }
    }
  }
  return fragmento;
}
