import assert from 'node:assert/strict';
import { test } from 'node:test';

import { describirCruce, describirFrecuencias, MINIMO_REGISTROS_POR_FILA } from '../js/ui/lectura.js';

const fila = (tipo, etiqueta, frecuencia, porcentaje) => ({ tipo, etiqueta, rango: null, frecuencia, porcentaje });
const frecuencias = (cambios) => ({
  columna: 'Edad', tipo: 'numerica', agrupado: true, n: 197, vacios_excluidos: 3, solapados: 0, avisos: [], filas: [], ...cambios,
});
const porRangos = [
  fila('rango', 'Menos de 30', 41, 20.81),
  fila('rango', '30 a 39', 52, 26.39),
  fila('rango', '40 a 59', 68, 34.52),
  fila('rango', '60 o más', 36, 18.27),
];

test('frecuencias con rangos: qué muestra, lectura y límites', () => {
  const texto = describirFrecuencias(frecuencias({ filas: porRangos }));
  assert.equal(texto.muestra, 'Cuántos registros caen en cada rango de «Edad» y qué parte del total representan.');
  assert.equal(texto.lectura, 'El grupo más numeroso es el de 40 a 59, con 68 registros (34,5 %).');
  assert.equal(
    texto.limites,
    'Los porcentajes se calculan sobre los 197 registros con dato en «Edad», no sobre las 200 filas del archivo.',
  );
});

test('frecuencias sin rangos: cuenta valores', () => {
  const texto = describirFrecuencias(frecuencias({
    columna: 'Sexo', agrupado: false, n: 200, vacios_excluidos: 0,
    filas: [fila('valor', 'Femenino', 104, 52), fila('valor', 'Masculino', 96, 48)],
  }));
  assert.equal(texto.muestra, 'Cuántos registros hay de cada valor de «Sexo» y qué parte del total representan.');
  assert.equal(texto.lectura, 'El valor más frecuente es «Femenino», con 104 registros (52,0 %).');
  assert.equal(texto.limites, 'Los porcentajes se calculan sobre los 200 registros del archivo; ninguno tiene vacía la columna «Sexo».');
});

test('un rango con límite abierto sigue la frase con minúscula', () => {
  const texto = describirFrecuencias(frecuencias({
    filas: [fila('rango', 'Menos de 30', 90, 45.7), fila('rango', '60 o más', 10, 5.1)],
  }));
  assert.equal(texto.lectura, 'El grupo más numeroso es el de menos de 30, con 90 registros (45,7 %).');
});

test('un empate nombra hasta tres y cuenta el resto', () => {
  const dos = describirFrecuencias(frecuencias({
    columna: 'Sexo', agrupado: false,
    filas: [fila('valor', 'A', 68, 34.5), fila('valor', 'B', 68, 34.5), fila('valor', 'C', 10, 5.1)],
  }));
  assert.equal(dos.lectura, 'Los valores más frecuentes son «A» y «B», con 68 registros cada uno (34,5 %).');

  const cinco = describirFrecuencias(frecuencias({
    columna: 'Dx', agrupado: false,
    filas: ['A', 'B', 'C', 'D', 'E'].map((v) => fila('valor', v, 68, 34.5)).concat(fila('valor', 'F', 3, 1.5)),
  }));
  assert.equal(cinco.lectura, 'Los valores más frecuentes son «A», «B», «C» y 2 más, con 68 registros cada uno (34,5 %).');

  const grupos = describirFrecuencias(frecuencias({
    filas: [fila('rango', '30 a 39', 52, 26.4), fila('rango', '40 a 59', 52, 26.4), fila('rango', '60 o más', 5, 2.5)],
  }));
  assert.equal(grupos.lectura, 'Los grupos más numerosos son el de 30 a 39 y el de 40 a 59, con 52 registros cada uno (26,4 %).');
});

test('si todos los valores empatan (un identificador) no se nombra a nadie', () => {
  const texto = describirFrecuencias(frecuencias({
    columna: 'Id', agrupado: false, n: 5, vacios_excluidos: 0,
    filas: ['a', 'b', 'c', 'd', 'e'].map((v) => fila('valor', v, 1, 20)),
  }));
  assert.equal(texto.lectura, 'Todos los valores tienen la misma frecuencia: 1 registro cada uno (20,0 %).');
});

test('la lectura ignora «fuera de rango» y «sin valor numérico»', () => {
  const texto = describirFrecuencias(frecuencias({
    filas: [fila('rango', '30 a 39', 10, 5), fila('fuera_de_rango', 'Fuera de los rangos', 150, 76), fila('sin_valor_numerico', 'Sin valor numérico', 37, 19)],
  }));
  assert.equal(texto.lectura, 'El grupo más numeroso es el de 30 a 39, con 10 registros (5,0 %).');
  assert.match(texto.limites, /150 registros quedan fuera de los rangos\./);
  assert.match(texto.limites, /37 registros no son numéricos y no entran en ningún rango\./);
});

test('límites con un solo registro fuera de rango o no numérico (singular)', () => {
  const texto = describirFrecuencias(frecuencias({
    filas: [fila('rango', '30 a 39', 195, 99), fila('fuera_de_rango', 'Fuera de los rangos', 1, 0.5), fila('sin_valor_numerico', 'Sin valor numérico', 1, 0.5)],
  }));
  assert.match(texto.limites, / 1 registro queda fuera de los rangos\./);
  assert.match(texto.limites, / 1 registro no es numérico y no entra en ningún rango\./);
});

test('con rangos solapados avisa de que la suma supera el total', () => {
  const texto = describirFrecuencias(frecuencias({ solapados: 12, filas: porRangos }));
  assert.match(texto.limites, /Los rangos se solapan: 12 registros se cuentan más de una vez, así que las filas suman más que el total\./);
  assert.match(describirFrecuencias(frecuencias({ solapados: 1, filas: porRangos })).limites, /1 registro se cuenta más de una vez/);
});

test('si ningún registro cae en los rangos lo dice', () => {
  const texto = describirFrecuencias(frecuencias({
    filas: [fila('rango', '100 o más', 0, 0), fila('fuera_de_rango', 'Fuera de los rangos', 197, 100)],
  }));
  assert.equal(texto.lectura, 'Ningún registro cae dentro de los rangos.');
});

test('nunca habla de pacientes ni de causas', () => {
  const texto = Object.values(describirFrecuencias(frecuencias({ solapados: 2, filas: porRangos }))).join(' ');
  assert.doesNotMatch(texto, /paciente|causa|provoca|debido/i);
});

// ---------- Cruce ----------

const celda = (frecuencia, porcentaje) => ({ frecuencia, porcentaje });
const cruce = (cambios) => ({
  fila: { columna: 'Edad', agrupado: true },
  columna: { columna: 'Sexo', agrupado: false },
  n: 197,
  vacios_excluidos: 3,
  columnas: [{ tipo: 'valor', etiqueta: 'Femenino', rango: null }, { tipo: 'valor', etiqueta: 'Masculino', rango: null }],
  filas: [
    { tipo: 'rango', etiqueta: 'Menos de 30', rango: '<30', total: 41, celdas: [celda(23, 56.1), celda(18, 43.9)] },
    { tipo: 'rango', etiqueta: '30 a 39', rango: '30-39', total: 52, celdas: [celda(20, 38.5), celda(32, 61.5)] },
  ],
  totales_columna: [celda(43, 21.8), celda(50, 25.4)],
  avisos: [],
  ...cambios,
});

test('cruce: qué muestra y lectura con la combinación más frecuente', () => {
  const texto = describirCruce(cruce());
  assert.equal(
    texto.muestra,
    'Cuántos registros hay en cada combinación de «Edad» (filas) y «Sexo» (columnas). Cada porcentaje es la parte de su fila.',
  );
  assert.equal(texto.lectura, 'La combinación más frecuente es «30 a 39» con «Masculino»: 32 registros, el 61,5 % de su fila.');
});

test('cruce: límites con la base, las filas excluidas y las filas pequeñas', () => {
  const texto = describirCruce(cruce());
  assert.equal(
    texto.limites,
    'La tabla usa los 197 registros con dato en «Edad» y en «Sexo». Quedan fuera 3 de las 200 filas del archivo porque les falta alguno de los dos datos.',
  );

  const pocas = describirCruce(cruce({
    filas: [{ tipo: 'rango', etiqueta: 'Menos de 30', rango: '<30', total: 9, celdas: [celda(5, 55.6), celda(4, 44.4)] }],
  }));
  assert.match(pocas.limites, /Las filas con pocos registros dan porcentajes poco estables\.$/);
  assert.equal(MINIMO_REGISTROS_POR_FILA, 10);
});

test('cruce: una fila con exactamente 10 registros no se considera pequeña', () => {
  const texto = describirCruce(cruce({
    filas: [{ tipo: 'valor', etiqueta: 'A', rango: null, total: 10, celdas: [celda(5, 50), celda(5, 50)] }],
  }));
  assert.doesNotMatch(texto.limites, /pocos registros/);
});

test('cruce: una fila excluida en singular y sin excluidos', () => {
  assert.match(describirCruce(cruce({ vacios_excluidos: 1 })).limites, /Queda fuera 1 de las 198 filas del archivo porque le falta alguno/);
  assert.doesNotMatch(describirCruce(cruce({ vacios_excluidos: 0 })).limites, /fuera/);
});

test('cruce: empate entre combinaciones', () => {
  const texto = describirCruce(cruce({
    filas: [{ tipo: 'rango', etiqueta: 'Menos de 30', rango: '<30', total: 46, celdas: [celda(23, 50), celda(23, 50)] }],
  }));
  assert.equal(
    texto.lectura,
    'Hay 2 combinaciones empatadas como las más frecuentes, con 23 registros cada una: «Menos de 30» con «Femenino» (50,0 % de su fila) y «Menos de 30» con «Masculino» (50,0 % de su fila).',
  );
});

test('cruce: las categorías de fuera de rango no cuentan en la lectura y sí en los límites', () => {
  const texto = describirCruce(cruce({
    filas: [
      { tipo: 'rango', etiqueta: '30 a 39', rango: '30-39', total: 12, celdas: [celda(6, 50), celda(6, 50)] },
      { tipo: 'fuera_de_rango', etiqueta: 'Fuera de los rangos', rango: null, total: 100, celdas: [celda(90, 90), celda(10, 10)] },
      { tipo: 'sin_valor_numerico', etiqueta: 'Sin valor numérico', rango: null, total: 1, celdas: [celda(1, 100), celda(0, 0)] },
    ],
  }));
  assert.match(texto.lectura, /«30 a 39» con «Femenino» \(50,0 % de su fila\)/);
  assert.match(texto.limites, /En «Edad», 100 registros quedan fuera de los rangos\./);
  assert.match(texto.limites, /En «Edad», 1 registro no es numérico y no entra en ningún rango\./);
});
