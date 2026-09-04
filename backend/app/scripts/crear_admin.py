"""
Crea un usuario administrador, o promueve a admin uno que ya exista.

A diferencia de `app/seed.py` —que hace un drop_all y borraría la tienda—, este
script solo toca (o agrega) una fila de usuarios, así que es seguro correrlo
contra producción. Es idempotente: si el correo ya existe, lo deja como admin y
le fija la contraseña indicada; si no existe, lo crea.

Las credenciales salen del entorno, nunca escritas en el código:

    ADMIN_EMAIL=jeffersanchez@sanchez.pe \
    ADMIN_PASSWORD='una-clave-larga' \
    ADMIN_NAME='Jefferson Sanchez' \
    python -m app.scripts.crear_admin

En PowerShell:

    $env:ADMIN_EMAIL="jeffersanchez@sanchez.pe"
    $env:ADMIN_PASSWORD="una-clave-larga"
    $env:ADMIN_NAME="Jefferson Sanchez"
    python -m app.scripts.crear_admin
"""

import asyncio
import os
import sys

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.user import User, UserRole


async def crear() -> int:
    email = os.getenv("ADMIN_EMAIL")
    password = os.getenv("ADMIN_PASSWORD")
    nombre = os.getenv("ADMIN_NAME") or (email.split("@")[0] if email else "")

    if not email or not password:
        print("Faltan ADMIN_EMAIL o ADMIN_PASSWORD en el entorno.")
        return 1

    async with AsyncSessionLocal() as db:
        existente = (
            await db.execute(select(User).where(User.email == email))
        ).scalar_one_or_none()

        if existente is not None:
            existente.role = UserRole.ADMIN
            existente.is_active = True
            existente.hashed_password = hash_password(password)
            await db.commit()
            print(f"El usuario {email} ya existía; ahora es admin y su contraseña quedó actualizada.")
            return 0

        db.add(
            User(
                email=email,
                hashed_password=hash_password(password),
                full_name=nombre,
                role=UserRole.ADMIN,
            )
        )
        await db.commit()
        print(f"Usuario administrador creado: {email}")
        return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(crear()))
