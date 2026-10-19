# API de DataTab

Contrato entre el frontend y el backend. Es la única fuente de verdad: si algo cambia aquí, cambian las dos partes.

- Todo cuelga de `/api`. Peticiones y respuestas en JSON (UTF-8), salvo la subida de archivos (`multipart/form-data`).
- Los nombres de campos y los textos para el usuario están en español.
- Todas las respuestas de `/api` llevan `Cache-Control: no-store`.
- No hay cuentas ni cookies. Un archivo cargado se identifica con un `dataset_id` aleatorio que vive solo en la memoria del servidor.

## Ciclo de vida de un archivo

1. `POST /api/datasets` lee el archivo **en memoria** y devuelve un `dataset_id`.
2. Cada petición que usa ese `dataset_id` renueva su plazo de inactividad.
3. Se elimina al pasar `minutos_inactividad` (30 por defecto) sin uso, con `DELETE`, o al apagar el servidor.
4. No se escribe ninguna copia del archivo en disco.

## Errores

Todo error (también los de validación de FastAPI y los inesperados) tiene esta forma:

```json
{
  "error": {
    "codigo": "ARCHIVO_DEMASIADO_GRANDE",
    "mensaje": "El archivo pesa 7,2 MB. El máximo es 5 MB.",
    "sugerencia": "Elimina hojas o columnas que no necesites y vuelve a intentarlo.",
    "detalle": { "tamano_mb": 7.2, "max_mb": 5 }
  }
}
```

`codigo` es estable y lo usa el frontend para decidir qué hacer. `mensaje` está en español, es comprensible para una persona sin conocimientos técnicos y **nunca** contiene texto de excepciones internas, rutas ni contenido de celdas. `sugerencia` y `detalle` son opcionales.

| HTTP | `codigo` | Cuándo |
|---|---|---|
| 400 | `PETICION_NO_VALIDA` | Cuerpo mal formado, campos que faltan o con tipo incorrecto, no llegó el campo `archivo`. |
| 404 | `ARCHIVO_NO_ENCONTRADO` | El `dataset_id` no existe o ya caducó. |
| 404 | `RUTA_NO_ENCONTRADA` | Ruta inexistente bajo `/api`. |
| 405 | `METODO_NO_PERMITIDO` | Método HTTP no admitido en esa ruta. |
| 413 | `ARCHIVO_DEMASIADO_GRANDE` | Supera `max_mb`. Se rechaza sin leer el resto del cuerpo. |
| 415 | `FORMATO_NO_SOPORTADO` | La extensión no es `xlsx`, `xls` ni `csv`. |
| 415 | `CONTENIDO_NO_COINCIDE` | El contenido real no corresponde a la extensión (incluye Excel protegido con contraseña y HTML guardado como `.xls`). |
| 422 | `ARCHIVO_ILEGIBLE` | Archivo dañado o que no se puede leer. |
| 422 | `ARCHIVO_VACIO` | Sin columnas o sin filas con datos. |
| 422 | `TABLA_DEMASIADO_GRANDE` | Más de `max_filas` filas, `max_columnas` columnas o `max_celdas` celdas, o un `.xlsx` que al descomprimirse supera el límite seguro. |
| 422 | `COLUMNA_NO_ENCONTRADA` | La columna pedida no existe. |
| 422 | `COLUMNAS_IGUALES` | En un cruce, fila y columna son la misma. |
| 422 | `RANGO_NO_VALIDO` | Un rango no se entiende. `detalle.rango` trae el texto problemático. |
| 422 | `RANGO_REPETIDO` | El mismo rango dos veces. |
| 422 | `DEMASIADOS_RANGOS` | Más de 50 rangos. |
| 422 | `RANGOS_EN_COLUMNA_NO_NUMERICA` | Se pidieron rangos para una columna que no es numérica. |
| 422 | `RANGOS_SOLAPADOS_EN_CRUCE` | En un cruce, un mismo valor cae en dos rangos (contaría doble). |
| 422 | `SIN_DATOS` | La columna (o la pareja de columnas) no tiene ningún valor. |
| 422 | `DEMASIADAS_CATEGORIAS` | Un cruce tendría más de 100 filas, 100 columnas o 2 500 celdas, o una frecuencia sin rangos tendría más de `max_valores_distintos` (1 000) valores distintos. En ese último caso `detalle` es `{ "valores_distintos": N, "maximo": 1000 }`. |
| 500 | `ERROR_INTERNO` | Cualquier otro fallo. Mensaje genérico; el detalle se registra solo en el servidor y sin contenido de datos. |

## Avisos

Los avisos no son errores: acompañan a un resultado válido.

```json
{ "codigo": "RANGOS_SOLAPADOS", "nivel": "atencion", "mensaje": "Los rangos 30-39 y 35-45 se solapan: 12 registros se cuentan dos veces." }
```

`nivel` es `"info"` o `"atencion"`. Códigos usados: `ENCABEZADOS_DUDOSOS`, `COLUMNAS_REPETIDAS`, `VARIAS_HOJAS`, `FILAS_VACIAS_OMITIDAS`, `VALORES_PARECIDOS`, `RANGOS_SOLAPADOS`, `VALORES_NO_NUMERICOS`.

---

## `GET /api/salud`

`200` con `{ "estado": "ok" }`. Para comprobar que el servidor está arriba.

## `GET /api/configuracion`

Límites vigentes, para que el frontend los muestre y valide antes de enviar. El servidor siempre vuelve a validar.

```json
{
  "max_mb": 5,
  "max_bytes": 5242880,
  "formatos": ["xlsx", "xls", "csv"],
  "minutos_inactividad": 30,
  "max_filas": 100000,
  "max_columnas": 200,
  "max_celdas": 2000000
}
```

## `POST /api/datasets`

`multipart/form-data` con un único campo `archivo`. Respuesta `201`:

```json
{
  "dataset_id": "kV3x9b0q2Yf8mZpL1sWc7A",
  "nombre": "pacientes-ficticios.xlsx",
  "formato": "xlsx",
  "filas": 200,
  "columnas": [
    { "nombre": "Edad", "tipo": "numerica", "vacios": 3, "distintos": 47,
      "no_numericos": 0, "minimo": 18, "maximo": 92 },
    { "nombre": "Sexo", "tipo": "texto", "vacios": 0, "distintos": 2,
      "no_numericos": 0, "minimo": null, "maximo": null }
  ],
  "avisos": [],
  "expira_en_segundos": 1800
}
```

- `nombre` es solo para mostrar: se reduce al nombre de archivo (sin rutas), sin caracteres de control y a un máximo de 120 caracteres. Nunca se usa para tocar el disco.
- `tipo` es `"numerica"`, `"texto"` o `"fecha"` (ver reglas de tipos).
- `minimo` y `maximo` solo existen en columnas `numerica`; en las demás son `null`.

## `GET /api/datasets/{dataset_id}`

Devuelve la misma estructura que la subida (sin `avisos` nuevos: lista vacía) y renueva el plazo. Sirve para recuperar el archivo si se recarga la página. `404` si caducó.

## `GET /api/datasets/{dataset_id}/filas?desde=0&cantidad=50`

Filas tal como se muestran, para la vista de datos. `desde` ≥ 0; `cantidad` entre 1 y 200 (50 por defecto). Todas las celdas son texto ya formateado; las vacías son `""`.

```json
{
  "total": 200,
  "desde": 0,
  "cantidad": 50,
  "columnas": ["Edad", "Sexo"],
  "filas": [["34", "Femenino"], ["", "Masculino"]]
}
```

## `POST /api/datasets/{dataset_id}/frecuencias`

```json
{ "columna": "Edad", "rangos": ["<30", "30-39", "40-59", ">=60"] }
```

`rangos` es opcional. Vacío u omitido = contar cada valor distinto. Solo se admite en columnas `numerica`.

Respuesta:

```json
{
  "columna": "Edad",
  "tipo": "numerica",
  "agrupado": true,
  "n": 197,
  "vacios_excluidos": 3,
  "filas": [
    { "tipo": "rango", "etiqueta": "Menos de 30", "rango": "<30",   "frecuencia": 41, "porcentaje": 20.81 },
    { "tipo": "rango", "etiqueta": "30 a 39",     "rango": "30-39", "frecuencia": 52, "porcentaje": 26.39 },
    { "tipo": "rango", "etiqueta": "40 a 59",     "rango": "40-59", "frecuencia": 68, "porcentaje": 34.52 },
    { "tipo": "rango", "etiqueta": "60 o más",    "rango": ">=60",  "frecuencia": 36, "porcentaje": 18.27 }
  ],
  "solapados": 0,
  "avisos": []
}
```

- `n` = valores no vacíos de la columna. Es la base de todos los porcentajes (igual que hoy).
- `vacios_excluidos` = filas del archivo donde esta columna está vacía.
- `filas[].tipo`:
  - `"valor"`: un valor distinto (sin rangos). `rango` es `null`.
  - `"rango"`: un rango pedido, en el orden en que se enviaron.
  - `"fuera_de_rango"`: valores numéricos que no entran en ningún rango. Solo aparece si hay al menos uno. Etiqueta: "Fuera de los rangos".
  - `"sin_valor_numerico"`: valores no numéricos en una columna numérica (por ejemplo "N/D"), solo con rangos y solo si hay. Etiqueta: "Sin valor numérico".
- `solapados` = cuántos registros caen en más de un rango (0 si no hay solapes). Si es mayor que 0, la suma de las filas supera `n` y hay un aviso `RANGOS_SOLAPADOS`.
- Sin rangos, `agrupado` es `false` y `solapados` es `0`. Si la columna tiene más de `max_valores_distintos` (1 000) valores distintos no se devuelve la tabla: `422 DEMASIADAS_CATEGORIAS` (ver «Precisiones»).
- Porcentajes con 2 decimales. El frontend los muestra con 1 decimal y coma decimal.

## `POST /api/datasets/{dataset_id}/tabla-cruzada`

```json
{
  "fila":    { "columna": "Edad", "rangos": ["<30", "30-39", "40+"] },
  "columna": { "columna": "Sexo" }
}
```

`rangos` es opcional en cada eje, con las mismas reglas que en frecuencias. Los rangos no pueden solaparse.

Respuesta:

```json
{
  "fila":    { "columna": "Edad", "agrupado": true },
  "columna": { "columna": "Sexo", "agrupado": false },
  "n": 197,
  "vacios_excluidos": 3,
  "columnas": [
    { "tipo": "valor", "etiqueta": "Femenino",  "rango": null },
    { "tipo": "valor", "etiqueta": "Masculino", "rango": null }
  ],
  "filas": [
    { "tipo": "rango", "etiqueta": "Menos de 30", "rango": "<30", "total": 41,
      "celdas": [ { "frecuencia": 23, "porcentaje": 56.1 },
                  { "frecuencia": 18, "porcentaje": 43.9 } ] }
  ],
  "totales_columna": [
    { "frecuencia": 104, "porcentaje": 52.8 },
    { "frecuencia": 93,  "porcentaje": 47.2 }
  ],
  "avisos": []
}
```

- `n` = filas del archivo donde **ambas** columnas tienen valor. `vacios_excluidos` = las que se descartan por tener alguna vacía.
- `celdas` tiene un elemento por cada elemento de `columnas`, en el mismo orden. El porcentaje de una celda es sobre el `total` de su fila (1 decimal). `totales_columna[i].porcentaje` es sobre `n`.
- Los ejes con rangos añaden, si hay, las categorías `"fuera_de_rango"` y `"sin_valor_numerico"` con la misma regla que en frecuencias. Así cada registro cae en exactamente una fila y una columna, y `sum(total de filas) == n`.

## `DELETE /api/datasets/{dataset_id}`

`204` sin cuerpo. Es idempotente: también responde `204` si el archivo ya no existe.

---

## Reglas de cálculo

Son las reglas que comparten el backend y las pruebas. El frontend no las reimplementa, salvo la validación de sintaxis de rangos (que el servidor repite).

### Lectura del archivo

- Solo se lee la primera hoja. Si hay otras hojas **con datos**, aviso `VARIAS_HOJAS` (info). Las hojas vacías no avisan.
- La fila 1 son los encabezados. Si más de la mitad de las columnas no tienen nombre (`Unnamed`), aviso `ENCABEZADOS_DUDOSOS` (atencion): "La primera fila no parece tener nombres de columna."
- Se descartan las columnas totalmente vacías y las filas totalmente vacías. Si se descartó alguna fila, aviso `FILAS_VACIAS_OMITIDAS` (info) con la cantidad.
- Nombres de columna: texto, sin espacios en los extremos. Una columna sin nombre pasa a llamarse `Columna N` (N = posición, desde 1). Si hay nombres repetidos aparece un aviso `COLUMNAS_REPETIDAS` y el segundo se renombra `Edad (2)`, el tercero `Edad (3)`.
- CSV: se detecta la codificación (UTF-8 con o sin BOM; si no es válido, Windows-1252) y el separador (`,` `;` o tabulador) mirando las primeras líneas. Todo se lee como texto y el tipo lo decide DataTab.
- Excel (`xlsx`, `xls`): los números llegan como números, las fechas como fechas, los textos como texto.

### Valor normalizado

Todo valor no vacío se convierte a un texto de presentación, y con ese texto se cuenta:

- Texto: se quitan espacios al inicio y al final y las secuencias de espacios internos se reducen a uno. Un texto que queda vacío es un valor vacío.
- Números: sin decimales sobrantes (`30.0` → `30`), con punto decimal (`1.5`), sin notación científica.
- Fechas: `AAAA-MM-DD`, o `AAAA-MM-DD HH:MM` si tienen hora.
- Booleanos: `Verdadero` / `Falso`.

Mayúsculas, minúsculas y tildes **no** se unifican, porque podría ocultar errores de captura; en su lugar, si dos valores solo se diferencian por eso, aviso `VALORES_PARECIDOS` (info): "«Masculino» y «masculino» parecen el mismo valor pero se cuentan por separado." (hasta 3 ejemplos).

### Tipos de columna

- `fecha`: todos los valores no vacíos son fechas.
- `numerica`: al menos el 90 % de los valores no vacíos son números. Cuentan como número los valores numéricos y los textos que lo parecen (`"34"`, `"1,5"`, `"-2.5"`, con coma o punto decimal, sin separador de miles). `no_numericos` = el resto. Un valor `"31-40"` o `"N/D"` no es número.
- `texto`: todo lo demás.

Una columna numérica con `no_numericos > 0` genera aviso `VALORES_NO_NUMERICOS` (info) al calcular con rangos.

### Rangos

Sintaxis (espacios alrededor se ignoran; coma o punto decimal; negativos permitidos):

| Texto | Significa | Etiqueta |
|---|---|---|
| `<30` | menor que 30 | `Menos de 30` |
| `<=30` o `≤30` | 30 o menos | `30 o menos` |
| `>60` | mayor que 60 | `Más de 60` |
| `>=60` o `≥60` | 60 o más | `60 o más` |
| `40+` | 40 o más | `40 o más` |
| `30-39` (también `–`) | de 30 a 39, **ambos incluidos** | `30 a 39` |

- `-5-10` es de −5 a 10. En `a-b`, `a` no puede ser mayor que `b`.
- Dos rangos son el mismo si significan lo mismo (`40+` y `>=40`): `RANGO_REPETIDO`.
- Los decimales que caen entre rangos enteros (39,5 entre `30-39` y `40-59`) quedan en "Fuera de los rangos". Se muestra y no se esconde.
- Solapes en frecuencias: se calculan y avisan. En cruces: error.

### Orden de las filas

- Frecuencias sin rangos: columna `numerica` y `fecha` de menor a mayor; `texto` de mayor a menor frecuencia y, en empate, alfabético sin distinguir tildes ni mayúsculas.
- Con rangos: el orden en que se enviaron, y al final "Fuera de los rangos" y "Sin valor numérico".
- Cruces: ejes ordenados como un orden natural (números y fechas ascendentes, texto alfabético sin distinguir tildes ni mayúsculas).

### Límites de seguridad

`max_bytes` = 5 MB, `max_filas` = 100 000, `max_columnas` = 200, `max_celdas` = 2 000 000, y un `.xlsx` no puede descomprimirse a más de 200 MB en total. Una frecuencia sin rangos admite como mucho `max_valores_distintos` = 1 000 valores distintos. Todos se pueden cambiar con variables de entorno `DATATAB_*` (ver `.env.example`).

---

## Precisiones de la implementación del backend

Filas añadidas al contrato al implementarlo. No cambian nada de lo anterior: concretan casos que el texto no cubría.

| Tema | Regla |
|---|---|
| Rangos vacíos | Los textos vacíos o de solo espacios dentro de `rangos` se ignoran. Si no queda ninguno, es como no enviar `rangos`. |
| `filas.cantidad` | Es el número de filas realmente devueltas: menor que la pedida al final del archivo, y `0` (con `filas: []`) si `desde` supera el total. |
| `FILAS_VACIAS_OMITIDAS` | Cuenta las filas vacías que hay entre filas con datos. Las vacías al final de la hoja no se cuentan ni avisan. |
| `Columna N` | `N` es la posición original de la columna en la hoja (A = 1), aunque se hayan descartado columnas vacías a su izquierda. |
| Textos que parecen número | En una columna `numerica` se escriben en forma canónica: `"007"` → `7`, `"1,5"` → `1.5`, `"30.0"` → `30`. En una columna `texto` no se tocan. |
| Fechas en CSV | En CSV solo se detectan como `fecha` las ISO (`AAAA-MM-DD`, con `HH:MM` opcional). `05/01/2024` queda como `texto`. En Excel, las celdas con formato de fecha sí son `fecha`. |
| Valores no numéricos | En una columna `numerica` sin rangos, los valores que no son número (`N/D`) salen al final de la tabla. |
| Tope de valores distintos | Las frecuencias sin rangos devuelven una fila por valor distinto; en una columna casi sin repeticiones (un identificador) serían tantas filas como registros. Por eso, si hay más de `DATATAB_MAX_VALORES_DISTINTOS` (1 000 por defecto) responden `422 DEMASIADAS_CATEGORIAS` con el mensaje «X» tiene N valores distintos; son demasiados para una tabla de frecuencias. (N con punto de miles: «1.001»), `detalle` `{ "valores_distintos": N, "maximo": 1000 }` y una sugerencia: en una columna `numerica`, «Agrúpalos en rangos, por ejemplo 0-9, 10-19…»; en las demás, «Elige otra columna o limpia el archivo para unificar valores parecidos.». Exactamente el máximo se calcula. Se cuentan los valores distintos no vacíos (en una columna `numerica` también los no numéricos, como `N/D`). Con rangos no aplica: la tabla tiene como mucho 52 filas. |
| Tamaño en `413` | `detalle.tamano_mb` (decimal, redondeado hacia arriba) solo está cuando el servidor conoce el tamaño (por `Content-Length` o por el archivo recibido). Si el cuerpo llega sin longitud y se corta al pasar el límite, `detalle` solo trae `max_mb`. La respuesta lleva `Connection: close`. |
| Qué mide el límite | `max_bytes` se aplica a los bytes del **archivo**. El cuerpo `multipart` puede superarlo hasta 64 KB (el sobre del formulario); más que eso se rechaza sin leer el resto. |
| `PETICION_NO_VALIDA` | `detalle.campos` lista los nombres de los campos con problema, sin sus valores. |
| `DATATAB_MAX_DESCOMPRIMIDO_MB` | Variable nueva (200 por defecto): el límite de 200 MB para un `.xlsx` descomprimido (ver «Límites de seguridad») pasa a ser configurable. |
| Cabeceras | Todas las respuestas llevan `X-Content-Type-Options: nosniff` y `Referrer-Policy: no-referrer`, y una `Content-Security-Policy` estricta (`default-src 'self'`...), salvo `/docs`, `/redoc` y `/openapi.json`, que cargan recursos de una CDN. Esas tres rutas se desactivan con `DATATAB_DOCS=0`. |
| `.xlsx` con DTD | Un `.xlsx` cuyo XML declara un DTD (`<!DOCTYPE`, con o sin `<!ENTITY`) se rechaza como `ARCHIVO_ILEGIBLE` antes de abrirlo: ningún Excel real lo lleva y es la vía de los ataques de expansión de entidades. |
| Rutas desconocidas | Cualquier ruta inexistente bajo `/api` responde `404 RUTA_NO_ENCONTRADA` y un método incorrecto `405 METODO_NO_PERMITIDO` (con la cabecera `Allow`), en JSON, aunque el servidor también entregue el frontend. |
