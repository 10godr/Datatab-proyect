import os
import uuid
import shutil
from fastapi import UploadFile

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"xlsx", "xls", "csv"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def safe_filename(original: str) -> str:
    """Genera un nombre seguro con UUID para evitar conflictos y ataques."""
    ext = original.rsplit(".", 1)[1].lower()
    return f"{uuid.uuid4().hex}.{ext}"


def save_upload(file: UploadFile) -> tuple[str, str]:
    """
    Guarda el archivo subido de forma segura.
    Retorna (nombre_seguro, ruta_completa).
    """
    safe_name = safe_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, safe_name)
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return safe_name, filepath


def delete_file(filename: str) -> None:
    """Elimina un archivo del servidor si existe."""
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(filepath):
        os.remove(filepath)


def get_filepath(filename: str) -> str | None:
    """Retorna la ruta completa si el archivo existe, si no None."""
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    return filepath if os.path.exists(filepath) else None
