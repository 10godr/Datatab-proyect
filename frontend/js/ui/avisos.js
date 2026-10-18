// Avisos del contrato ({ codigo, nivel, mensaje }) pintados con la plantilla #tpl-aviso.

import { clonar, rellenar } from '../plantillas.js';

const TEXTO_DE_NIVEL = { info: 'Nota', atencion: 'Atención' };

/** Rellena la lista con los avisos y la oculta si no hay ninguno. */
export function pintarAvisos(lista, avisos) {
  const fragmento = document.createDocumentFragment();
  for (const aviso of avisos ?? []) {
    const nivel = aviso.nivel === 'atencion' ? 'atencion' : 'info';
    const item = clonar('tpl-aviso');
    item.dataset.nivel = nivel;
    rellenar(item, { nivel: TEXTO_DE_NIVEL[nivel], mensaje: aviso.mensaje });
    fragmento.append(item);
  }
  lista.replaceChildren(fragmento);
  lista.hidden = lista.children.length === 0;
}
