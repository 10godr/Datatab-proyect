from fastapi import APIRouter, Request, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Optional

from app.utils.file_handler import get_filepath
from app.services.excel_service import read_file, get_preview
from app.services.stats_service import (
    calcular_frecuencias,
    calcular_frecuencias_con_rangos,
    calcular_tabla_cruzada,
)

router = APIRouter()
templates = Jinja2Templates(directory="templates")


# ── MODELOS ──────────────────────────────────

class AnalizarRequest(BaseModel):
    columna: str
    rangos: Optional[List[str]] = []


class TablacruzadaRequest(BaseModel):
    col_fila: str
    col_columna: str


# ── RUTAS ────────────────────────────────────

@router.get("/analisis", response_class=HTMLResponse)
async def analisis(
    request: Request,
    filename: Optional[str] = Cookie(None),
    original_name: Optional[str] = Cookie(None),
):
    if not filename:
        return RedirectResponse(url="/")

    filepath = get_filepath(filename)
    if not filepath:
        return RedirectResponse(url="/")

    try:
        df = read_file(filepath)
        preview = get_preview(df)
    except Exception as e:
        return HTMLResponse(f"Error al leer el archivo: {str(e)}", status_code=400)

    return templates.TemplateResponse("analisis.html", {
        "request": request,
        "filename": original_name or filename,
        "columnas": preview["columns"],
        "preview_cols": preview["columns"],
        "preview_rows": preview["rows"],
        "total_filas": preview["total_rows"],
        "total_cols": preview["total_cols"],
    })


@router.post("/api/analizar")
async def api_analizar(
    body: AnalizarRequest,
    filename: Optional[str] = Cookie(None),
):
    if not filename:
        return JSONResponse({"error": "No hay archivo cargado"}, status_code=400)

    filepath = get_filepath(filename)
    if not filepath:
        return JSONResponse({"error": "Archivo no encontrado en el servidor"}, status_code=400)

    try:
        df = read_file(filepath)
    except Exception as e:
        return JSONResponse({"error": f"Error al leer archivo: {str(e)}"}, status_code=400)

    if body.columna not in df.columns:
        return JSONResponse({"error": f"La columna '{body.columna}' no existe"}, status_code=400)

    import pandas as pd
    es_numerica = pd.api.types.is_numeric_dtype(df[body.columna].dropna())

    if body.rangos and es_numerica:
        resultado = calcular_frecuencias_con_rangos(df, body.columna, body.rangos)
    else:
        resultado = calcular_frecuencias(df, body.columna)

    return JSONResponse(resultado)


@router.post("/api/tabla-cruzada")
async def api_tabla_cruzada(
    body: TablacruzadaRequest,
    filename: Optional[str] = Cookie(None),
):
    if not filename:
        return JSONResponse({"error": "No hay archivo cargado"}, status_code=400)

    filepath = get_filepath(filename)
    if not filepath:
        return JSONResponse({"error": "Archivo no encontrado"}, status_code=400)

    try:
        df = read_file(filepath)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)

    for col in [body.col_fila, body.col_columna]:
        if col not in df.columns:
            return JSONResponse({"error": f"Columna '{col}' no encontrada"}, status_code=400)

    if body.col_fila == body.col_columna:
        return JSONResponse({"error": "Selecciona dos columnas diferentes"}, status_code=400)

    try:
        resultado = calcular_tabla_cruzada(df, body.col_fila, body.col_columna)
        return JSONResponse(resultado)
    except Exception as e:
        return JSONResponse({"error": f"Error al calcular tabla cruzada: {str(e)}"}, status_code=400)
