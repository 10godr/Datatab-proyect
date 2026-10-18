// Desde Node 21, `node --test tests/` ya no recorre el directorio por su cuenta: lo trata como un
// archivo. Este índice importa todas las pruebas (*.test.mjs) para que ese comando siga funcionando.
import { readdirSync } from 'node:fs';

for (const archivo of readdirSync(new URL('.', import.meta.url)).sort()) {
  if (archivo.endsWith('.test.mjs')) await import(`./${archivo}`);
}
