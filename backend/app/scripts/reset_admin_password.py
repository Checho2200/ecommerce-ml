"""
Cambia la contrasena de un usuario ya existente.

Hace falta porque app/seed.py no sirve para esto: lo primero que hace es un
drop_all, asi que volver a ejecutarlo contra produccion borraria la tienda
entera. Este script solo toca la columna del hash.

Uso:
    ADMIN_EMAIL=admin@sanchez.pe ADMIN_PASSWORD='...' python -m app.scripts.reset_admin_password
"""

import asyncio
import os
import sys

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.user import User


async def reset() -> int:
    email = os.getenv("ADMIN_EMAIL")
    password = os.getenv("ADMIN_PASSWORD")

    if not email or not password:
        print("Faltan ADMIN_EMAIL o ADMIN_PASSWORD en el entorno.")
        return 1

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user is None:
            print(f"No existe ningun usuario con el correo {email}.")
            return 1

        user.hashed_password = hash_password(password)
        await db.commit()

    print(f"Contrasena actualizada para {email}.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(reset()))
