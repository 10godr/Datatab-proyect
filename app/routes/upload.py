from fastapi import APIRouter, File, UploadFile, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.utils.file_handler import save_upload
from app.utils.validators import validate_file, ValidationError
from app.services.excel_service import read_file

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@router.post("/upload")
async def upload_file(request: Request, file: UploadFile = File(...)):
    try:
        validate_file(file)
        safe_name, filepath = save_upload(file)
        read_file(filepath)  # Verificar que se pueda leer
    except ValidationError as e:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "error": e.message
        }, status_code=400)
    except Exception as e:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "error": f"No se pudo leer el archivo: {str(e)}"
        }, status_code=400)

    response = RedirectResponse(url="/analisis", status_code=303)
    response.set_cookie(key="filename", value=safe_name)
    response.set_cookie(key="original_name", value=file.filename)
    return response
