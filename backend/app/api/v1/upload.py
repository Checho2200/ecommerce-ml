"""
Subida de imágenes para productos y categorías.

Las imágenes se guardan en Cloudinary y el endpoint devuelve la URL de su CDN,
que es la que queda escrita en el producto. Cuando no hay credenciales de
Cloudinary —en local, por ejemplo— se guardan en la base de datos y la URL
apunta de vuelta a este mismo módulo. Los dos caminos están en
`app/services/image_storage.py`, con el porqué de cada uno.

Nada se escribe ya en el disco del servidor. Las imágenes antiguas que sigan en
/static/uploads se continúan sirviendo desde ahí, así que las URLs que ya
estaban guardadas en los productos no se rompen.
"""

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.database import get_db
from app.models.uploaded_image import UploadedImage
from app.models.user import User
from app.services import image_storage

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
    Sube una imagen y retorna la URL pública desde la que servirla.
    Solo accesible para administradores.
    - Formatos: JPEG, PNG, WebP, GIF, SVG
    - Tamaño máximo: 5 MB
    """
    # Validar tipo de archivo
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tipo de archivo no permitido. Use: JPEG, PNG, WebP, GIF o SVG",
        )

    # Leer contenido y validar tamaño
    content = await file.read()
    if len(content) > MAX_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"El archivo supera el límite de {MAX_SIZE_MB} MB",
        )

    nombre = file.filename or "imagen"

    # El SDK de Cloudinary es síncrono y la subida tarda lo que tarde la red:
    # en un hilo aparte para no dejar el servidor entero esperando.
    url = await run_in_threadpool(image_storage.subir, content, nombre)
    if url:
        return JSONResponse(content={"url": url, "filename": nombre})

    # Respaldo: sin Cloudinary configurado (o si falló), a la base de datos.
    ext = Path(nombre).suffix.lower() or ".jpg"
    imagen = UploadedImage(
        filename=f"{uuid.uuid4().hex}{ext}",
        content_type=file.content_type,
        data=content,
    )
    db.add(imagen)
    await db.flush()

    return JSONResponse(
        content={"url": f"/api/v1/upload/image/{imagen.id}", "filename": imagen.filename}
    )


@router.get("/image/{image_id}")
async def get_image(image_id: str, db: AsyncSession = Depends(get_db)):
    """Sirve una imagen guardada en la base. Pública: la ve cualquier visitante."""
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
