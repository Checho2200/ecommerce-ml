"""
Piezas compartidas por las pruebas de la API.

Cada prueba corre contra su propia base SQLite en un archivo temporal, creada y
borrada por la propia prueba. Así ninguna deja rastro en la siguiente y no se
toca la base de desarrollo.

La aplicación no se modifica para poder probarla: se sustituye la dependencia
`get_db` por una sesión contra esa base temporal, que es el punto exacto por
donde la API habla con PostgreSQL en producción.
"""

import os

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Debe quedar fijado antes de importar la aplicación: si el .env del proyecto
# apunta a otra base, las pruebas la usarían.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_sanchez.db")

from app.core.database import Base, get_db  # noqa: E402
from app.core.rate_limit import limiter  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.main import app  # noqa: E402
from app.models.product import Category, Product  # noqa: E402
from app.models.user import User, UserRole  # noqa: E402


@pytest_asyncio.fixture
async def sesion(tmp_path):
    """Base de datos limpia para una sola prueba."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'prueba.db'}")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    fabrica = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with fabrica() as sesion_de_pruebas:
        yield sesion_de_pruebas

    await engine.dispose()


@pytest_asyncio.fixture
async def cliente(sesion):
    """
    Cliente HTTP que habla con la aplicación real, sin levantar un servidor.

    El límite de peticiones queda apagado porque si no, la decena de intentos
    de login que hacen estas pruebas chocaría contra el tope. La prueba que sí
    verifica el tope lo vuelve a encender.
    """
    async def get_db_de_pruebas():
        try:
            yield sesion
            await sesion.commit()
        except Exception:
            await sesion.rollback()
            raise

    app.dependency_overrides[get_db] = get_db_de_pruebas
    limiter.enabled = False

    transporte = ASGITransport(app=app)
    async with AsyncClient(transport=transporte, base_url="http://pruebas") as http:
        yield http

    app.dependency_overrides.clear()
    limiter.enabled = True
    limiter.reset()


# --- Datos de partida ---

CONTRASENA = "clave-de-prueba"


async def crear_usuario(
    sesion,
    email: str = "cliente@ejemplo.com",
    rol: str = UserRole.CLIENTE,
    contrasena: str = CONTRASENA,
) -> User:
    """Inserta un usuario listo para iniciar sesión."""
    usuario = User(
        email=email,
        hashed_password=hash_password(contrasena),
        full_name="Persona de Prueba",
        phone="900000000",
        role=rol,
    )
    sesion.add(usuario)
    await sesion.commit()
    await sesion.refresh(usuario)
    return usuario


async def crear_producto(
    sesion,
    nombre: str = "Teclado mecánico",
    precio: float = 199.0,
    stock: int = 10,
    alto_riesgo: bool = False,
) -> Product:
    """Inserta una categoría y un producto con stock."""
    categoria = Category(
        name="Periféricos" if not alto_riesgo else "Tarjetas de video",
        slug=f"cat-{nombre.lower().replace(' ', '-')}",
        is_high_risk=alto_riesgo,
    )
    sesion.add(categoria)
    await sesion.flush()

    producto = Product(
        name=nombre,
        description="Producto para pruebas",
        price=precio,
        stock=stock,
        category_id=categoria.id,
    )
    sesion.add(producto)
    await sesion.commit()
    await sesion.refresh(producto)
    return producto


async def token_de(cliente: AsyncClient, email: str, contrasena: str = CONTRASENA) -> str:
    """Inicia sesión y devuelve la cabecera Authorization ya armada."""
    respuesta = await cliente.post(
        "/api/v1/auth/login", json={"email": email, "password": contrasena}
    )
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()["access_token"]


async def cabeceras_de(cliente: AsyncClient, email: str, contrasena: str = CONTRASENA) -> dict:
    return {"Authorization": f"Bearer {await token_de(cliente, email, contrasena)}"}
