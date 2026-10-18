# Datos de prueba

Todo lo que hay en esta carpeta es **inventado**: no hay personas, historias clínicas ni
identificadores reales. Sirve para probar DataTab, para las pruebas automáticas y para el botón
«Probar con datos de ejemplo».

## Archivos

| Archivo | Para qué sirve |
|---|---|
| `pacientes-ficticios.xlsx` | El ejemplo principal (200 pacientes; 3 hojas, las dos últimas vacías (no avisan); una columna final sin nombre y vacía, edades vacías, «Complicaciones» casi vacía y comorbilidades como «HTA y Diabetes»). Lo carga el botón de ejemplo (`DATATAB_EJEMPLO`). |
| `ficticio-punto-y-coma.csv` | CSV de Excel en español: separador `;`, coma decimal y codificación Windows-1252. |
| `ficticio-antiguo.xls` | Formato antiguo de Excel (`.xls`). |
| `ficticio-con-suciedad.xlsx` | Filas vacías intercaladas, «N/D» en una columna numérica y valores que solo se diferencian por mayúsculas (aviso `VALORES_PARECIDOS`). |
| `ficticio-titulo-en-primera-fila.xlsx` | Una hoja que empieza con un título en lugar de los nombres de columna (aviso `ENCABEZADOS_DUDOSOS`). |
| `generar_ficticios.py` | Vuelve a crear los archivos anteriores. Es determinista: dos ejecuciones dan archivos idénticos. |

Para regenerarlos, desde la raíz del repositorio y con las dependencias de
`backend/requirements-dev.txt`:

```
python datos-de-prueba/generar_ficticios.py
```

## Tus archivos reales: `privados/`

Si quieres probar DataTab con tus propios Excel, déjalos en una carpeta `datos-de-prueba/privados/`
(créala tú). El `.gitignore` de la raíz del repositorio ya la ignora, así que git no la ve y no se sube nunca al repositorio.
DataTab no guarda nada en disco: el archivo se lee en memoria y se borra a los 30 minutos sin actividad
o al cerrar el servidor.

Aun así, antes de compartir una captura o un archivo, comprueba que no contiene datos de personas.
