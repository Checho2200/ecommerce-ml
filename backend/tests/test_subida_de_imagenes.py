"""
Pruebas de la subida de imágenes del panel de administración.

Lo que se comprueba es adónde va a parar el archivo: a Cloudinary cuando hay
credenciales, y a la base de datos cuando no las hay o cuando Cloudinary
falla. Ese respaldo es el que evita que un corte del servicio externo le
estropee al administrador el producto que está creando.

Nunca se habla con Cloudinary de verdad: se sustituye la llamada del SDK.
"""

import io

from app.core.config import get_settings
from app.models.user import UserRole
from app.services import image_storage
from tests.conftest import cabeceras_de, crear_usuario

# Un PNG de 1x1 píxel, lo mínimo que el endpoint acepta como imagen.
PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d494844520000000100000001080200000090"
    "7753de0000000c49444154789c63f8cfc0000003010100c9fe92ef000000"
    "0049454e44ae426082"
)

URL_FALSA = "cloudinary://clave:secreto@nube-de-pruebas"


async def _admin(cliente, sesion):
    await crear_usuario(sesion, email="admin@ejemplo.com", rol=UserRole.ADMIN)
    return await cabeceras_de(cliente, "admin@ejemplo.com")


async def _subir(cliente, cabeceras):
    return await cliente.post(
        "/api/v1/upload/image",
        files={"file": ("foto.png", io.BytesIO(PNG), "image/png")},
        headers=cabeceras,
    )


async def test_sin_cloudinary_la_imagen_queda_en_la_base(cliente, sesion, monkeypatch):
    monkeypatch.setattr(get_settings(), "CLOUDINARY_URL", "")
    cabeceras = await _admin(cliente, sesion)

    respuesta = await _subir(cliente, cabeceras)

    assert respuesta.status_code == 200, respuesta.text
    url = respuesta.json()["url"]
    assert url.startswith("/api/v1/upload/image/")

    # Y desde esa URL se vuelve a servir el mismo archivo, sin autenticación.
    descarga = await cliente.get(url)
    assert descarga.status_code == 200
    assert descarga.content == PNG


async def test_con_cloudinary_la_url_es_la_del_cdn(cliente, sesion, monkeypatch):
    monkeypatch.setattr(get_settings(), "CLOUDINARY_URL", URL_FALSA)
    subidas = []

    def upload_falso(archivo, **opciones):
        subidas.append((archivo.read(), opciones))
        return {"secure_url": "https://res.cloudinary.com/nube/foto.png"}

    monkeypatch.setattr(image_storage.cloudinary.uploader, "upload", upload_falso)
    cabeceras = await _admin(cliente, sesion)

    respuesta = await _subir(cliente, cabeceras)

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["url"] == "https://res.cloudinary.com/nube/foto.png"

    contenido, opciones = subidas[0]
    assert contenido == PNG
    assert opciones["folder"] == get_settings().CLOUDINARY_FOLDER
    # Nombres irrepetibles: dos productos con una "foto.png" no se pisan.
    assert opciones["unique_filename"] is True


async def test_si_cloudinary_falla_la_imagen_no_se_pierde(cliente, sesion, monkeypatch):
    monkeypatch.setattr(get_settings(), "CLOUDINARY_URL", URL_FALSA)

    def upload_que_falla(archivo, **opciones):
        raise RuntimeError("la red se cayó")

    monkeypatch.setattr(image_storage.cloudinary.uploader, "upload", upload_que_falla)
    cabeceras = await _admin(cliente, sesion)

    respuesta = await _subir(cliente, cabeceras)

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["url"].startswith("/api/v1/upload/image/")


async def test_una_url_de_cloudinary_mal_escrita_se_ignora(monkeypatch):
    monkeypatch.setattr(get_settings(), "CLOUDINARY_URL", "https://cloudinary.com/nube")

    # No se cae ni intenta subir: se comporta como si no hubiera credenciales.
    assert image_storage.esta_configurado() is False
    assert image_storage.subir(PNG, "foto.png") is None


async def test_solo_un_administrador_puede_subir(cliente, sesion):
    await crear_usuario(sesion, email="cliente@ejemplo.com")
    cabeceras = await cabeceras_de(cliente, "cliente@ejemplo.com")

    respuesta = await _subir(cliente, cabeceras)

    assert respuesta.status_code == 403
