"""
Cancela las ordenes que quedaron en PENDING y nunca se pagaron.

Una orden descuenta stock en cuanto se crea. Si el cliente abandona el checkout
de MercadoPago, la orden se queda en PENDING y ese inventario no vuelve nunca:
la tienda acaba mostrando productos agotados que en realidad estan en almacen.
Este script cierra esas ordenes y devuelve las unidades.

Uso (por defecto caducan a las 24 horas):
    python -m app.scripts.expire_pending_orders
    ORDER_EXPIRY_HOURS=6 python -m app.scripts.expire_pending_orders
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.order import Order, OrderStatus
from app.models.product import Product


async def expire() -> int:
    horas = float(os.getenv("ORDER_EXPIRY_HOURS", "24"))
    limite = datetime.now(timezone.utc) - timedelta(hours=horas)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Order).where(
                Order.status == OrderStatus.PENDING,
                Order.created_at < limite,
            )
        )
        ordenes = result.scalars().all()

        if not ordenes:
            print(f"No hay ordenes PENDING con mas de {horas:g} horas.")
            return 0

        for orden in ordenes:
            for item in orden.items:
                producto = await db.get(Product, item.product_id)
                if producto:
                    producto.stock += item.quantity
            orden.status = OrderStatus.CANCELLED
            print(f"Cancelada {orden.id} (creada el {orden.created_at:%Y-%m-%d %H:%M}).")

        await db.commit()

    print(f"{len(ordenes)} orden(es) caducadas y stock devuelto.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(expire()))
