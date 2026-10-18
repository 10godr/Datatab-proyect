import assert from 'node:assert/strict';
import { test } from 'node:test';

import { interpretarRango, MAX_RANGOS, validarRango } from '../js/ui/rangos.js';

test('interpretarRango entiende toda la sintaxis del contrato', () => {
  const casos = [
    ['<30', 'Menos de 30'],
    ['<=30', '30 o menos'],
    ['≤30', '30 o menos'],
    ['>60', 'Más de 60'],
    ['>=60', '60 o más'],
    ['≥60', '60 o más'],
    ['40+', '40 o más'],
    ['30-39', '30 a 39'],
    ['30–39', '30 a 39'],
    ['-5-10', '-5 a 10'],
    ['-5--3', '-5 a -3'],
    ['1,5-2.5', '1,5 a 2,5'],
    ['.5+', '0,5 o más'],
    ['  < 30 ', 'Menos de 30'],
    ['30 - 39', '30 a 39'],
    ['40 +', '40 o más'],
    ['39-39', '39 a 39'],
    ['<-2', 'Menos de -2'],
  ];
  for (const [texto, etiqueta] of casos) {
    const rango = interpretarRango(texto);
    assert.equal(rango.ok, true, texto);
    assert.equal(rango.etiqueta, etiqueta, texto);
  }
});

test('interpretarRango guarda los límites con su inclusión', () => {
  assert.deepEqual(
    (({ minimo, incluyeMinimo, maximo, incluyeMaximo }) => ({ minimo, incluyeMinimo, maximo, incluyeMaximo }))(interpretarRango('30-39')),
    { minimo: 30, incluyeMinimo: true, maximo: 39, incluyeMaximo: true },
  );
  const menorQue = interpretarRango('<30');
  assert.equal(menorQue.minimo, -Infinity);
  assert.equal(menorQue.incluyeMaximo, false);
  const oMas = interpretarRango('40+');
  assert.equal(oMas.maximo, Infinity);
  assert.equal(oMas.incluyeMinimo, true);
});

test('interpretarRango rechaza lo que no es un rango', () => {
  const casos = [
    ['', 'vacio'],
    ['   ', 'vacio'],
    ['abc', 'no_valido'],
    ['30', 'no_valido'],
    ['-5', 'no_valido'],
    ['30-', 'no_valido'],
    ['30-40-50', 'no_valido'],
    ['>=', 'no_valido'],
    ['=30', 'no_valido'],
    ['30++', 'no_valido'],
    ['1e3+', 'no_valido'],
    ['40-30', 'invertido'],
    ['5 - -3', 'invertido'],
    ['1'.repeat(41) + '+', 'largo'],
  ];
  for (const [texto, motivo] of casos) {
    const rango = interpretarRango(texto);
    assert.equal(rango.ok, false, texto);
    assert.equal(rango.motivo, motivo, texto);
  }
});

test('validarRango detecta duplicados por significado, no por texto', () => {
  assert.equal(validarRango('30-39', []).ok, true);

  const igualPorTexto = validarRango('30-39', ['30-39']);
  assert.equal(igualPorTexto.ok, false);
  assert.match(igualPorTexto.mensaje, /«30-39» ya está añadido\./);

  const igualPorSignificado = validarRango('40+', ['>=40']);
  assert.equal(igualPorSignificado.ok, false);
  assert.match(igualPorSignificado.mensaje, /«40\+» ya está añadido: significa lo mismo que «>=40»\./);

  assert.equal(validarRango('≥40', ['40+']).ok, false);
  assert.equal(validarRango('30–39', ['30-39']).ok, false);
  // <30 y <=29 no significan lo mismo: hay decimales entre 29 y 30
  assert.equal(validarRango('<=29', ['<30']).ok, true);
});

test('validarRango explica los errores en español', () => {
  assert.match(validarRango('abc', []).mensaje, /No se entiende «abc»\. Escribe un rango como 30-39, <30, >=60 o 40\+\./);
  assert.match(validarRango('40-30', []).mensaje, /primer número es mayor que el segundo/);
  assert.match(validarRango('', []).mensaje, /Escribe un rango/);
});

test('validarRango limita el número de rangos', () => {
  const existentes = Array.from({ length: MAX_RANGOS }, (_, i) => `${i * 10}-${i * 10 + 9}`);
  const resultado = validarRango('1000-1009', existentes);
  assert.equal(resultado.ok, false);
  assert.match(resultado.mensaje, /Ya hay 50 rangos/);
  assert.equal(validarRango('1000-1009', existentes.slice(1)).ok, true);
});

test('validarRango acorta el texto de un rango muy largo en el mensaje', () => {
  const largo = 'x'.repeat(35);
  const { mensaje } = validarRango(largo, []);
  assert.ok(!mensaje.includes(largo));
  assert.ok(mensaje.includes('…'));
});
