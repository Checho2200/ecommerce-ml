"""
Una compra con la dependencia de base de datos REAL, sin sustituir por nada.

Por qué hace falta una prueba aparte: el resto de las pruebas de la API
reemplazan `get_db` por una única sesión compartida, y eso, sin querer, tapaba
un fallo grave. Al crear una orden, la respuesta leía `item.product.name` sobre
una línea recién insertada; con la sesión compartida el producto ya estaba en
memoria y no hacía falta ir a la base, pero con una sesión nueva por petición
—que es como corre la aplicación de verdad— esa lectura dispara una consulta
perezosa dentro de código síncrono, y SQLAlchemy la corta con MissingGreenlet.

Resultado: el checkout devolvía HTTP 500 en el servidor mientras todas las
pruebas pasaban en verde. Esta prueba cierra ese hueco: monta la aplicación tal
cual, contra una base temporal, y compra.
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.database import Base
from app.core.rate_limit import limiter
from app.core.security import hash_password
from app.main import app
from app.models.product import Category, Product
from app.models.user import User, UserRole
from tests.conftest import CONTRASENA

CORREO = "compra.real@ejemplo.com"


@pytest_asyncio.fixture
async def tienda(tmp_path, monkeypatch):
    """
    Una tienda montada sobre una base temporal, con la aplicación intacta.

    No se toca `app.dependency_overrides`: cada petición abre y cierra su propia
    sesión, igual que en producción.
    """
    motor = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'tienda.db'}")
    fabrica = async_sessionmaker(bind=motor, expire_on_commit=False)

    async with motor.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with fabrica() as sesion:
        categoria = Category(name="Tarjetas de video", slug="gpu", is_high_risk=True)
        sesion.add(categoria)
        await sesion.flush()

        sesion.add_all(
            [
                User(
                    email=CORREO,
                    hashed_password=hash_password(CONTRASENA),
                    full_name="Compradora de Prueba",
                    role=UserRole.CLIENTE,
                ),
                Product(
                    name="Tarjeta de video RTX 4060",
                    description="Producto de prueba",
                    price=1899.0,
                    stock=10,
                    category_id=categoria.id,
                ),
                Product(
                    name="Teclado mecánico",
                    description="Producto de prueba",
                    price=189.0,
                    stock=10,
                    category_id=categoria.id,
                ),
            ]
        )
        await sesion.commit()

    # La aplicación lee estos dos nombres del módulo cada vez que los usa.
    monkeypatch.setattr("app.core.database.engine", motor)
    monkeypatch.setattr("app.core.database.AsyncSessionLocal", fabrica)

    assert not app.dependency_overrides, "esta prueba corre sin sustituciones"
    limiter.enabled = False

    transporte = ASGITransport(app=app)
    async with AsyncClient(transport=transporte, base_url="http://tienda") as http:
        yield http, fabrica

    limiter.enabled = True
    limiter.reset()
    await motor.dispose()


async def _productos(fabrica) -> list[dict]:
    from sqlalchemy import select

    async with fabrica() as sesion:
        resultado = await sesion.execute(select(Product))
        return [{"id": p.id, "nombre": p.name} for p in resultado.scalars().all()]


@pytest.mark.parametrize("cuantos_articulos", [1, 2])
async def test_una_compra_de_verdad_termina_bien(tienda, cuantos_articulos):
    """
    El checkout completo contra la aplicación sin retoques. Antes de arreglarlo,
    esto devolvía 500.
    """
    http, fabrica = tienda
    productos = (await _productos(fabrica))[:cuantos_articulos]

    acceso = await http.post(
        "/api/v1/auth/login", json={"email": CORREO, "password": CONTRASENA}
    )
    assert acceso.status_code == 200, acceso.text
    cabeceras = {"Authorization": f"Bearer {acceso.json()['access_token']}"}

    respuesta = await http.post(
        "/api/v1/orders",
        json={
            "items": [{"product_id": p["id"], "quantity": 1} for p in productos],
            "shipping_address": "Av. España 1234, Trujillo",
            "shipping_city": "Trujillo",
            "checkout_duration_seconds": 240.0,
        },
        headers=cabeceras,
    )

    assert respuesta.status_code == 201, respuesta.text
    orden = respuesta.json()

    # Y la respuesta trae el nombre de cada producto, que es justo lo que
    # obligaba a consultar la base en mitad de la respuesta.
    assert len(orden["items"]) == cuantos_articulos
    nombres_esperados = {p["nombre"] for p in productos}
    assert {item["product_name"] for item in orden["items"]} == nombres_esperados


async def test_el_pedido_creado_se_puede_volver_a_consultar(tienda):
    """La otra mitad: leer la orden después, ya con sus relaciones cargadas."""
    http, fabrica = tienda
    producto = (await _productos(fabrica))[0]

    acceso = await http.post(
        "/api/v1/auth/login", json={"email": CORREO, "password": CONTRASENA}
    )
    cabeceras = {"Authorization": f"Bearer {acceso.json()['access_token']}"}

    creada = await http.post(
        "/api/v1/orders",
        json={
            "items": [{"product_id": producto["id"], "quantity": 1}],
            "shipping_address": "Av. España 1234, Trujillo",
            "shipping_city": "Trujillo",
            "checkout_duration_seconds": 240.0,
        },
        headers=cabeceras,
    )
    assert creada.status_code == 201, creada.text
    orden_id = creada.json()["id"]

    consultada = await http.get(f"/api/v1/orders/{orden_id}", headers=cabeceras)

    assert consultada.status_code == 200, consultada.text
    assert consultada.json()["items"][0]["product_name"] == producto["nombre"]


async def test_mis_pedidos_se_listan_con_los_nombres(tienda):
    http, fabrica = tienda
    producto = (await _productos(fabrica))[0]

    acceso = await http.post(
        "/api/v1/auth/login", json={"email": CORREO, "password": CONTRASENA}
    )
    cabeceras = {"Authorization": f"Bearer {acceso.json()['access_token']}"}

    await http.post(
        "/api/v1/orders",
        json={
            "items": [{"product_id": producto["id"], "quantity": 2}],
            "shipping_address": "Jr. Pizarro 456, Trujillo",
            "shipping_city": "Trujillo",
            "checkout_duration_seconds": 300.0,
        },
        headers=cabeceras,
    )

    listado = await http.get("/api/v1/orders/my-orders", headers=cabeceras)

    assert listado.status_code == 200, listado.text
    cuerpo = listado.json()
    assert cuerpo["total"] == 1
    assert cuerpo["items"][0]["items"][0]["product_name"] == producto["nombre"]
