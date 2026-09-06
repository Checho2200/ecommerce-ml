"""
Sube a Cloudinary las imágenes que quedaron guardadas dentro de la base.

    python -m app.scripts.migrar_imagenes_a_cloudinary            # solo mira
    python -m app.scripts.migrar_imagenes_a_cloudinary --aplicar
    python -m app.scripts.migrar_imagenes_a_cloudinary --aplicar --borrar

Antes de usar Cloudinary, cada imagen que subía el panel se guardaba en la
tabla `uploaded_images` y el producto apuntaba a `/api/v1/upload/image/<id>`.
Eso funciona, pero ocupa el espacio del plan gratuito de Neon y obliga a que
cada foto la sirva el backend de Render, que tras un rato sin visitas tarda
medio minuto en despertar.

Este script sube cada una a Cloudinary y reescribe las URLs de los productos y
las categorías que apuntaban a ella. Sin `--aplicar` no toca nada: enseña lo
que haría. `--borrar` vacía además la fila de `uploaded_images`, que es lo que
libera el espacio de verdad; conviene dejarlo para una segunda pasada, cuando
ya se haya visto la tienda con las imágenes nuevas.
"""

import argparse
import asyncio
import sys

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.product import Category, Product
from app.models.uploaded_image import UploadedImage
from app.services import image_storage


async def _referencias(db, ruta: str) -> list:
    """
    Productos y categorías cuya imagen es esta.

    Se busca por el final de la URL porque la misma imagen quedó guardada de
    dos formas: la ruta a secas y la ruta con el dominio del backend delante,
    según desde dónde se subiera.
    """
    filas = []
    for modelo in (Product, Category):
        resultado = await db.execute(
            select(modelo).where(modelo.image_url.like(f"%{ruta}"))
        )
        filas.extend(resultado.scalars().all())
    return filas


async def migrar(aplicar: bool, borrar: bool) -> int:
    if not image_storage.esta_configurado():
        print(
            "Falta CLOUDINARY_URL en el entorno: sin credenciales no hay "
            "adónde subir las imágenes."
        )
        return 1

    async with AsyncSessionLocal() as db:
        imagenes = (await db.execute(select(UploadedImage))).scalars().all()

        if not imagenes:
            print("No hay imágenes guardadas en la base. Nada que mover.")
            return 0

        print(f"{len(imagenes)} imagen(es) guardadas en la base de datos.")
        if not aplicar:
            print("Ensayo: no se va a modificar nada (añade --aplicar).\n")

        movidas = 0
        fallidas = 0

        for imagen in imagenes:
            ruta = f"/api/v1/upload/image/{imagen.id}"
            usos = await _referencias(db, ruta)
            tamano = len(imagen.data) // 1024
            etiqueta = f"{imagen.filename} ({tamano} KB, {len(usos)} uso/s)"

            if not aplicar:
                print(f"  - {etiqueta}")
                continue

            url = await asyncio.to_thread(
                image_storage.subir, imagen.data, imagen.filename
            )
            if url is None:
                print(f"  ! {etiqueta}: no se pudo subir, se queda en la base")
                fallidas += 1
                continue

            for fila in usos:
                fila.image_url = url

            if borrar:
                await db.delete(imagen)

            movidas += 1
            print(f"  + {etiqueta} -> {url}")

        if aplicar:
            await db.commit()
            print(f"\nSubidas {movidas}, fallidas {fallidas}.")
            if movidas and not borrar:
                print(
                    "Las filas siguen en `uploaded_images`. Cuando compruebes "
                    "que la tienda se ve bien, vuelve a ejecutarlo con "
                    "--aplicar --borrar para liberar el espacio."
                )

    return 1 if fallidas else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--aplicar",
        action="store_true",
        help="Sube de verdad y reescribe las URLs (sin esto solo enseña el plan)",
    )
    parser.add_argument(
        "--borrar",
        action="store_true",
        help="Borra de la base las imágenes que ya estén en Cloudinary",
    )
    args = parser.parse_args()

    if args.borrar and not args.aplicar:
        print("--borrar solo tiene sentido junto a --aplicar.")
        return 1

    return asyncio.run(migrar(args.aplicar, args.borrar))


if __name__ == "__main__":
    sys.exit(main())
