// Formato de cifras y textos en español. Sin DOM: se prueba con Node.

const MB = 1024 * 1024;

const formatoEntero = new Intl.NumberFormat('es', { maximumFractionDigits: 0 });
const formatoUnDecimal = new Intl.NumberFormat('es', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const formatoLibre = new Intl.NumberFormat('es', { maximumFractionDigits: 6 });

const TIPOS_DE_COLUMNA = { numerica: 'Numérica', texto: 'Texto', fecha: 'Fecha' };

/** 1234 -> "1234" y 12345 -> "12.345" (así agrupa el español). */
export function entero(n) {
  return formatoEntero.format(n);
}

/** Porcentaje con un decimal y coma: 20.81 -> "20,8". No añade el signo %. */
export function porcentaje(p) {
  return formatoUnDecimal.format(p);
}

/** Porcentaje con su signo, unidos por un espacio que no se parte: 20.81 -> "20,8 %". */
export function porcentajeConSigno(p) {
  return `${porcentaje(p)}\u00a0%`;
}

/** Número con los decimales que tenga (hasta 6): 1.5 -> "1,5", 30 -> "30". */
export function numero(n) {
  return formatoLibre.format(n);
}

/** "1 registro" / "68 registros". */
export function cantidad(n, singular, plural) {
  return `${entero(n)} ${n === 1 ? singular : plural}`;
}

export function citar(texto) {
  return `«${texto}»`;
}

/** Primera letra en minúscula, para seguir una frase: "Menos de 30" -> "menos de 30". */
export function enMinuscula(texto) {
  return texto.charAt(0).toLowerCase() + texto.slice(1);
}

/** ["a", "b", "c"] -> "a, b y c". La conjunción por defecto es "y". */
export function unir(elementos, conjuncion = 'y') {
  if (elementos.length <= 1) return elementos.join('');
  return `${elementos.slice(0, -1).join(', ')} ${conjuncion} ${elementos[elementos.length - 1]}`;
}

/** Tamaño en MB redondeado hacia arriba a un decimal, como el servidor: 7.15 MB -> "7,2". */
export function tamanoEnMB(bytes) {
  return numero(Math.ceil((bytes / MB) * 10) / 10);
}

/** ["xlsx", "xls", "csv"] -> ".xlsx, .xls y .csv". */
export function listaDeFormatos(formatos, conjuncion = 'y') {
  return unir(formatos.map((f) => `.${f}`), conjuncion);
}

/** Pista bajo el selector de columna: "Numérica · de 18 a 92 · 3 vacías". */
export function pistaColumna(columna) {
  const partes = [TIPOS_DE_COLUMNA[columna.tipo] ?? 'Texto'];
  if (columna.tipo === 'numerica' && columna.minimo != null && columna.maximo != null) {
    partes.push(`de ${numero(columna.minimo)} a ${numero(columna.maximo)}`);
  } else {
    partes.push(cantidad(columna.distintos, 'valor distinto', 'valores distintos'));
  }
  partes.push(cantidad(columna.vacios, 'vacía', 'vacías'));
  if (columna.no_numericos > 0) {
    partes.push(cantidad(columna.no_numericos, 'valor no numérico', 'valores no numéricos'));
  }
  return partes.join(' · ');
}
