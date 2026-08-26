"""
Agrega a `fraud_logs` las columnas `risk_level` y `explanation`.

El proyecto crea las tablas con `Base.metadata.create_all`, que solo crea
tablas nuevas: no altera las que ya existen. Como estas dos columnas se
añadieron al modelo después de que la base estuviera creada, hay que agregarlas
a mano una vez.

Es idempotente (`ADD COLUMN IF NOT EXISTS`), así que se puede repetir sin
riesgo.

Uso:  python -m app.scripts.migrate_fraud_log_columns
"""

import asyncio

import sqlalchemy

from app.core.database import engine

STATEMENTS = [
    "ALTER TABLE fraud_logs ADD COLUMN IF NOT EXISTS risk_level VARCHAR(10)",
    "ALTER TABLE fraud_logs ADD COLUMN IF NOT EXISTS explanation TEXT",
]


async def migrate() -> None:
    async with engine.begin() as conn:
        for statement in STATEMENTS:
            await conn.execute(sqlalchemy.text(statement))
            print(f"  OK  {statement}")

        cols = await conn.run_sync(
            lambda sync_conn: [
                c["name"] for c in sqlalchemy.inspect(sync_conn).get_columns("fraud_logs")
            ]
        )
    await engine.dispose()
    print(f"\nColumnas actuales de fraud_logs: {', '.join(cols)}")


if __name__ == "__main__":
    asyncio.run(migrate())
