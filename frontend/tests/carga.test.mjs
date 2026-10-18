import assert from 'node:assert/strict';
import { test } from 'node:test';

import { validarArchivos } from '../js/vistas/carga.js';

const config = { formatos: ['xlsx', 'xls', 'csv'], max_mb: 5, max_bytes: 5 * 1024 * 1024 };
const archivo = (name, size) => ({ name, size });

test('un archivo válido pasa', () => {
  assert.equal(validarArchivos([archivo('datos.xlsx', 1000)], config), null);
  assert.equal(validarArchivos([archivo('DATOS.CSV', 5 * 1024 * 1024)], config), null); // justo en el máximo
  assert.equal(validarArchivos([archivo('a.b.xls', 1)], config), null);
});

test('más de un archivo, o ninguno', () => {
  assert.match(validarArchivos([archivo('a.csv', 1), archivo('b.csv', 1)], config).mensaje, /más de un archivo/);
  assert.match(validarArchivos([], config).mensaje, /no es un archivo/);
});

test('extensión no permitida o ausente', () => {
  const texto = validarArchivos([archivo('notas.txt', 10)], config);
  assert.equal(texto.mensaje, 'El formato .txt no es compatible.');
  assert.match(texto.sugerencia, /\.xlsx, \.xls o \.csv/);
  assert.match(validarArchivos([archivo('sin-extension', 10)], config).mensaje, /no tiene extensión/);
  // solo cuenta la última extensión
  assert.match(validarArchivos([archivo('datos.xlsx.exe', 10)], config).mensaje, /\.exe/);
});

test('archivo vacío', () => {
  assert.equal(validarArchivos([archivo('vacio.csv', 0)], config).mensaje, 'El archivo está vacío.');
});

test('archivo demasiado grande, con el mensaje del contrato', () => {
  const problema = validarArchivos([archivo('grande.xlsx', 5 * 1024 * 1024 + 1)], config);
  assert.equal(problema.mensaje, 'El archivo pesa 5,1 MB. El máximo es 5 MB.');
  assert.match(problema.sugerencia, /Elimina hojas o columnas/);
  assert.equal(
    validarArchivos([archivo('grande.xlsx', 7.2 * 1024 * 1024)], config).mensaje,
    'El archivo pesa 7,2 MB. El máximo es 5 MB.',
  );
});

test('la extensión se comprueba antes que el tamaño', () => {
  assert.match(validarArchivos([archivo('enorme.zip', 50 * 1024 * 1024)], config).mensaje, /no es compatible/);
});
