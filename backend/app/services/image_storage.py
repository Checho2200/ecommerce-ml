"""
Dónde acaban las imágenes que sube el panel de administración.

El destino es **Cloudinary** siempre que haya credenciales configuradas. Las
sirve desde su propia CDN, con un plan gratuito sin caducidad, así que las
fotos ni ocupan sitio en la base (el plan gratuito de Neon da 0.5 GB para todo,
y una imagen de 3 MB dentro de una tabla se come ese margen deprisa) ni pasan
por el backend de Render, que tarda medio minuto en despertar tras un rato sin
visitas.

Si `CLOUDINARY_URL` está vacía —y también si Cloudinary falla justo al subir—
la imagen se guarda en la tabla `uploaded_images`, que es como funcionaba
antes. Así el proyecto sigue arrancando en local sin dar de alta ninguna cuenta
y una caída del servicio externo nunca hace perder la imagen que el
administrador acaba de elegir: se guarda peor, pero se guarda.

Lo que nunca se usa es el disco del servidor: en el plan gratuito de Render es
efímero y cada despliegue lo deja vacío, que fue el motivo original de dejar de
escribir en `static/uploads`.
"""

import io
import logging
from urllib.parse import urlparse

import cloudinary
import cloudinary.uploader

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def _credenciales() -> dict | None:
    """
    Descompone `CLOUDINARY_URL` en las piezas sueltas que espera el SDK.

    El panel de Cloudinary entrega la variable ya montada con la forma
    `cloudinary://<api_key>:<api_secret>@<cloud_name>`, así que basta con
    copiar una sola cosa en Render en lugar de tres.

    Devuelve None si no hay variable o si está mal escrita; en ambos casos las
    imágenes acaban en la base de datos.
    """
    url = (get_settings().CLOUDINARY_URL or "").strip()
    if not url:
        return None

    partes = urlparse(url)
    if partes.scheme != "cloudinary" or not all(
        (partes.username, partes.password, partes.hostname)
    ):
        logger.error(
            "CLOUDINARY_URL no tiene la forma cloudinary://<api_key>:"
            "<api_secret>@<cloud_name>; las imágenes irán a la base de datos"
        )
        return None

    return {
        "cloud_name": partes.hostname,
        "api_key": partes.username,
        "api_secret": partes.password,
        # Las URLs que devuelve han de ser https: la tienda se sirve por https
        # y el navegador bloquea las imágenes que lleguen por http.
        "secure": True,
    }


def esta_configurado() -> bool:
    """Si hay credenciales utilizables. Lo usan el arranque y las pruebas."""
    return _credenciales() is not None


def subir(contenido: bytes, nombre: str) -> str | None:
    """
    Sube una imagen y devuelve su URL pública, o None si no se pudo.

    None significa "guárdala tú en la base de datos", que es lo que hace el
    endpoint de subida. Por eso aquí no se propaga ninguna excepción: un error
    de red con Cloudinary no debe convertirse en un error para el
    administrador que está creando un producto.
    """
    credenciales = _credenciales()
    if credenciales is None:
        return None

    # Se configura en cada subida en vez de una vez al arrancar: son cuatro
    # valores en un diccionario, no cuesta nada, y evita que el servidor haya
    # que reiniciarlo para que tome unas credenciales recién puestas.
    cloudinary.config(**credenciales)

    try:
        resultado = cloudinary.uploader.upload(
            io.BytesIO(contenido),
            folder=get_settings().CLOUDINARY_FOLDER,
            resource_type="image",
            # Conserva el nombre original como base para reconocer el archivo
            # en el panel de Cloudinary, pero le añade un sufijo aleatorio:
            # dos productos con una "foto.jpg" no se pisan el uno al otro.
            filename=nombre,
            use_filename=True,
            unique_filename=True,
        )
    except Exception as exc:  # noqa: BLE001 - cualquier fallo cae a la base
        logger.error("No se pudo subir la imagen a Cloudinary: %s", exc)
        return None

    url = resultado.get("secure_url") or resultado.get("url")
    if not url:
        logger.error("Cloudinary aceptó la imagen pero no devolvió su URL")
        return None

    return url
