// Textos de «Cómo leerlo». Funciones puras: reciben la respuesta del servidor y devuelven frases.
// Solo describen lo que muestra la tabla: sin conclusiones médicas ni causales. La unidad es «registros».

import { cantidad, citar, enMinuscula, entero, porcentajeConSigno, unir } from '../formato.js';

// Con menos registros en una fila, un solo registro mueve su porcentaje 10 puntos o más
// (1 de 10 = 10 %). Es una regla práctica para avisar de porcentajes poco estables, no un criterio estadístico.
export const MINIMO_REGISTROS_POR_FILA = 10;

// Cuántos empatados se nombran; el resto se cuenta («y 2 más»)
const MAX_NOMBRADOS = 3;

const esCategoria = (fila) => fila.tipo === 'valor' || fila.tipo === 'rango';

const losRegistros = (n) => (n === 1 ? 'el único registro' : `los ${entero(n)} registros`);
const lasFilas = (n) => (n === 1 ? 'la única fila' : `las ${entero(n)} filas`);

function nombrar(nombres) {
  if (nombres.length <= MAX_NOMBRADOS) return unir(nombres);
  return unir([...nombres.slice(0, MAX_NOMBRADOS), `${entero(nombres.length - MAX_NOMBRADOS)} más`]);
}

/** Frases sobre los registros que no entran en ningún rango; `prefijo` abre la frase («En «Edad», »). */
function frasesFueraDeRangos(fuera, sinValor, prefijo = '') {
  const frases = [];
  if (fuera > 0) {
    frases.push(`${prefijo}${fuera === 1 ? '1 registro queda' : `${entero(fuera)} registros quedan`} fuera de los rangos.`);
  }
  if (sinValor > 0) {
    frases.push(`${prefijo}${sinValor === 1 ? '1 registro no es numérico y no entra' : `${entero(sinValor)} registros no son numéricos y no entran`} en ningún rango.`);
  }
  return frases;
}

const frecuenciaDe = (filas, tipo) => filas.find((fila) => fila.tipo === tipo)?.frecuencia ?? 0;

// ---------- Frecuencias ----------

function lecturaFrecuencias(r) {
  const candidatas = r.filas.filter(esCategoria);
  if (candidatas.length === 0) return '';
  const maxima = candidatas.reduce((mayor, fila) => Math.max(mayor, fila.frecuencia), 0);
  if (maxima === 0) return 'Ningún registro cae dentro de los rangos.';

  const empatadas = candidatas.filter((fila) => fila.frecuencia === maxima);
  const registros = cantidad(maxima, 'registro', 'registros');
  const parte = porcentajeConSigno(empatadas[0].porcentaje);

  if (empatadas.length === 1) {
    const [fila] = empatadas;
    const quien = r.agrupado
      ? `El grupo más numeroso es el de ${enMinuscula(fila.etiqueta)}`
      : `El valor más frecuente es ${citar(fila.etiqueta)}`;
    return `${quien}, con ${registros} (${parte}).`;
  }
  // Una columna sin repeticiones (un identificador) empata en todo: nombrar tres no diría nada
  if (empatadas.length > MAX_NOMBRADOS && empatadas.length === candidatas.length) {
    return `Todos los ${r.agrupado ? 'grupos' : 'valores'} tienen la misma frecuencia: ${registros} cada uno (${parte}).`;
  }
  const nombres = empatadas.map((fila) => (r.agrupado ? `el de ${enMinuscula(fila.etiqueta)}` : citar(fila.etiqueta)));
  const quienes = r.agrupado ? 'Los grupos más numerosos son' : 'Los valores más frecuentes son';
  return `${quienes} ${nombrar(nombres)}, con ${registros} cada uno (${parte}).`;
}

function limitesFrecuencias(r) {
  const columna = citar(r.columna);
  const frases = [
    r.vacios_excluidos > 0
      ? `Los porcentajes se calculan sobre ${losRegistros(r.n)} con dato en ${columna}, no sobre ${lasFilas(r.n + r.vacios_excluidos)} del archivo.`
      : `Los porcentajes se calculan sobre ${losRegistros(r.n)} del archivo; ninguno tiene vacía la columna ${columna}.`,
  ];
  frases.push(...frasesFueraDeRangos(frecuenciaDe(r.filas, 'fuera_de_rango'), frecuenciaDe(r.filas, 'sin_valor_numerico')));
  if (r.solapados > 0) {
    const cuenta = r.solapados === 1 ? '1 registro se cuenta' : `${entero(r.solapados)} registros se cuentan`;
    frases.push(`Los rangos se solapan: ${cuenta} más de una vez, así que las filas suman más que el total.`);
  }
  return frases.join(' ');
}

/** Los tres párrafos de «Cómo leerlo» para una respuesta de frecuencias. */
export function describirFrecuencias(r) {
  return {
    muestra: `Cuántos registros ${r.agrupado ? 'caen en cada rango' : 'hay de cada valor'} de ${citar(r.columna)} y qué parte del total representan.`,
    lectura: lecturaFrecuencias(r),
    limites: limitesFrecuencias(r),
  };
}

// ---------- Cruce ----------

function lecturaCruce(r) {
  const columnas = r.columnas.map((columna, indice) => ({ columna, indice })).filter(({ columna }) => esCategoria(columna));
  let maxima = 0;
  let combinaciones = [];
  for (const fila of r.filas.filter(esCategoria)) {
    for (const { columna, indice } of columnas) {
      const celda = fila.celdas[indice];
      const combinacion = { fila, columna, celda };
      if (celda.frecuencia > maxima) {
        maxima = celda.frecuencia;
        combinaciones = [combinacion];
      } else if (celda.frecuencia === maxima && maxima > 0) {
        combinaciones.push(combinacion);
      }
    }
  }
  if (combinaciones.length === 0) {
    return 'Ningún registro cae en una combinación de categorías con valor: todos quedan fuera de los rangos o sin valor numérico.';
  }

  const describir = ({ fila, columna }) => `${citar(fila.etiqueta)} con ${citar(columna.etiqueta)}`;
  if (combinaciones.length === 1) {
    const [{ celda }] = combinaciones;
    return `La combinación más frecuente es ${describir(combinaciones[0])}: ${cantidad(maxima, 'registro', 'registros')}, el ${porcentajeConSigno(celda.porcentaje)} de su fila.`;
  }
  const nombres = combinaciones.map((c) => `${describir(c)} (${porcentajeConSigno(c.celda.porcentaje)} de su fila)`);
  return `Hay ${entero(combinaciones.length)} combinaciones empatadas como las más frecuentes, con ${cantidad(maxima, 'registro', 'registros')} cada una: ${nombrar(nombres)}.`;
}

function limitesCruce(r) {
  const filaColumna = citar(r.fila.columna);
  const columnaColumna = citar(r.columna.columna);
  const frases = [`La tabla usa ${losRegistros(r.n)} con dato en ${filaColumna} y en ${columnaColumna}.`];
  if (r.vacios_excluidos === 1) {
    frases.push(`Queda fuera 1 de las ${entero(r.n + 1)} filas del archivo porque le falta alguno de los dos datos.`);
  } else if (r.vacios_excluidos > 1) {
    frases.push(`Quedan fuera ${entero(r.vacios_excluidos)} de las ${entero(r.n + r.vacios_excluidos)} filas del archivo porque les falta alguno de los dos datos.`);
  }

  const totalColumna = (tipo) => {
    const indice = r.columnas.findIndex((columna) => columna.tipo === tipo);
    return indice < 0 ? 0 : r.totales_columna[indice].frecuencia;
  };
  const totalFila = (tipo) => r.filas.find((fila) => fila.tipo === tipo)?.total ?? 0;
  frases.push(...frasesFueraDeRangos(totalFila('fuera_de_rango'), totalFila('sin_valor_numerico'), `En ${filaColumna}, `));
  frases.push(...frasesFueraDeRangos(totalColumna('fuera_de_rango'), totalColumna('sin_valor_numerico'), `En ${columnaColumna}, `));

  if (r.filas.some((fila) => fila.total < MINIMO_REGISTROS_POR_FILA)) {
    frases.push('Las filas con pocos registros dan porcentajes poco estables.');
  }
  return frases.join(' ');
}

/** Los tres párrafos de «Cómo leerlo» para una tabla cruzada. */
export function describirCruce(r) {
  return {
    muestra: `Cuántos registros hay en cada combinación de ${citar(r.fila.columna)} (filas) y ${citar(r.columna.columna)} (columnas). Cada porcentaje es la parte de su fila.`,
    lectura: lecturaCruce(r),
    limites: limitesCruce(r),
  };
}
