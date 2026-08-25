"""
Configuración de la base de datos con SQLAlchemy async.
Soporta SQLite (desarrollo) y PostgreSQL (producción).
"""

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.core.config import get_settings

settings = get_settings()

# Configuración del engine según el tipo de BD
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    connect_args=connect_args,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Clase base para todos los modelos ORM."""
    pass


async def get_db():
    """Dependency que provee una sesión de BD por request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_tables():
    """Crea todas las tablas si no existen (SQLite y PostgreSQL)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    if settings.DATABASE_URL.startswith("sqlite"):
        # Parche para archivos .db de SQLite creados antes de que estas columnas
        # existieran en el modelo (SQLite no soporta ALTER COLUMN). No aplica a
        # PostgreSQL: ahí create_all ya crea las columnas desde cero.
        import sqlalchemy

        for statement in (
            "ALTER TABLE categories ADD COLUMN image_url VARCHAR(500)",
            "ALTER TABLE products ADD COLUMN discount_price FLOAT",
        ):
            try:
                async with engine.begin() as conn:
                    await conn.execute(sqlalchemy.text(statement))
            except Exception:
                pass  # La columna ya existe, ignorar

