# Datos de prueba

Tres archivos inventados (no hay personas reales). Son para probar la herramienta a mano.

| Archivo | Qué es |
|---|---|
| `pacientes-ficticios.xlsx` | 200 pacientes con 16 variables variadas (sexo, edad, ocupación, ciudad, diagnóstico, comorbilidad, peso, fecha de ingreso, satisfacción…). |
| `encuesta-escolar.csv` | Encuesta escolar (no médica) en CSV de Excel en español: separador `;`, Windows-1252. |
| `ventas-tienda.xls` | Ventas de una tienda en formato antiguo de Excel (`.xls`). |

`generar_datos_de_prueba.py` los vuelve a crear (`python datos-de-prueba/generar_datos_de_prueba.py`).

Tus archivos reales van en `datos-de-prueba/privados/`: git los ignora y nunca se suben.
Los archivos que usan las pruebas automáticas (con casos raros a propósito) están aparte, en `backend/tests/fixtures/datos/`.
