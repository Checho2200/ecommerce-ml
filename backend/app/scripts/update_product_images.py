"""
Asigna imágenes locales (servidas por el frontend) a productos y categorías.

A diferencia de `app.seed`, este script es idempotente y NO borra nada: solo
ejecuta UPDATE sobre la columna `image_url`. Es seguro correrlo contra la base
de producción cuantas veces haga falta.

Uso:  python -m app.scripts.update_product_images
"""

import asyncio

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.product import Category, Product

# Ruta relativa: la resuelve el frontend (Vercel), no el backend.
PRODUCT_IMAGES: dict[str, str] = {
    "AMD Ryzen 5 5600X": "/products/cpu-ryzen.webp",
    "Intel Core i7-13700K": "/products/cpu-socket.webp",
    "AMD Ryzen 7 7800X3D": "/products/chipset.webp",
    "NVIDIA RTX 4060 Ti 8GB": "/products/gpu-duo.webp",
    "AMD RX 7600 8GB": "/products/gpu-rtx.webp",
    "NVIDIA RTX 4070 Super": "/products/gpu-build.webp",
    "Kingston Fury Beast DDR4 16GB (2x8GB)": "/products/ram.webp",
    "Corsair Vengeance DDR5 32GB (2x16GB)": "/products/ram-rgb.webp",
    "Kingston NV2 1TB NVMe": "/products/storage.webp",
    "Samsung 980 PRO 2TB": "/products/storage-2.webp",
    'LG UltraGear 27" 1440p 165Hz': "/products/monitor.webp",
    "Logitech G502 X PLUS": "/products/mouse.webp",
    "HyperX Alloy Origins Core": "/products/keyboard.webp",
    "Corsair 4000D Airflow": "/products/case.webp",
    "EVGA SuperNOVA 750 G6": "/products/psu-build.webp",
}

CATEGORY_IMAGES: dict[str, str] = {
    "procesadores": "/products/cpu-ryzen.webp",
    "tarjetas-de-video": "/products/gpu-duo.webp",
    "memorias-ram": "/products/ram.webp",
    "almacenamiento": "/products/storage.webp",
    "monitores": "/products/monitor.webp",
    "perifericos": "/products/mouse.webp",
    "cases-y-fuentes": "/products/case.webp",
    "placas-madre": "/products/chipset.webp",
    "audio": "/products/audio.webp",
    "redes": "/products/redes.webp",
}


async def update_images() -> None:
    async with AsyncSessionLocal() as db:
        updated = skipped = 0

        result = await db.execute(select(Product))
        for product in result.scalars().all():
            new_url = PRODUCT_IMAGES.get(product.name)
            if new_url is None:
                print(f"  ? Sin imagen definida para: {product.name}")
                skipped += 1
            elif product.image_url != new_url:
                product.image_url = new_url
                print(f"  + {product.name} -> {new_url}")
                updated += 1

        cat_updated = 0
        result = await db.execute(select(Category))
        for category in result.scalars().all():
            new_url = CATEGORY_IMAGES.get(category.slug)
            if new_url is not None and category.image_url != new_url:
                category.image_url = new_url
                print(f"  + [categoria] {category.name} -> {new_url}")
                cat_updated += 1

        await db.commit()

    print(
        f"\nListo. Productos actualizados: {updated} | sin mapear: {skipped} "
        f"| categorias actualizadas: {cat_updated}"
    )


if __name__ == "__main__":
    asyncio.run(update_images())
