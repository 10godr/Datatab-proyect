// Pestañas ARIA (patrón de tabulación móvil): solo la activa entra en el orden de Tab;
// flechas, Inicio y Fin mueven el foco y activan.

/** Devuelve { activar(nombre) }. `alActivar` recibe el nombre ('frecuencias', 'cruce' o 'datos'). */
export function iniciarPestanas(lista, alActivar) {
  const pestanas = [...lista.querySelectorAll('[role="tab"]')];

  function activar(pestana, { conFoco = false } = {}) {
    for (const otra of pestanas) {
      const activa = otra === pestana;
      otra.setAttribute('aria-selected', String(activa));
      otra.tabIndex = activa ? 0 : -1;
      document.getElementById(otra.getAttribute('aria-controls')).hidden = !activa;
    }
    if (conFoco) pestana.focus();
    alActivar(pestana.id.replace('tab-', ''));
  }

  lista.addEventListener('click', (evento) => {
    const pestana = evento.target.closest('[role="tab"]');
    if (pestana) activar(pestana);
  });

  lista.addEventListener('keydown', (evento) => {
    const actual = pestanas.indexOf(evento.target);
    if (actual < 0) return;
    const destinos = {
      ArrowRight: (actual + 1) % pestanas.length,
      ArrowLeft: (actual - 1 + pestanas.length) % pestanas.length,
      Home: 0,
      End: pestanas.length - 1,
    };
    if (!(evento.key in destinos)) return;
    evento.preventDefault();
    activar(pestanas[destinos[evento.key]], { conFoco: true });
  });

  return { activar: (nombre) => activar(document.getElementById(`tab-${nombre}`)) };
}
