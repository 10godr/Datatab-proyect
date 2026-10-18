# DataTab

Herramienta para tabular y analizar datos de un Excel/CSV: frecuencias, rangos y tablas cruzadas de 2 variables. Proyecto personal.

- Formatos: `.xlsx`, `.xls`, `.csv` (máx. 5 MB, una hoja).
- Privacidad: el archivo vive solo en la memoria del servidor y se borra tras 30 min sin uso. No se guarda en disco ni se envía a servicios externos.
- Interpretar los resultados es responsabilidad de quien los usa; DataTab no saca conclusiones médicas.

## Ejecutar en Windows (PowerShell)

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m app
```

Abre http://127.0.0.1:8000. Variables opcionales: ver `.env.example`.

## Pruebas

```powershell
cd backend; pip install -r requirements-dev.txt; python -m pytest
cd ..\frontend; node --test tests/
```

## Estructura

- `backend/` FastAPI + pandas (API JSON, contrato en `docs/api.md`).
- `frontend/` HTML + CSS + JS sin build (diseño en `docs/diseno.md`).
- `datos-de-prueba/` 3 archivos ficticios; los reales van en `datos-de-prueba/privados/` (ignorada por git).
