import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  cantidad, citar, enMinuscula, entero, listaDeFormatos, numero, pistaColumna, porcentaje, porcentajeConSigno, tamanoEnMB, unir,
} from '../js/formato.js';

test('entero agrupa miles al estilo español', () => {
  assert.equal(entero(0), '0');
  assert.equal(entero(1234), '1234');
  assert.equal(entero(12345), '12.345');
  assert.equal(entero(1000000), '1.000.000');
});

test('porcentaje usa un decimal y coma', () => {
  assert.equal(porcentaje(20.81), '20,8');
  assert.equal(porcentaje(34.52), '34,5');
  assert.equal(porcentaje(100), '100,0');
  assert.equal(porcentaje(0), '0,0');
  assert.equal(porcentaje(0.04), '0,0');
});

test('porcentajeConSigno une el número y el signo con un espacio que no se parte', () => {
  assert.equal(porcentajeConSigno(34.52), '34,5\u00a0%');
  assert.equal(porcentajeConSigno(100), '100,0\u00a0%');
});

test('numero conserva los decimales que tiene, con coma', () => {
  assert.equal(numero(1.5), '1,5');
  assert.equal(numero(30), '30');
  assert.equal(numero(-2.5), '-2,5');
  assert.equal(numero(0.1 + 0.2), '0,3'); // sin ruido binario
});

test('cantidad concuerda en singular y plural', () => {
  assert.equal(cantidad(1, 'registro', 'registros'), '1 registro');
  assert.equal(cantidad(0, 'registro', 'registros'), '0 registros');
  assert.equal(cantidad(68, 'registro', 'registros'), '68 registros');
  assert.equal(cantidad(12345, 'fila', 'filas'), '12.345 filas');
});

test('tamanoEnMB redondea hacia arriba a un decimal, como el servidor', () => {
  const MB = 1024 * 1024;
  assert.equal(tamanoEnMB(5 * MB + 1), '5,1');
  assert.equal(tamanoEnMB(6 * MB), '6');
  assert.equal(tamanoEnMB(7.15 * MB), '7,2');
  assert.equal(tamanoEnMB(MB / 2), '0,5');
});

test('unir y listaDeFormatos', () => {
  assert.equal(unir([]), '');
  assert.equal(unir(['a']), 'a');
  assert.equal(unir(['a', 'b']), 'a y b');
  assert.equal(unir(['a', 'b', 'c']), 'a, b y c');
  assert.equal(unir(['a', 'b'], 'o'), 'a o b');
  assert.equal(listaDeFormatos(['xlsx', 'xls', 'csv']), '.xlsx, .xls y .csv');
  assert.equal(listaDeFormatos(['xlsx', 'xls', 'csv'], 'o'), '.xlsx, .xls o .csv');
});

test('citar y enMinuscula', () => {
  assert.equal(citar('Edad'), '«Edad»');
  assert.equal(enMinuscula('Menos de 30'), 'menos de 30');
  assert.equal(enMinuscula('30 a 39'), '30 a 39');
  assert.equal(enMinuscula(''), '');
});

test('pistaColumna describe el tipo, el contenido y los vacíos', () => {
  const numerica = { nombre: 'Edad', tipo: 'numerica', vacios: 3, distintos: 47, no_numericos: 0, minimo: 18, maximo: 92 };
  assert.equal(pistaColumna(numerica), 'Numérica · de 18 a 92 · 3 vacías');
  assert.equal(
    pistaColumna({ ...numerica, minimo: 1.5, maximo: 9.25, vacios: 1, no_numericos: 1 }),
    'Numérica · de 1,5 a 9,25 · 1 vacía · 1 valor no numérico',
  );
  assert.equal(pistaColumna({ ...numerica, no_numericos: 4 }), 'Numérica · de 18 a 92 · 3 vacías · 4 valores no numéricos');
  const texto = { nombre: 'Sexo', tipo: 'texto', vacios: 0, distintos: 2, no_numericos: 0, minimo: null, maximo: null };
  assert.equal(pistaColumna(texto), 'Texto · 2 valores distintos · 0 vacías');
  assert.equal(pistaColumna({ ...texto, distintos: 1 }), 'Texto · 1 valor distinto · 0 vacías');
  assert.equal(
    pistaColumna({ ...texto, tipo: 'fecha', distintos: 120, vacios: 5 }),
    'Fecha · 120 valores distintos · 5 vacías',
  );
});
