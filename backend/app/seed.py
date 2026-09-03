"""
Script de inicialización de datos de prueba.
Crea un usuario admin, categorías de ejemplo, productos de muestra, órdenes y reseñas.
Ejecutar: python -m app.seed
"""

import asyncio
import os

from app.core.database import AsyncSessionLocal, create_tables, engine
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.models.product import Category, Product
from app.taxonomia import SUBCATEGORIAS, subcategoria_para
from app.models.order import Order, OrderItem, OrderStatus
from app.models.review import ProductReview

# Las credenciales salen del entorno: este repositorio es publico y antes
# estaban escritas aqui, asi que cualquiera podia entrar al panel de
# administracion de la tienda desplegada. Los valores por defecto son solo
# para desarrollo local.
ADMIN_EMAIL = os.getenv("SEED_ADMIN_EMAIL", "admin@local.test")
ADMIN_PASSWORD = os.getenv("SEED_ADMIN_PASSWORD", "cambiame-en-produccion")
CLIENTE_EMAIL = os.getenv("SEED_CLIENTE_EMAIL", "cliente@local.test")
CLIENTE_PASSWORD = os.getenv("SEED_CLIENTE_PASSWORD", "cambiame-en-produccion")


async def seed():
    """Pobla la base de datos con datos iniciales."""
    # Drop all and recreate to ensure clean state
    async with engine.begin() as conn:
        from app.core.database import Base
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        # ===== ADMIN USER =====
        admin = User(
            email=ADMIN_EMAIL,
            hashed_password=hash_password(ADMIN_PASSWORD),
            full_name="Administrador Sanchez",
            phone="944123456",
            role=UserRole.ADMIN,
        )
        db.add(admin)

        # ===== CLIENTE DE PRUEBA =====
        cliente = User(
            email=CLIENTE_EMAIL,
            hashed_password=hash_password(CLIENTE_PASSWORD),
            full_name="Juan Pérez López",
            phone="976543210",
            role=UserRole.CLIENTE,
        )
        db.add(cliente)

        # ===== CATEGORÍAS (raíces + subcategorías) =====
        # (nombre, slug, alto_riesgo, imagen)
        raices = [
            ("Procesadores", "procesadores", True, "/products/cpu-ryzen.webp"),
            ("Tarjetas de Video", "tarjetas-de-video", True, "/products/gpu-duo.webp"),
            ("Memorias RAM", "memorias-ram", False, "/products/ram.webp"),
            ("Almacenamiento", "almacenamiento", False, "/products/storage.webp"),
            ("Monitores", "monitores", True, "/products/monitor.webp"),
            ("Periféricos", "perifericos", False, "/products/mouse.webp"),
            ("Cases y Fuentes", "cases-y-fuentes", False, "/products/case.webp"),
            ("Placas Madre", "placas-madre", True, "/products/chipset.webp"),
            ("Audio", "audio", False, "/products/audio.webp"),
            ("Redes", "redes", False, "/products/redes.webp"),
        ]

        por_slug: dict[str, Category] = {}
        for nombre, slug, alto_riesgo, imagen in raices:
            cat = Category(name=nombre, slug=slug, is_high_risk=alto_riesgo, image_url=imagen)
            db.add(cat)
            por_slug[slug] = cat
        await db.flush()

        # Las subcategorías heredan la marca de alto riesgo de su raíz: si los
        # procesadores importan para el fraude, sus líneas también.
        for raiz_slug, hijas in SUBCATEGORIAS.items():
            raiz = por_slug[raiz_slug]
            for nombre_hija, slug_hija, _claves in hijas:
                hija = Category(
                    name=nombre_hija,
                    slug=slug_hija,
                    is_high_risk=raiz.is_high_risk,
                    parent_id=raiz.id,
                    image_url=raiz.image_url,
                )
                db.add(hija)
                por_slug[slug_hija] = hija
        await db.flush()

        # ===== PRODUCTOS =====
        # (slug_raíz, nombre, descripción, precio, stock, imagen). Cada producto
        # se coloca en la subcategoría que le corresponda por su texto; si
        # ninguna coincide, se queda en la raíz.
        catalogo = [
            ("procesadores", "AMD Ryzen 5 5600X", "Procesador 6 núcleos, 12 hilos, 3.7GHz base / 4.6GHz boost. Ideal para gaming y productividad.", 649.00, 15, "/products/cpu-ryzen.webp"),
            ("procesadores", "Intel Core i7-13700K", "Procesador de 16 núcleos (8P+8E), 24 hilos, hasta 5.4GHz. Potencia para multitarea extrema.", 1299.00, 8, "/products/cpu-socket.webp"),
            ("procesadores", "AMD Ryzen 7 7800X3D", "Procesador gaming con V-Cache 3D, 8 núcleos, 16 hilos. El mejor para juegos.", 1599.00, 5, "/products/chipset.webp"),

            ("tarjetas-de-video", "NVIDIA RTX 4060 Ti 8GB", "GPU gaming con DLSS 3, Ray Tracing. 8GB GDDR6. Rendimiento 1080p/1440p.", 1899.00, 10, "/products/gpu-duo.webp"),
            ("tarjetas-de-video", "AMD RX 7600 8GB", "GPU económica para gaming 1080p. 8GB GDDR6, arquitectura RDNA 3.", 1099.00, 12, "/products/gpu-rtx.webp"),
            ("tarjetas-de-video", "NVIDIA RTX 4070 Super", "GPU de gama alta. 12GB GDDR6X. Excelente para 1440p y ray tracing.", 2799.00, 4, "/products/gpu-build.webp"),

            ("memorias-ram", "Kingston Fury Beast DDR4 16GB (2x8GB)", "Kit de memoria DDR4 3200MHz, CL16. Ideal para gaming y multitarea.", 189.00, 30, "/products/ram.webp"),
            ("memorias-ram", "Corsair Vengeance DDR5 32GB (2x16GB)", "Kit DDR5 5600MHz, CL36. Para plataformas de última generación.", 449.00, 15, "/products/ram-rgb.webp"),

            ("almacenamiento", "Kingston NV2 1TB NVMe", "SSD M.2 NVMe, lectura hasta 3500MB/s. Almacenamiento rápido y confiable.", 189.00, 25, "/products/storage.webp"),
            ("almacenamiento", "Samsung 980 PRO 2TB", "SSD PCIe 4.0 NVMe, hasta 7000MB/s. Para profesionales y gamers exigentes.", 649.00, 8, "/products/storage-2.webp"),

            ("monitores", "LG UltraGear 27\" 1440p 165Hz", "Monitor gaming IPS, 1ms, HDR10, FreeSync Premium. Colores vibrantes.", 1199.00, 7, "/products/monitor.webp"),

            ("perifericos", "Logitech G502 X PLUS", "Mouse gaming inalámbrico, sensor HERO 25K, RGB, 13 botones programables.", 349.00, 20, "/products/mouse.webp"),
            ("perifericos", "HyperX Alloy Origins Core", "Teclado mecánico TKL, switches HyperX Red, retroiluminación RGB.", 279.00, 18, "/products/keyboard.webp"),

            ("cases-y-fuentes", "Corsair 4000D Airflow", "Case ATX con flujo de aire optimizado, panel de vidrio templado, incluye 2 ventiladores.", 329.00, 12, "/products/case.webp"),
            ("cases-y-fuentes", "EVGA SuperNOVA 750 G6", "Fuente 750W 80+ Gold, full modular. Protecciones completas, silenciosa.", 399.00, 10, "/products/psu-build.webp"),

            ("placas-madre", "ASUS TUF Gaming B550-PLUS", "Placa madre ATX socket AM4 para procesadores Ryzen. PCIe 4.0, doble M.2, disipadores VRM reforzados y red Realtek 2.5 Gb.", 699.00, 8, "/products/mainboard.webp"),
            ("placas-madre", "MSI PRO B760M-A WiFi", "Placa madre micro-ATX socket LGA1700 para Intel de 12.a y 13.a generacion. Soporta DDR5, WiFi 6E y doble ranura M.2.", 799.00, 6, "/products/chipset.webp"),

            ("audio", "Logitech G733 Lightspeed", "Audifonos gaming inalambricos con microfono desmontable, iluminacion RGB y hasta 29 horas de bateria.", 499.00, 12, "/products/audio.webp"),
            ("audio", "HyperX Cloud II", "Audifonos gaming con sonido envolvente 7.1 virtual, almohadillas de espuma viscoelastica y microfono con cancelacion de ruido.", 349.00, 15, "/products/audio-2.webp"),

            ("redes", "TP-Link Archer AX55", "Router WiFi 6 de doble banda AX3000. Cuatro antenas de alta ganancia, OFDMA y MU-MIMO.", 329.00, 18, "/products/redes.webp"),
            ("redes", "TP-Link TL-SG108 Gigabit", "Switch de 8 puertos Gigabit con carcasa metalica. Plug and play, ideal para ampliar la red de una oficina pequena.", 149.00, 25, "/products/redes-2.webp"),
        ]

        products = []
        for raiz_slug, nombre, descripcion, precio, stock, imagen in catalogo:
            slug_hija = subcategoria_para(f"{nombre} {descripcion}", SUBCATEGORIAS.get(raiz_slug, []))
            destino = por_slug.get(slug_hija) if slug_hija else None
            destino = destino or por_slug[raiz_slug]
            producto = Product(
                name=nombre,
                description=descripcion,
                price=precio,
                stock=stock,
                category_id=destino.id,
                image_url=imagen,
            )
            db.add(producto)
            products.append(producto)

        await db.flush()

        # ===== ORDER FOR REVIEWS =====
        order = Order(
            user_id=cliente.id,
            total_amount=649.00,
            status=OrderStatus.COMPLETED,
            shipping_address="Calle Falsa 123",
            shipping_city="Trujillo"
        )
        db.add(order)
        await db.flush()

        order_item = OrderItem(
            order_id=order.id,
            product_id=products[0].id, # AMD Ryzen 5 5600X
            quantity=1,
            unit_price=649.00
        )
        db.add(order_item)
        await db.flush()

        # ===== REVIEWS =====
        review = ProductReview(
            user_id=cliente.id,
            product_id=products[0].id,
            rating=5,
            comment="¡Excelente procesador! Lo instalé y corre todo a la perfección."
        )
        db.add(review)

        await db.commit()
        print("✅ Base de datos poblada exitosamente con reviews!")
        print(f"   Admin: {ADMIN_EMAIL} (contrasena tomada del entorno)")
        print(f"   Cliente: {CLIENTE_EMAIL} (contrasena tomada del entorno)")
        print(f"   Categorías: {len(por_slug)} (raíces + subcategorías)")
        print(f"   Productos: {len(products)}")


if __name__ == "__main__":
    asyncio.run(seed())
