"""
Aplica las migraciones de Alembic. Se ejecuta en cada despliegue.

    python -m app.scripts.apply_migrations

Por qué hace falta un script y no basta `alembic upgrade head`: la base de
producción se creó en su día con `Base.metadata.create_all()`, así que tiene
todas las tablas pero no la tabla `alembic_version` donde Alembic anota por
dónde va. Lanzarle `upgrade head` a esa base intentaría crear tablas que ya
existen y fallaría el despliegue.

Entonces se mira primero en qué estado está:

- Hay `alembic_version`  ->  `upgrade head`, el caso normal de cada despliegue.
- No hay, pero sí `users` ->  `stamp head`: el esquema ya está puesto, solo se
                              anota la revisión para que los despliegues
                              siguientes sean migraciones de verdad.
- Base vacía             ->  `upgrade head`, que la construye desde cero.
"""

import asyncio
import sys

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from app.core.config import get_settings
from app.core.database import engine

settings = get_settings()


async def _tablas_existentes() -> set:
    """Nombres de las tablas que ya hay en la base."""
    async with engine.connect() as conn:
        return set(await conn.run_sync(lambda c: inspect(c).get_table_names()))


def main() -> int:
    print(f"Revisando el esquema de {settings.DATABASE_URL.split('@')[-1]}")

    try:
        tablas = asyncio.run(_tablas_existentes())
    except Exception as exc:  # noqa: BLE001 - el despliegue debe ver el motivo
        print(f"ERROR: no se pudo conectar a la base de datos: {exc}")
        return 1

    config = Config("alembic.ini")

    if "alembic_version" in tablas:
        print("Alembic ya lleva el control; aplicando migraciones pendientes.")
        command.upgrade(config, "head")
    elif "users" in tablas:
        print(
            "La base tiene el esquema pero no el registro de Alembic "
            "(la creó create_all). Se marca en la revisión actual sin tocar "
            "los datos."
        )
        command.stamp(config, "head")
    else:
        print("Base vacía; se construye el esquema desde las migraciones.")
        command.upgrade(config, "head")

    print("Esquema al día.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
