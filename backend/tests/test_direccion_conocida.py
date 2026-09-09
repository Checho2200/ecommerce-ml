"""
Pruebas de `is_new_shipping_address`, una de las cuatro variables del modelo.

La variable dice si el cliente ya había enviado antes a esa dirección, y de
todas las del modelo es la única que el propio sistema calcula a partir de su
historia. Eso la hace la más fácil de envenenar: si un pedido rechazado dejara
la dirección marcada como conocida, bastaría intentar dos veces la misma compra
para que la segunda puntuara más bajo que la primera. El bloqueo se convertiría
en un trámite.

Desde fuera ese agujero no se ve como un agujero: se ve como que el modelo
decide distinto ante compras iguales, es decir, como si respondiera al azar.
"""

import pytest

from app.models.order import Order, OrderStatus
from app.services.order_service import _es_direccion_nueva

from tests.conftest import crear_usuario

DIRECCION = "Av. Larco 1150, Trujillo"


async def _pedido(sesion, usuario, estado: OrderStatus, direccion: str = DIRECCION):
    orden = Order(
        user_id=usuario.id,
        total_amount=500.0,
        status=estado,
        shipping_address=direccion,
        shipping_city="Trujillo",
    )
    sesion.add(orden)
    await sesion.commit()
    return orden


@pytest.mark.asyncio
async def test_sin_pedidos_previos_la_direccion_es_nueva(sesion):
    usuario = await crear_usuario(sesion)

    assert await _es_direccion_nueva(sesion, usuario.id, DIRECCION) == 1


@pytest.mark.asyncio
async def test_un_pedido_rechazado_no_vuelve_conocida_la_direccion(sesion):
    """
    El caso que motivó el arreglo: reintentar la compra que el modelo acaba de
    bloquear no puede rebajar su propio puntaje.
    """
    usuario = await crear_usuario(sesion)
    await _pedido(sesion, usuario, OrderStatus.REJECTED)

    assert await _es_direccion_nueva(sesion, usuario.id, DIRECCION) == 1


@pytest.mark.asyncio
async def test_un_pedido_que_el_sistema_dejo_vivir_si_la_vuelve_conocida(sesion):
    usuario = await crear_usuario(sesion)
    await _pedido(sesion, usuario, OrderStatus.COMPLETED)

    assert await _es_direccion_nueva(sesion, usuario.id, DIRECCION) == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "estado",
    [OrderStatus.PENDING, OrderStatus.FRAUD_REVIEW, OrderStatus.COMPLETED],
)
async def test_los_estados_que_no_son_un_rechazo_cuentan(sesion, estado):
    usuario = await crear_usuario(sesion)
    await _pedido(sesion, usuario, estado)

    assert await _es_direccion_nueva(sesion, usuario.id, DIRECCION) == 0


@pytest.mark.asyncio
async def test_la_direccion_de_otro_cliente_no_cuenta(sesion):
    """
    La variable es por cliente. Que otra persona haya enviado a esa dirección no
    dice nada de ésta —y si dijera algo, un defraudador podría estrenar cuenta
    reutilizando una dirección ajena que ya constara.
    """
    uno = await crear_usuario(sesion, email="uno@ejemplo.com")
    otro = await crear_usuario(sesion, email="otro@ejemplo.com")
    await _pedido(sesion, uno, OrderStatus.COMPLETED)

    assert await _es_direccion_nueva(sesion, otro.id, DIRECCION) == 1


@pytest.mark.asyncio
async def test_otra_direccion_del_mismo_cliente_sigue_siendo_nueva(sesion):
    usuario = await crear_usuario(sesion)
    await _pedido(sesion, usuario, OrderStatus.COMPLETED)

    assert await _es_direccion_nueva(sesion, usuario.id, "Jr. Pizarro 300, Trujillo") == 1


@pytest.mark.asyncio
async def test_un_rechazo_no_tapa_un_pedido_bueno_a_la_misma_direccion(sesion):
    """
    Basta un pedido no rechazado para que la dirección cuente como conocida,
    aunque después haya habido un bloqueo a la misma dirección.
    """
    usuario = await crear_usuario(sesion)
    await _pedido(sesion, usuario, OrderStatus.COMPLETED)
    await _pedido(sesion, usuario, OrderStatus.REJECTED)

    assert await _es_direccion_nueva(sesion, usuario.id, DIRECCION) == 0
