from fastapi import UploadFile
from app.utils.file_handler import ALLOWED_EXTENSIONS, MAX_FILE_SIZE


class ValidationError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def validate_file(file: UploadFile) -> None:
    """Valida extensión y tamaño del archivo."""
    if not file.filename:
        raise ValidationError("No se recibió ningún archivo.")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            f"Formato '{ext}' no soportado. Usa: {', '.join(ALLOWED_EXTENSIONS).upper()}"
        )
