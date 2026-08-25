"""
Script de inicialización de datos de prueba.
Crea un usuario admin, categorías de ejemplo, productos de muestra, órdenes y reseñas.
Ejecutar: python -m app.seed
"""

import asyncio
from app.core.database import AsyncSessionLocal, create_tables, engine
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.models.product import Category, Product
from app.models.order import Order, OrderItem, OrderStatus
from app.models.review import ProductReview

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
            email="admin@sanchez.pe",
            hashed_password=hash_password("Admin123!"),
            full_name="Administrador Sanchez",
            phone="944123456",
            role=UserRole.ADMIN,
        )
        db.add(admin)

        # ===== CLIENTE DE PRUEBA =====
        cliente = User(
            email="cliente@test.com",
            hashed_password=hash_password("Cliente123!"),
            full_name="Juan Pérez López",
            phone="976543210",
            role=UserRole.CLIENTE,
        )
        db.add(cliente)

        # ===== CATEGORÍAS =====
        categories = [
            Category(name="Procesadores", slug="procesadores", is_high_risk=True),
            Category(name="Tarjetas de Video", slug="tarjetas-de-video", is_high_risk=True),
            Category(name="Memorias RAM", slug="memorias-ram", is_high_risk=False),
            Category(name="Almacenamiento", slug="almacenamiento", is_high_risk=False),
            Category(name="Monitores", slug="monitores", is_high_risk=True),
            Category(name="Periféricos", slug="perifericos", is_high_risk=False),
            Category(name="Cases y Fuentes", slug="cases-y-fuentes", is_high_risk=False),
            Category(name="Placas Madre", slug="placas-madre", is_high_risk=True),
            Category(name="Audio", slug="audio", is_high_risk=False),
            Category(name="Redes", slug="redes", is_high_risk=False),
        ]
        for cat in categories:
            db.add(cat)

        await db.flush()

        # ===== PRODUCTOS =====
        products = [
            # Procesadores (high risk)
            Product(name="AMD Ryzen 5 5600X", description="Procesador 6 núcleos, 12 hilos, 3.7GHz base / 4.6GHz boost. Ideal para gaming y productividad.", price=649.00, stock=15, category_id=1, image_url="https://placehold.co/400x400?text=Ryzen+5+5600X"),
            Product(name="Intel Core i7-13700K", description="Procesador de 16 núcleos (8P+8E), 24 hilos, hasta 5.4GHz. Potencia para multitarea extrema.", price=1299.00, stock=8, category_id=1, image_url="https://placehold.co/400x400?text=i7-13700K"),
            Product(name="AMD Ryzen 7 7800X3D", description="Procesador gaming con V-Cache 3D, 8 núcleos, 16 hilos. El mejor para juegos.", price=1599.00, stock=5, category_id=1, image_url="https://placehold.co/400x400?text=Ryzen+7+7800X3D"),

            # Tarjetas de Video (high risk)
            Product(name="NVIDIA RTX 4060 Ti 8GB", description="GPU gaming con DLSS 3, Ray Tracing. 8GB GDDR6. Rendimiento 1080p/1440p.", price=1899.00, stock=10, category_id=2, image_url="https://placehold.co/400x400?text=RTX+4060+Ti"),
            Product(name="AMD RX 7600 8GB", description="GPU económica para gaming 1080p. 8GB GDDR6, arquitectura RDNA 3.", price=1099.00, stock=12, category_id=2, image_url="https://placehold.co/400x400?text=RX+7600"),
            Product(name="NVIDIA RTX 4070 Super", description="GPU de gama alta. 12GB GDDR6X. Excelente para 1440p y ray tracing.", price=2799.00, stock=4, category_id=2, image_url="https://placehold.co/400x400?text=RTX+4070+Super"),

            # Memorias RAM
            Product(name="Kingston Fury Beast DDR4 16GB (2x8GB)", description="Kit de memoria DDR4 3200MHz, CL16. Ideal para gaming y multitarea.", price=189.00, stock=30, category_id=3, image_url="https://placehold.co/400x400?text=Kingston+16GB"),
            Product(name="Corsair Vengeance DDR5 32GB (2x16GB)", description="Kit DDR5 5600MHz, CL36. Para plataformas de última generación.", price=449.00, stock=15, category_id=3, image_url="https://placehold.co/400x400?text=Corsair+32GB"),

            # Almacenamiento
            Product(name="Kingston NV2 1TB NVMe", description="SSD M.2 NVMe, lectura hasta 3500MB/s. Almacenamiento rápido y confiable.", price=189.00, stock=25, category_id=4, image_url="https://placehold.co/400x400?text=Kingston+1TB"),
            Product(name="Samsung 980 PRO 2TB", description="SSD PCIe 4.0 NVMe, hasta 7000MB/s. Para profesionales y gamers exigentes.", price=649.00, stock=8, category_id=4, image_url="https://placehold.co/400x400?text=Samsung+2TB"),

            # Monitores (high risk)
            Product(name="LG UltraGear 27\" 1440p 165Hz", description="Monitor gaming IPS, 1ms, HDR10, FreeSync Premium. Colores vibrantes.", price=1199.00, stock=7, category_id=5, image_url="https://placehold.co/400x400?text=LG+27+165Hz"),

            # Periféricos
            Product(name="Logitech G502 X PLUS", description="Mouse gaming inalámbrico, sensor HERO 25K, RGB, 13 botones programables.", price=349.00, stock=20, category_id=6, image_url="https://placehold.co/400x400?text=G502+X+PLUS"),
            Product(name="HyperX Alloy Origins Core", description="Teclado mecánico TKL, switches HyperX Red, retroiluminación RGB.", price=279.00, stock=18, category_id=6, image_url="https://placehold.co/400x400?text=HyperX+TKL"),

            # Cases y Fuentes
            Product(name="Corsair 4000D Airflow", description="Case ATX con flujo de aire optimizado, panel de vidrio templado, incluye 2 ventiladores.", price=329.00, stock=12, category_id=7, image_url="https://placehold.co/400x400?text=4000D+Airflow"),
            Product(name="EVGA SuperNOVA 750 G6", description="Fuente 750W 80+ Gold, full modular. Protecciones completas, silenciosa.", price=399.00, stock=10, category_id=7, image_url="https://placehold.co/400x400?text=EVGA+750W"),
        ]
        for product in products:
            db.add(product)

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
        print(f"   Admin: admin@sanchez.pe / Admin123!")
        print(f"   Cliente: cliente@test.com / Cliente123!")
        print(f"   Categorías: {len(categories)}")
        print(f"   Productos: {len(products)}")


if __name__ == "__main__":
    asyncio.run(seed())
