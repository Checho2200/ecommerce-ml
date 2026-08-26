"""
Completa el catálogo con productos para las categorías que quedaron vacías.

Audio, Redes y Placas Madre existían como categorías pero sin ningún producto,
así que al entrar desde la portada se veía una tienda sin stock.

Es idempotente: si un producto ya existe (mismo nombre), no lo duplica.

Uso:  python -m app.scripts.add_missing_products
"""

import asyncio

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.product import Category, Product

# (slug de categoría, nombre, descripción, precio, stock, imagen)
NEW_PRODUCTS = [
    (
        "audio",
        "Logitech G733 Lightspeed",
        "Audífonos gaming inalámbricos con micrófono desmontable, iluminación RGB "
        "y hasta 29 horas de batería. Diadema de suspensión para uso prolongado.",
        499.00, 12, "/products/audio.webp",
    ),
    (
        "audio",
        "HyperX Cloud II",
        "Audífonos gaming con sonido envolvente 7.1 virtual, almohadillas de "
        "espuma viscoelástica y micrófono con cancelación de ruido.",
        349.00, 15, "/products/audio-2.webp",
    ),
    (
        "redes",
        "TP-Link Archer AX55",
        "Router WiFi 6 de doble banda AX3000. Cuatro antenas de alta ganancia, "
        "OFDMA y MU-MIMO para mantener muchos dispositivos conectados sin caídas.",
        329.00, 18, "/products/redes.webp",
    ),
    (
        "redes",
        "TP-Link TL-SG108 Gigabit",
        "Switch de 8 puertos Gigabit con carcasa metálica. Plug and play, sin "
        "configuración, ideal para ampliar la red de una oficina pequeña.",
        149.00, 25, "/products/redes-2.webp",
    ),
    (
        "placas-madre",
        "ASUS TUF Gaming B550-PLUS",
        "Placa madre ATX socket AM4 para procesadores Ryzen. PCIe 4.0, doble M.2, "
        "disipadores VRM reforzados y red Realtek 2.5 Gb.",
        699.00, 8, "/products/mainboard.webp",
    ),
    (
        "placas-madre",
        "MSI PRO B760M-A WiFi",
        "Placa madre micro-ATX socket LGA1700 para Intel de 12.ª y 13.ª "
        "generación. Soporta DDR5, WiFi 6E y doble ranura M.2.",
        799.00, 6, "/products/chipset.webp",
    ),
]


async def add_products() -> None:
    async with AsyncSessionLocal() as db:
        cats = {c.slug: c for c in (await db.execute(select(Category))).scalars().all()}
        existing = {p.name for p in (await db.execute(select(Product))).scalars().all()}

        created = skipped = 0
        for slug, name, desc, price, stock, image in NEW_PRODUCTS:
            if name in existing:
                print(f"  = ya existe: {name}")
                skipped += 1
                continue
            category = cats.get(slug)
            if category is None:
                print(f"  ! no existe la categoría '{slug}', se omite {name}")
                skipped += 1
                continue

            db.add(
                Product(
                    name=name,
                    description=desc,
                    price=price,
                    stock=stock,
                    image_url=image,
                    category_id=category.id,
                )
            )
            print(f"  + {category.name}: {name}  (S/{price:.2f})")
            created += 1

        await db.commit()

    print(f"\nListo. Creados: {created} | omitidos: {skipped}")


if __name__ == "__main__":
    asyncio.run(add_products())
