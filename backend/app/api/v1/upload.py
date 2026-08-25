"""
Endpoint de upload de imágenes para productos y categorías.
Guarda los archivos en /static/uploads/ y retorna la URL pública.
"""

import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from fastapi.responses import JSONResponse

from app.api.deps import require_admin
from app.models.user import User

router = APIRouter(prefix="/upload", tags=["Upload"])

# Directorio donde se guardan las imágenes
UPLOAD_DIR = Path("static/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Tipos de archivo permitidos
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/svg+xml"}
MAX_SIZE_MB = 5


@router.post("/image", status_code=status.HTTP_200_OK)
async def upload_image(
    file: UploadFile = File(...),
    admin: User = Depends(require_admin),
):
    """
    Sube una imagen al servidor y retorna la URL pública.
    Solo accesible para administradores.
    - Formatos: JPEG, PNG, WebP, GIF, SVG
    - Tamaño máximo: 5 MB
    """
    # Validar tipo de archivo
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de archivo no permitido. Use: JPEG, PNG, WebP, GIF o SVG",
        )

    # Leer contenido y validar tamaño
    content = await file.read()
    if len(content) > MAX_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"El archivo supera el límite de {MAX_SIZE_MB} MB",
        )

    # Generar nombre único preservando la extensión
    ext = os.path.splitext(file.filename or "image")[1].lower()
    if not ext:
        ext = ".jpg"
    unique_filename = f"{uuid.uuid4().hex}{ext}"
    file_path = UPLOAD_DIR / unique_filename

    # Guardar el archivo
    with open(file_path, "wb") as f:
        f.write(content)

    # Retornar la URL pública
    url = f"/static/uploads/{unique_filename}"
    return JSONResponse(content={"url": url, "filename": unique_filename})
