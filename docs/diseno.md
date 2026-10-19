# Diseño de DataTab

Capa visual del frontend: tokens, tipografía, paleta, espaciado, logo y la estructura del HTML con los ganchos que usa JavaScript. El contrato con el servidor está en `api.md`. Un solo tema claro, sin selector de tema. HTML semántico, CSS con variables y JavaScript en módulos ES, sin compilación.

Archivos (todo en `frontend/`):

| Archivo | Contenido |
|---|---|
| `index.html` | Una sola página. Dos vistas (carga y análisis) que se alternan con `hidden`, un `<dialog>` y las plantillas. |
| `css/fonts.css` | `@font-face` de las fuentes locales. |
| `css/tokens.css` | Variables (`:root`). |
| `css/base.css` | Reinicio, tipografía, foco, utilidades (`.visualmente-oculto`, `.num`, `.etiqueta`). |
| `css/layout.css` | Contenedor, cabecera, pestañas, vista de carga, rejilla del análisis, puntos de corte. |
| `css/components.css` | Botones, campos, rangos, mensajes, tablas, gráfico, plegables, diálogo, versión de teléfono. |
| `css/print.css` | Solo papel o PDF (`media="print"`). |
| `assets/` | `logo.svg`, `logo-claro.svg`, `favicon.svg`, `favicon-32.png`, `apple-touch-icon.png`, `fonts/` (woff2 y `OFL.txt`). |
| `vendor/chart.umd.min.js` | Chart.js **4.5.1** (MIT), copia exacta del paquete npm `chart.js@4.5.1`, sin modificar. Licencia en `vendor/chart.js-LICENSE.md`. Expone la variable global `Chart`. |

La CSP del servidor (`default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'`) se cumple: no hay estilos ni scripts en línea ni manejadores `onclick`. Se probó con esa misma CSP, incluido Chart.js dibujando, sin violaciones en consola y sin peticiones a hosts externos.

## Tokens

Los de la maqueta aprobada (18/10/2026) están copiados tal cual en `tokens.css`; las extensiones están al final del archivo y solo añaden nombres.

| Grupo | Variables |
|---|---|
| Superficies | `--ink-0 #E8F5EC` fondo · `--ink-1 #FFFFFF` superficie · `--ink-2 #F2FAF5` campos y zonas elevadas |
| Separadores | `--line #CDE3D4` · `--line-strong #B3D1BE` · `--line-control #6C9A80` borde de controles (3:1) |
| Texto | `--text #10261A` · `--text-2 #3D5847` · `--text-3 #54705F` |
| Musgo y señal | Valores vigentes en `frontend/css/tokens.css` (`--signal #147A3F`, `--signal-hover #0F6633`). |
| Estados | Valores vigentes en `frontend/css/tokens.css` (`--signal #147A3F`, `--signal-hover #0F6633`). |
| Gráfico | Valores vigentes en `frontend/css/tokens.css` (`--signal #147A3F`, `--signal-hover #0F6633`). |
| Tipografía | `--font-ui`, `--font-num`; escala `--t-xs` 13 px · `--t-sm` 15 · `--t-md` 17 · `--t-lg` 22 · `--t-xl` 30 · `--t-2xl` 44 |
| Espaciado | `--s-1`…`--s-9` = 4, 8, 12, 16, 24, 32, 48, 64, 96 px |
| Radios | `--r-1` 3 px · `--r-2` 6 px |
| Anchos | `--measure` 64ch · `--page` 72rem |
| Extensiones | Valores vigentes en `frontend/css/tokens.css` (`--signal #147A3F`, `--signal-hover #0F6633`). |

**Gráficos.** Una sola serie va en `--signal`. Con varias categorías, en este orden: rosa suave, blanco cálido, azul apagado, ocre, violeta y gris (el circular admite 6 categorías como máximo). Cada categoría también se identifica por su etiqueta y por la tabla. Más categorías no reciben colores al azar: pasan a barras de un solo color.

## Tipografía

- **Atkinson Hyperlegible Next** para la interfaz y **Atkinson Hyperlegible Mono** para las cifras (clase `.num`, celdas `.n`). Diseñada por el Braille Institute para baja visión: I, l, 1 y O, 0 se distinguen, y la versión Mono es de la misma familia, de modo que las columnas de cifras cuadran (cifras tabulares) sin cambiar de "voz".
- Archivos locales, versiones variables (eje de peso 200–800), tomados de `@fontsource-variable/atkinson-hyperlegible-next` 5.3.0 y `@fontsource-variable/atkinson-hyperlegible-mono` 5.3.0 (en lugar de los estáticos `@fontsource/atkinson-hyperlegible-mono`: un archivo cubre los pesos 400, 500 y 600 que se usan y pesa menos que dos estáticos). Licencia OFL 1.1 en `assets/fonts/OFL.txt`.
- Subconjuntos: `latin` (todo el español: ñ, tildes, ü, ¿ ¡ × – · %) y `latin-ext` (se descarga solo si el archivo del usuario trae letras de ese rango). Pesos: Next latin 33,2 KB + latin-ext 18,6 KB; Mono latin 17,3 KB + latin-ext 10,5 KB. En una carga normal se bajan unos 50 KB (Next latin, precargado, y Mono latin). `font-display: swap`.
- Pila de reserva real: `"Segoe UI", system-ui, sans-serif` y `ui-monospace, "Cascadia Mono", Consolas, monospace`.
- Comprobado con el protocolo de depuración de Chromium (`CSS.getPlatformFontsForNode`): todos los caracteres de prueba (`Ñandú ¿Cuántos? ¡Atención! 3 × 4 – 5 · 50 % áéíóúü`) se dibujan con Atkinson, en la interfaz y en Mono. Los únicos que caen a la fuente de reserva son `≤` y `≥` (la fuente no los tiene); aparecen solo si alguien los escribe como rango, porque las etiquetas que genera la API dicen "30 o menos".
- Escala: 17 px en texto corrido, 15 px en controles y tablas, 13 px en pistas, etiquetas y encabezados de tabla. Encabezados 600, interlineado 1,15 (títulos) y 1,55 (texto).

## Paleta y contraste

Calculado con la fórmula de luminancia relativa de WCAG 2.2. Mínimos: 4,5:1 en texto, 3:1 en bordes de controles, foco y relleno de gráfico.

| Par | Contraste | Uso |
|---|---|---|
| `--text` sobre `--ink-0` / `--ink-1` / `--ink-2` | 17,2 / 16,3 / 15,3 | Texto principal |
| `--text-2` sobre `--ink-0` / `--ink-1` / `--ink-2` | 9,0 / 8,5 / 8,0 | Texto secundario, botones tenues |
| `--text-3` sobre `--ink-0` / `--ink-1` / `--ink-2` / `--moss-900` | 5,6 / 5,3 / 5,0 / 4,6 | Pistas, marcadores de posición, pie |
| `--moss-300` sobre `--ink-0` / `--ink-1` / `--ink-2` | 8,9 / 8,4 / 7,9 | Etiquetas "Resultado calculado", código |
| `--signal` sobre `--ink-0` / `--ink-1` | 10,8 / 10,2 | Enlaces, subrayado activo |
| `--signal-ink` sobre `--signal` / `--signal-hover` | 9,5 / 10,7 | Botón principal |
| `--error` sobre `--ink-0` / `--ink-1` | 7,5 / 7,1 | Errores, botón de cerrar archivo |
| `--warn` sobre `--ink-0` / `--ink-1` | 10,2 / 9,7 | Avisos de atención |
| `--text` sobre `--moss-700` | 10,7 | Opción elegida del control segmentado |
| `--line-control` sobre `--ink-0` / `--ink-1` / `--ink-2` | 3,6 / 3,4 / 3,2 | Borde de botones, campos y selects |
| `--signal` sobre `--ink-0` / `--ink-2` / `--moss-900` / `--moss-700` | 10,8 / 9,6 / 8,7 / 6,7 | Foco, relleno de barra sobre su pista |
| Colores de gráfico sobre `--ink-0` | rosa 9,5 · blanco 16,4 · azul 7,8 · ocre 8,9 · violeta 6,7 · gris 5,6 | Series |
| Negro sobre blanco | 21 | Impresión |

`--moss-500` (4,25:1 sobre `--ink-0`) y `--line` / `--line-strong` solo se usan como decoración (separadores, regla bajo el pie de tabla), nunca para texto ni para delimitar un control.

**El estado nunca depende solo del color.** Pestaña activa: subrayado de 2 px además del color. Opción elegida del gráfico: fondo, color de texto y subrayado. Avisos: la palabra "Atención" o "Nota" delante del texto. Errores: título "No se pudo…" en el propio bloque. Zona de carga al arrastrar: borde sólido en lugar de punteado y texto "Suelta el archivo para cargarlo.". Fila fuera de rango: su etiqueta dice "Fuera de los rangos".

## Espaciado y composición

- Solo la escala `--s-1`…`--s-9`. Dentro de un grupo, 8–12 px; entre grupos, 24–32 px; entre secciones, 64–96 px.
- Margen lateral: 16 px en teléfono y 32 px desde 641 px (más `env(safe-area-inset-*)`). Página de 72 rem como máximo (`.contenedor`), texto corrido de 64 caracteres.
- Controles (botones, campos, selects, pestañas, resúmenes plegables, opciones del control segmentado, "Quitar"): 40 px de alto como mínimo. Comprobado con medición automática a 1440 y 390 px.
- Un panel solo agrupa controles (`.controles`, `--ink-1`, borde `--line`, radio 6 px). Nada va dentro de una tarjeta dentro de otra. Las tablas, el gráfico y el texto no tienen caja: se separan con reglas de 1 px y espacio. Sin sombras ni degradados (comprobado con búsqueda en el CSS).
- Radios: 3 px (elementos de lista dentro del panel) y 6 px (controles, panel, diálogo). Las barras proporcionales y la barra de progreso usan 2 px, como las barras de la maqueta.
- Puntos de corte: **≤ 640 px** teléfono; **641–960 px** tableta (una columna; el panel de controles se reparte en dos columnas); **≥ 961 px** escritorio (controles de 19 rem a la izquierda, resultado a la derecha). Dentro del resultado, la tabla y el gráfico van lado a lado (5fr/6fr) cuando el contenedor mide 44 rem o más (consulta de contenedor), y apilados si no; por eso a 1024 px quedan apilados y a 768 px lado a lado.
- Sin desbordamiento horizontal de la página a 1440, 1024, 768, 390 ni 320 px.

### Teléfono (≤ 640 px)

- La cabecera pasa a dos filas: logo y "Cerrar archivo", y debajo nombre del archivo (se recorta con puntos suspensivos), filas y columnas.
- Los controles van arriba, dentro de un `<details>` (`#frec-controles`, `#cruce-controles`) que JS cierra tras calcular. Su resumen muestra el título y un texto de apoyo (`#frec-controles-resumen`).
- La tabla de frecuencias se muestra como lista: etiqueta, frecuencia y porcentaje en una línea y, debajo, una barra proporcional que empieza en cero. Se hace con `display: grid` sobre los propios elementos de tabla y con roles ARIA repetidos en el marcado (`role="table"`, `row`, `cell`…) para que los lectores de pantalla no pierdan la semántica de tabla. La barra la dibujan `tr::before` (pista) y `tr::after` (relleno, ancho `var(--ancho)`).
- El gráfico queda en `<details id="frec-grafico-detalles">` con el resumen "Ver gráfico".
- El cruce y la vista de datos se desplazan en horizontal dentro de su contenedor, con la primera columna fija (y el encabezado fijo en la vista de datos). La página no se desplaza.

### Escritorio y tableta: los `<details>` siempre muestran su contenido

Desde 641 px se oculta el `<summary>` y `::details-content { content-visibility: visible }` mantiene visible el contenido aunque el `<details>` esté cerrado. Aun así, **JS debe poner `open` en escritorio** (`details.open = !matchMedia('(max-width: 640px)').matches`) al dibujar un resultado y al cambiar la consulta de medios, para los navegadores sin `::details-content`.

### Impresión (`print.css`)

No es un modo claro: es solo para papel o PDF. Fondo blanco y texto negro. Se imprime la pestaña abierta con la línea de archivo (nombre, filas, columnas), el resultado, los avisos y "Cómo leerlo". Se ocultan la marca, "Cerrar archivo", las pestañas, los controles, los botones de página, el gráfico, el pie y los estados de vacío o carga. Las filas no se parten entre páginas y el encabezado de tabla se repite. **El gráfico no se imprime**: es un `<canvas>` con los colores del tema oscuro y saldría ilegible; la tabla trae los mismos datos.

## Logo

Símbolo "A · Tabulador": un trazo horizontal que termina en una barra vertical (dos rectángulos). `viewBox` 32 × 32: `rect x4 y14.5 w17 h3` y `rect x24 y7 w3.5 h18`.

- `assets/logo.svg`: usa `currentColor`; el color lo da el contexto (`--signal` en la cabecera).
- `assets/logo-claro.svg`: musgo oscuro `#13261C`, para fondos claros.
- En la cabecera va **en línea** en el HTML (un `<svg>` con `fill="currentColor"` y `aria-hidden`), junto al nombre "datatab" en minúsculas, 22 px, peso 600. Un `<img>` no hereda `currentColor`. El nombre va siempre al lado: solo, el símbolo puede leerse como "ir al final".
- `assets/favicon.svg`: símbolo verde `#63D68F` sobre transparente. Para que sea nítido a 16 px, los trazos se redondearon a medidas pares (`x4 y14 w18 h4` y `x24 y6 w4 h20`), de modo que a 16 y 32 px caen en píxeles enteros. Es el único ajuste respecto al símbolo de la maqueta.
- `assets/favicon-32.png` (32 px, transparente) y `assets/apple-touch-icon.png` (180 px, símbolo con la geometría de la maqueta en verde sobre `#0A0C0B`) se generaron desde los SVG con Chromium.
- Espacio libre alrededor: al menos la altura de la barra horizontal del símbolo (3 unidades de 32). No se deforma, no se gira y no se le añaden contornos ni efectos.

## Textos

Español claro, voz de usuario, cada botón dice lo que hace ("Calcular frecuencias", "Generar tabla", "Añadir", "Quitar", "Cerrar archivo", "Seguir trabajando"). Los textos fijos están en el HTML, no en JS; JS solo pone las partes que cambian (cifras, nombres de columna, mensajes del servidor). Tres tipos de texto de resultado, que no se mezclan: **Resultado calculado** (cifras), **Descripción** ("Cómo leerlo": qué muestra, lectura, límites) y **avisos** (límites del dato).

## Estructura del HTML y ganchos para JavaScript

Convenciones:

- **Vistas y estados** se alternan con el atributo `hidden`. El CSS lo respeta siempre (`[hidden] { display: none !important }`).
- **Textos variables**: `textContent` sobre el elemento con id o con `data-campo`. Nunca `innerHTML`.
- **Plantillas** (`<template>`): se clonan con `plantilla.content.firstElementChild.cloneNode(true)` y se rellenan. Si la plantilla tiene un solo texto variable, la raíz (`th` o `td`) recibe el texto directamente (`celda.textContent = …`); si tiene varios, se rellenan los descendientes marcados con `data-campo`. `querySelector` no encuentra la propia raíz.
- **Anchos y alturas dinámicos**: variables CSS fijadas con `elemento.style.setProperty('--ancho', '60%')`. La CSP permite el CSSOM, pero **no** `setAttribute('style', …)` ni `<style>`.
- **Gráfico**: la biblioteca es la global `Chart` (se carga antes que `js/main.js`). `js/main.js` es el módulo de entrada (`<script type="module">`).
- **Anuncios**: `#frec-anuncio`, `#cruce-anuncio` y `#datos-anuncio` son regiones `role="status"` ocultas a la vista. JS escribe ahí frases como "Frecuencias calculadas: 4 filas".
- **Foco tras calcular**: los títulos de resultado `#frec-titulo` y `#cruce-titulo` llevan `tabindex="-1"` para llevarles el foco con `.focus()`.

### Cabecera y vistas

| Gancho | Qué es y qué hace JS |
|---|---|
| `#vista-carga`, `#vista-analisis` | Vistas. Se muestra una y se oculta la otra. Empieza visible la de carga. |
| `#archivo-barra` | Zona de la cabecera con datos del archivo. Oculta (`hidden`) en la vista de carga; JS la muestra en la de análisis. |
| `#archivo-nombre`, `#archivo-filas`, `#archivo-columnas` | Nombre, filas y columnas. |
| `#archivo-filas-unidad`, `#archivo-columnas-unidad` | "filas" y "columnas"; cambiar a singular si la cifra es 1. |
| `#btn-cerrar-archivo` | Abre el diálogo de confirmación. |
| `#archivo-avisos` | `<ul>` de avisos del archivo (los de `POST /api/datasets`). Oculta si no hay. Se llena con `#tpl-aviso`. |
| `main#contenido` | Destino del enlace "Saltar al contenido". |

### Vista de carga

| Gancho | Qué es y qué hace JS |
|---|---|
| `[data-config="formatos"]` | Texto con los formatos (`.xlsx, .xls y .csv`). Viene con el valor por defecto del contrato; JS lo sustituye con `/api/configuracion`. |
| `[data-config="max-mb"]` | Tamaño máximo en MB. |
| `[data-config="minutos-inactividad"]` | Minutos de caducidad (nota de privacidad). |
| `#zona-carga` | Zona para soltar. JS escucha `dragenter`, `dragover`, `dragleave` y `drop`. Mientras se arrastra: `data-arrastrando="true"`. Durante la lectura: `aria-busy="true"`. |
| `#archivo-input` | `<input type="file">` nativo; su etiqueta "Elegir archivo" hace de botón y se enfoca con el teclado. Tiene `accept=".xlsx,.xls,.csv"` por defecto (JS puede ajustarlo desde `formatos`). Al cargar, `disabled = true`. |
| `#carga-estado` (`role="status"`) y `#carga-leyendo` | El contenedor existe siempre; JS le quita `hidden` al hijo `#carga-leyendo` ("Leyendo el archivo…") mientras dura la lectura. |
| `#carga-error` (`role="alert"`) y `#carga-error-contenido` | El contenedor existe siempre; JS le quita `hidden` al hijo `#carga-error-contenido` y rellena `[data-campo="mensaje"]` y `[data-campo="sugerencia"]` (opcional) con `error.mensaje` y `error.sugerencia`. Para limpiar, vuelve a ponerle `hidden`. |

### Pestañas

`#tab-frecuencias`, `#tab-cruce` y `#tab-datos` (`role="tab"`, dentro de `role="tablist"`) controlan `#panel-frecuencias`, `#panel-cruce` y `#panel-datos` (`role="tabpanel"`, `aria-labelledby` ya puesto). El marcado inicial es el correcto: la primera pestaña tiene `aria-selected="true"` y `tabindex="0"`, las otras `aria-selected="false"` y `tabindex="-1"`; los paneles segundo y tercero llevan `hidden`. JS debe: al activar una pestaña, actualizar `aria-selected` y `tabindex` (patrón de tabulación móvil) y los `hidden` de los paneles; con las flechas izquierda y derecha, `Inicio` y `Fin`, mover el foco y activar.

### Frecuencias (prefijo `frec-`)

| Gancho | Qué es y qué hace JS |
|---|---|
| `#frec-form` | `<form>`. El botón `#frec-calcular` es `type="submit"`: usar el evento `submit` con `preventDefault()`. |
| `#frec-controles` (`<details open>`) y `#frec-controles-resumen` | Plegable de controles. JS lo cierra tras calcular **solo en teléfono** y escribe en el resumen un texto como "Edad · 4 rangos". |
| `#frec-columna` | `<select>` de columna. Opciones con `new Option(nombre, nombre)`. |
| `#frec-columna-pista` | Texto de tipo: "Numérica · de 18 a 92 · 3 vacías". |
| `[data-montaje-rangos="frec"]` | Punto de montaje de la pieza de rangos (ver más abajo). |
| `#frec-anuncio` | Región `role="status"` oculta. |
| `#frec-vacio` | Estado inicial: cómo continuar. |
| `#frec-cargando` | "Calculando las frecuencias…". |
| `#frec-error` | Error de cálculo. Rellenar `[data-campo="mensaje"]` y `[data-campo="sugerencia"]`. |
| `#frec-sin-datos` | Sin datos suficientes (`SIN_DATOS`). Rellenar `[data-campo="columna"]`. |
| `#frec-resultado` | Resultado. Muestra solo uno de los cinco estados anteriores a la vez (`hidden` en los demás). |
| `#frec-titulo` | Título ("Edad agrupada en 4 rangos"). |
| `#frec-n`, `#frec-excluidas` | `n` en `#frec-n`; en `#frec-excluidas`, el texto " · 3 filas sin dato excluidas" (vacío si no hay). |
| `#frec-avisos` | `<ul>` de avisos del resultado. Oculta si no hay. Se llena con `#tpl-aviso`. |
| `#frec-caption`, `#frec-encabezado-valor` | Texto del `<caption>` y del primer encabezado ("Valor" o "Rango de edad"). |
| `#frec-cuerpo` | `<tbody>`. Se llena con `#tpl-frec-fila`. |
| `#frec-pie-etiqueta`, `#frec-pie-frecuencia`, `#frec-pie-porcentaje` | Pie. Etiqueta "Total", o "Base de cálculo" si `solapados > 0`. |
| `#frec-grafico-detalles` | `<details>` del gráfico (resumen "Ver gráfico"). JS: `open = !esTelefono`. |
| `#frec-grafico-tipo` | `<fieldset>` del control segmentado: radios `name="frec-tipo-grafico"`, valores `barras` y `circular`. Escuchar `change`. Con más de 6 categorías, `disabled = true` en el radio `circular` (el CSS muestra solo la pista `#frec-circular-pista`). Con "muchas categorías", ocultar todo el fieldset. |
| `#frec-grafico`, `#frec-grafico-titulo`, `#frec-lienzo` | `<figure>`, su `<figcaption>` y el `<canvas>` de Chart.js. `aria-label` del canvas: JS lo actualiza con un resumen ("Gráfico de barras: …. Los mismos datos están en la tabla."). |
| `--alto-grafico` | Variable CSS del contenedor `.grafico__lienzo` (por defecto 18rem). JS la fija según el número de categorías, por ejemplo `calc(n * 2.6rem + 3.5rem)` en barras y `20rem` en circular. |
| `#frec-grafico-muchas` | Mensaje para más de 60 valores distintos: JS oculta `#frec-grafico` y `#frec-grafico-tipo`, destruye el gráfico, muestra este bloque y escribe la cantidad en `[data-campo="cantidad"]`. La tabla sigue completa. |
| `#frec-lectura-muestra`, `#frec-lectura-lectura`, `#frec-lectura-limites` | Los tres párrafos de "Cómo leerlo". Tras "Límites" ya hay una frase fija ("Describe este archivo; no es una conclusión sobre otra población."). |

### Cruce de variables (prefijo `cruce-`)

| Gancho | Qué es y qué hace JS |
|---|---|
| `#cruce-form`, `#cruce-generar` | Formulario y botón `type="submit"` ("Generar tabla"). |
| `#cruce-controles`, `#cruce-controles-resumen` | Plegable de controles (como en frecuencias). |
| `#cruce-fila-columna`, `#cruce-fila-pista`, `[data-montaje-rangos="cruce-fila"]` | Variable en filas: select, pista de tipo y rangos. |
| `#cruce-columna-columna`, `#cruce-columna-pista`, `[data-montaje-rangos="cruce-columna"]` | Variable en columnas. |
| `#cruce-anuncio`, `#cruce-vacio`, `#cruce-cargando`, `#cruce-error`, `#cruce-sin-datos`, `#cruce-resultado` | Igual que en frecuencias. |
| `#cruce-titulo`, `#cruce-n`, `#cruce-excluidas`, `#cruce-avisos` | Igual que en frecuencias. |
| `#cruce-caption` | `<caption>`: "Pacientes según rango de edad y sexo. Porcentaje calculado sobre el total de cada fila. n = 197." |
| `#cruce-variable-fila` | Esquina de la tabla: nombre de la variable de las filas. |
| `#cruce-variable-columna` | Encabezado de grupo (`scope="colgroup"`): nombre de la variable de las columnas. JS fija `colSpan` = 2 × (categorías + 1). |
| `#cruce-encabezado` | Segunda fila del encabezado: JS añade una categoría por columna (y «Total»), cada una con `colSpan` 2. |
| `#cruce-subencabezado` | Tercera fila: «Fr» y «%» bajo cada categoría. |
| `#cruce-cuerpo` | Filas con `#tpl-cruce-fila`; JS añade por cada columna una celda de frecuencia y otra de porcentaje de la fila, más el total (Fr y 100,0). |
| `#cruce-pie` | Fila "Total": JS añade Fr y % (sobre `n`) por columna y el total general. |
| `#cruce-lectura-muestra`, `#cruce-lectura-lectura`, `#cruce-lectura-limites` | "Cómo leerlo". Tras "Límites" ya está la frase fija: "Una asociación observada en estos datos no demuestra que una variable cause la otra." |

### Ver datos (prefijo `datos-`)

| Gancho | Qué es y qué hace JS |
|---|---|
| `#datos-anuncio` | Región `role="status"` oculta. |
| `#datos-cargando`, `#datos-error` | Estados. `#datos-contenido` contiene paginación y tabla. |
| `#datos-rango`, `#datos-desde`, `#datos-hasta`, `#datos-total` | "Mostrando 1–50 de 200". |
| `#datos-anterior`, `#datos-siguiente` | Botones. JS los deshabilita (`disabled`) en la primera y la última página. |
| `#datos-tabla`, `#datos-caption` | Tabla y su descripción (oculta a la vista; actualizable). |
| `#datos-encabezado` | `<tr>` del encabezado. Ya contiene el `<th>` "Fila"; JS añade un `<th>` por columna con `#tpl-datos-columna`. |
| `#datos-cuerpo` | Filas con `#tpl-datos-fila` (el `th` lleva el número de fila) y celdas con `#tpl-datos-celda`. Una celda vacía se deja sin texto: el CSS pinta una raya con texto alternativo "vacío". |

### Diálogo de cierre

`#dialogo-cerrar` (`<dialog>`) con `<form method="dialog">`. JS abre con `showModal()` y escribe el nombre en `#dialogo-cerrar-nombre`. El botón "Seguir trabajando" (`value="cancelar"`, `autofocus`) y el de "Cerrar archivo" (`value="cerrar"`, `#dialogo-cerrar-confirmar`) cierran el diálogo solos. JS escucha el evento `close` y actúa si `dialogo.returnValue === 'cerrar'`; con Escape o cancelar no hace nada.

### Pieza reutilizable de rangos

`<template id="tpl-rangos">` se monta en cada `[data-montaje-rangos]` (el valor del atributo es el prefijo: `frec`, `cruce-fila`, `cruce-columna`). El marcado usa la palabra `PREFIJO` en `id`, `for` y `aria-describedby`: al clonar hay que sustituirla por el prefijo para que los ids sean únicos. Receta:

```js
const fragmento = document.getElementById('tpl-rangos').content.cloneNode(true);
for (const el of fragmento.querySelectorAll('[id], [for], [aria-describedby]')) {
  for (const atributo of ['id', 'for', 'aria-describedby']) {
    if (el.hasAttribute(atributo)) {
      el.setAttribute(atributo, el.getAttribute(atributo).replaceAll('PREFIJO', prefijo));
    }
  }
}
punto.replaceChildren(fragmento);
```

Dentro de la pieza:

| Selector | Uso |
|---|---|
| `[data-rangos]` | `<fieldset>`. Con `disabled = true` se desactiva y el CSS oculta la entrada y la ayuda de sintaxis, dejando solo el aviso de columnas no numéricas. |
| `[data-rangos-contexto]` | Texto solo para lectores de pantalla en la leyenda. El punto de montaje trae `data-contexto="de la variable en filas"` (o en columnas) para copiarlo ahí. |
| `[data-rangos-aviso-tipo]` | "Los rangos solo están disponibles en columnas numéricas." Oculto por defecto; mostrarlo cuando la columna no sea numérica. |
| `[data-rangos-lista]` | `<ul>` de rangos añadidos (se oculta sola si está vacía). Se llena con `#tpl-rango-item`. |
| `[data-rangos-entrada]` | Campo de texto. **JS debe interceptar `Enter` aquí** (añadir el rango y `preventDefault()`), o el formulario se enviaría. |
| `[data-rangos-anadir]` | Botón "Añadir". |
| `[data-rangos-mensaje]` | Mensaje de validación en vivo (`aria-live="polite"`). Fijar `data-nivel` en `info`, `atencion` o `error` según el caso; vacío no ocupa espacio. |

`#tpl-rango-item`: `<li>` con `[data-campo="rango"]` y el botón `[data-accion="quitar"]`. JS le pone `aria-label="Quitar el rango 30-39"`.

### Otras plantillas

| Plantilla | Raíz y campos |
|---|---|
| `#tpl-aviso` | `<li class="mensaje aviso" data-nivel="info">` con `[data-campo="nivel"]` y `[data-campo="mensaje"]`. JS fija `data-nivel` (`info` o `atencion`, como la API) y el texto de nivel ("Nota" o "Atención"). Va dentro de un `<ul>` (`#archivo-avisos`, `#frec-avisos`, `#cruce-avisos`). |
| `#tpl-frec-fila` | `<tr data-tipo="valor">` con `[data-campo="etiqueta"]` (el `th`), `[data-campo="frecuencia"]` y `[data-campo="porcentaje"]`. JS fija `data-tipo` (`valor`, `rango`, `fuera_de_rango`, `sin_valor_numerico`, igual que `filas[].tipo` de la API) y `tr.style.setProperty('--ancho', 'N%')` para la barra de teléfono: frecuencia de la fila dividida por la frecuencia máxima (la barra de mayor frecuencia ocupa el 100 %, y todas empiezan en cero). |
| `#tpl-cruce-fila` | `<tr>` con `[data-campo="etiqueta"]` (el `th` de fila); las celdas las crea JS. |
| `#tpl-datos-columna` | `<th scope="col">`: la raíz recibe el texto. |
| `#tpl-datos-fila` | `<tr>` con `[data-campo="numero"]` (el `th` de número de fila). |
| `#tpl-datos-celda` | `<td>`: la raíz recibe el texto. |

### Qué decide JS y qué no

JS decide: qué estado se ve, los textos variables (títulos, `n`, lectura, avisos, resúmenes), el formato de cifras con coma decimal y un decimal, el color y tipo del gráfico, los `aria-label` de rangos y gráfico, el foco. El CSS decide: aspecto, el plegado en teléfono, la barra proporcional, los puntos de corte, la raya de las celdas vacías, la pista del gráfico circular (con `:has` sobre el radio deshabilitado) y el texto de arrastrar según el tipo de puntero.

### Gráfico: configuración propuesta

Leer los colores de las variables CSS (`getComputedStyle(document.documentElement).getPropertyValue('--c-rose')`) en lugar de repetir los valores. Esperar a que la fuente esté cargada antes de dibujar (`document.fonts.load('400 12px "Atkinson Hyperlegible Next"')`). Chart.js no trae etiquetas de valor: en barras se dibujan con un plugin propio. Esta configuración se probó con la CSP estricta.

```js
Chart.defaults.font.family = estilos.getPropertyValue('--font-ui');
Chart.defaults.font.size = 12;
Chart.defaults.color = estilos.getPropertyValue('--text-2');

// Barras horizontales, una sola serie en verde señal, escala desde cero
new Chart(lienzo, {
  type: 'bar',
  data: { labels, datasets: [{ data, backgroundColor: color('--signal'), borderRadius: 2, barPercentage: 0.6, categoryPercentage: 1 }] },
  options: {
    indexAxis: 'y', responsive: true, maintainAspectRatio: false, animation: false,
    layout: { padding: { right: 32 } },
    plugins: { legend: { display: false } },
    scales: {
      x: { beginAtZero: true, border: { display: false }, grid: { color: color('--line') },
           ticks: { color: color('--text-3'), precision: 0, font: { family: color('--font-num') } } },
      y: { border: { display: false }, grid: { display: false }, ticks: { color: color('--text-2') } },
    },
  },
});

// Circular (hasta 6 categorías): rosa, blanco, azul, ocre, violeta, gris; separadas con el color de fondo
new Chart(lienzo, {
  type: 'doughnut',
  data: { labels, datasets: [{ data, backgroundColor: [rosa, blanco, azul, ocre, violeta, gris], borderColor: color('--ink-0'), borderWidth: 2 }] },
  options: { responsive: true, maintainAspectRatio: false, animation: false, cutout: '55%',
             plugins: { legend: { position: 'bottom', labels: { color: color('--text-2'), boxWidth: 10, boxHeight: 10, padding: 14 } } } },
});
```

Con `prefers-reduced-motion` o sin ella, `animation: false` evita movimiento innecesario. Al cambiar de tipo de gráfico hay que llamar a `destroy()` antes de crear otro sobre el mismo `<canvas>`.

## Accesibilidad

- `lang="es"`, `viewport`, `color-scheme` claro.
- Enlace "Saltar al contenido" (primer elemento enfocable), `header`, `main`, `footer` únicos. Un solo `<h1>` visible en cada vista (en la de análisis es un título oculto a la vista: "Análisis de tu archivo"); los títulos de resultado son `h2` y "Cómo leerlo" es `h3`.
- Foco visible en todos los controles: 2 px en `--signal` con 2 px de separación (dentro de contenedores con desplazamiento, como pestañas y control segmentado, se dibuja hacia dentro para que no se recorte). Comprobado recorriendo la página con la tecla Tab.
- Tablas con `<caption>`, `th scope="col"` y `th scope="row"`; el cruce usa además `scope="colgroup"`. Los contenedores de tablas que se desplazan son `role="region"` con nombre y `tabindex="0"`, para poder desplazarlos con el teclado.
- Control segmentado con radios nativos: flechas del teclado y lectura de estado sin JS.
- Regiones vivas: `#carga-estado` (`status`), `#carga-error` (`alert`), `#frec-anuncio`, `#cruce-anuncio`, `#datos-anuncio` y el mensaje de rangos (`aria-live="polite"`).
- `prefers-reduced-motion`: sin transiciones ni animaciones; la barra de progreso queda fija y de un solo color.
- Sin iconos decorativos. Los únicos símbolos son el logo (decorativo, con el nombre al lado), el chevron de los plegables (dibujado con CSS, el estado lo da `<details>`) y la raya de las celdas vacías (con texto alternativo).

## Cómo se verificó

Con un servidor de previsualización y un script de capturas con Playwright y Chromium 141, fuera del repositorio. El servidor sirve `frontend/` con la misma CSP del contrato y rellena las plantillas con datos ficticios. Estados capturados a 1440, 1024, 768 y 390 px (y 320 px sin desbordamiento): carga, error de carga, lectura, arrastrando, vacío, cargando, error, sin datos, frecuencias con rangos, sin rangos (barras y circular), con solape ("Base de cálculo", "Fuera de los rangos", "Sin valor numérico"), con muchas categorías, cruce (estrecho y ancho), vista de datos (páginas 1 y 2, con desplazamiento), diálogo de cierre, avisos del archivo y plegado de controles en teléfono. Comprobado: sin desbordamiento horizontal, fuentes Atkinson cargadas, contrastes calculados, foco visible con Tab, zonas táctiles de 40 px, ids únicos y referencias ARIA válidas (también con las tres piezas de rangos montadas), CSS sin degradados ni sombras, ninguna petición externa ni violación de CSP, y el PDF de impresión de frecuencias, cruce y datos.

No se verificó con un lector de pantalla real (NVDA, JAWS o VoiceOver), ni en Safari, Firefox o Edge, ni en un teléfono físico; las comprobaciones de semántica son de estructura, no de lo que anuncia cada lector.

## Decisiones que se apartan de la maqueta

| Cambio | Motivo |
|---|---|
| Sin botones "Descargar .xlsx" y ".csv" en la cabecera del resultado y sin "Descargar resultado" en teléfono. | Decisión del proyecto: sin exportación por ahora. |
| Sin "Paso 1 de 3" en la pantalla de carga. | Petición expresa. |
| Texto de privacidad: "Tu archivo se usa solo mientras trabajas: se elimina al cerrarlo o tras N minutos sin uso." en lugar de "Tus datos se procesan en este equipo…". | Es el texto fijado para esta etapa y describe lo que hace el servidor (caducidad por inactividad). N viene de `/api/configuracion`. |
| El panel de controles es un panel con borde y radio de 6 px dentro de la página, no una columna a sangre de 19 rem con regla a la derecha. | La maqueta era una ventana de demostración; en la página real el panel se integra con el contenedor de 72 rem. Mantiene los 19 rem de ancho. |
| La cabecera y las pestañas ocupan todo el ancho de la ventana (con el contenido a 72 rem). | Mismo motivo: en la maqueta eran el marco de una ventana. |
| Encabezado de tabla de cruce en dos filas, con el nombre de la variable de columnas encima de sus categorías, y etiquetas de columna en la fuente de la interfaz y no en Mono. | La maqueta solo nombraba la variable de columnas en el pie de la tabla. Las etiquetas son nombres, no cifras, y en Mono ocupan demasiado con categorías largas. |
| Etiqueta "Descripción" sobre "Cómo leerlo". | Distinguir de un vistazo las cifras ("Resultado calculado") de la explicación, según se pidió. |
| Cabecera de tabla en Mono sin separación entre letras (`letter-spacing: 0`) en las columnas numéricas. | La separación de 0,04 em de la maqueta, aplicada a Mono, deletrea las palabras ("F r e c u e n c i a"). |
| "Total" del pie de tabla en peso 600 (en la maqueta era un `td`; aquí es un `th` de fila). | Mantener el mismo aspecto del pie con la semántica correcta. |
| La vista de datos añade la columna fija "Fila" (número de fila). | La primera columna de datos puede ser ancha y no cabe fija en 390 px; el número de fila es estrecho y sirve de referencia. |
| Pie de página (`footer`, en las dos vistas) y, en la vista de carga, el bloque "Qué puedes hacer" con tres capacidades. | El pie es un punto de referencia pedido para la accesibilidad. El bloque explica la herramienta a quien no la conoce y no lleva iconos. |
| Favicon con trazos de 4 unidades en lugar de 3 y 3,5. | Nitidez a 16 px. El símbolo del logo no cambia. |
| El gráfico no se imprime. | Es un lienzo; ver "Impresión". |
| No hay gráfico en el cruce. | La lista de entregables solo pide tabla, avisos y lectura para el cruce. La leyenda de colores de la maqueta (rosa y blanco) queda como referencia si se añade un gráfico de barras agrupadas. |

## Cambios hechos al integrar el JavaScript

Pequeños ajustes a `index.html` y a los CSS que salieron al conectar el JavaScript y probarlo en un navegador real.

| Cambio | Motivo |
|---|---|
| `index.html`: nuevo `<p class="visualmente-oculto" id="anuncio-general" role="status">` tras el enlace de salto. | Región viva para anunciar que se abrió o se cerró un archivo, cuando el cambio de vista no tiene un panel propio donde anunciarlo. |
| `index.html`: `#carga-titulo` lleva `tabindex="-1"`. | Al cerrar el archivo o al caducar, el foco vuelve al título de la vista de carga. |
| `index.html`: nuevo `#carga-aviso` (`role="status"`) con `#carga-aviso-contenido` (misma estructura que un aviso, `data-nivel="atencion"`). | Avisos que no son un error de carga: "Tu archivo ya no está disponible…" (caducidad o sesión que no se pudo recuperar) y fallo al borrar el archivo al cerrar. |
| `index.html`: `tabindex="-1"` en `#frec-error`, `#cruce-error`, `#datos-error`, `#frec-sin-datos` y `#cruce-sin-datos`. | El JavaScript les lleva el foco cuando aparecen, igual que a los títulos de resultado. |
| `index.html`: nuevos `#cruce-desliza` y `#datos-desliza` (`<p class="pista" hidden>`) sobre las tablas que se desplazan. JS los muestra solo mientras la tabla no cabe (`ResizeObserver`). | A 390 px la primera columna fija y el borde de la región ocultaban que hubiera más columnas a la derecha: no había ninguna señal visual. Sin degradados ni sombras (regla del diseño), la señal es una frase. |
| `components.css`, teléfono: en el cruce, la primera columna fija pasa de `max-width: 16rem` a `9rem`. | Con categorías largas ("Colecistitis crónica litiásica") ocupaba unos 225 de los 358 px útiles y dejaba a la vista solo media columna de datos. Ahora el texto se parte en dos líneas y se ve la siguiente columna cortada por el borde. |
| `layout.css`: `.pestanas` lleva `padding: var(--s-1)` con el mismo margen negativo; `components.css`: `.pestana:focus-visible` pasa de `outline-offset: -2px` a `2px`. | El anillo de foco iba dentro de la pestaña, justo encima de la primera y la última letra (las pestañas no llevan relleno horizontal). La holgura evita que `overflow-x: auto` lo recorte; el diseño no se mueve porque el margen negativo la compensa. |
| `frontend/package.json` (`"type": "module"`, script `test`) y `frontend/tests/index.js`. | `node --test tests/` en Node 22 trata el directorio como un módulo y falla; `tests/index.js` importa los `*.test.mjs`. No afecta al servidor ni al navegador. |

## Cambios del 18/10 (a petición de Seven)
- Pantalla de carga mínima: título, una línea, zona de carga. Sin lista de capacidades.
- "Datos del archivo" ya no es pestaña: va siempre debajo del análisis.
- Fondo verde más claro y botones secundarios con fondo y borde visibles.

## Estado visual actual
- **Tema único claro**: fondo menta `#E8F5EC`, tarjetas blancas, verde `#147A3F` para la acción principal. Tokens en `frontend/css/tokens.css`. Sin degradados, cristal ni elementos flotantes decorativos.
- **Pantalla de carga**: centrada, con líneas topográficas de fondo (`assets/topografia.svg`, trazo de 1 px, desvanecido hacia el centro por `.vista-carga::before`; solo aquí). La zona de carga tiene borde discontinuo, elevación al pasar el ratón y pulso al arrastrar.
- **Cabecera**: tarjeta blanca fija arriba, sin línea inferior; pestañas en píldora.
- **Gráfico**: tarjeta propia, sin selector de tipo. Con exactamente 2 categorías (y sin rangos solapados) es circular; en cualquier otro caso, barras. Cada barra con un color (`--c-green`, `--c-rose`, `--c-blue`, `--c-ochre`, `--c-violet`, `--c-teal`, `--c-coral`, `--c-lime`) y animación de entrada.
- **Análisis**: «Cómo leerlo» va bajo el cuadro de controles; la tabla de datos del archivo queda siempre debajo, en un recuadro `--moss-900`.
- **Cambio de columna**: el resultado anterior se atenúa, un cargador de cinco barras (mínimo 600 ms, `conPausaMinima` en `ui/panel.js`) cubre el cálculo y la tabla entra fila a fila.
- **Rangos múltiples**: varios a la vez separados por `;`, coma y espacio, salto de línea o « y » (`separarRangos` en `js/ui/rangos.js`).
- Todo el movimiento se desactiva con `prefers-reduced-motion`.
