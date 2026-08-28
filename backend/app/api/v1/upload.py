"""
Endpoint de upload de imagenes para productos y categorias.

Las imagenes se guardan en la base de datos, no en disco: el plan gratuito de
Render tiene sistema de archivos efimero y cada redespliegue borraba lo subido.
Las imagenes antiguas que sigan en /static/uploads se continuan sirviendo desde
ahi, asi que las URLs ya guardadas en productos no se rompen.
"""

import os
import uuid

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.database import get_db
from app.models.uploaded_image import UploadedImage
from app.models.user import User

router = APIRouter(prefix="/upload", tags=["Upload"])

# Tipos de archivo permitidos
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/svg+xml"}
MAX_SIZE_MB = 5


@router.post("/image", status_code=status.HTTP_200_OK)
async def upload_image(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """
    Sube una imagen y retorna la URL publica desde la que servirla.
    Solo accesible para administradores.
    - Formatos: JPEG, PNG, WebP, GIF, SVG
    - Tamano maximo: 5 MB
    """
    # Validar tipo de archivo
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tipo de archivo no permitido. Use: JPEG, PNG, WebP, GIF o SVG",
        )

    # Leer contenido y validar tamano
    content = await file.read()
    if len(content) > MAX_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"El archivo supera el limite de {MAX_SIZE_MB} MB",
        )

    ext = os.path.splitext(file.filename or "image")[1].lower() or ".jpg"
    imagen = UploadedImage(
        filename=f"{uuid.uuid4().hex}{ext}",
        content_type=file.content_type,
        data=content,
    )
    db.add(imagen)
    await db.flush()

    url = f"/api/v1/upload/image/{imagen.id}"
    return JSONResponse(content={"url": url, "filename": imagen.filename})


@router.get("/image/{image_id}")
async def get_image(image_id: str, db: AsyncSession = Depends(get_db)):
    """Sirve una imagen subida. Publico: las ve cualquier visitante de la tienda."""
    imagen = await db.get(UploadedImage, image_id)

    if imagen is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Imagen no encontrada",
        )

    return Response(
        content=imagen.data,
        media_type=imagen.content_type,
        # El contenido de una URL nunca cambia: cada subida genera un id nuevo.
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )
