"""
Pruebas de que un producto en oferta se cobra al precio de la oferta.

Esto nació de un fallo que la tienda tuvo en producción: el catálogo enseñaba el
precio rebajado y tachaba el de lista, pero el carrito, el pedido y el cobro
sumaban con `price`. Un producto anunciado a S/ 1 llegaba al carrito a S/ 5.

Una tienda que anuncia un precio y cobra otro más alto no tiene un fallo de
pantalla: tiene un problema con sus clientes. Por eso el precio que se cobra
vive ahora en un solo sitio, `Product.precio_efectivo`, y esto lo sujeta.
"""

from app.models.order import OrderStatus
from app.schemas.order import OrderCreate, OrderItemCreate
from app.services import order_service

from tests.conftest import crear_producto, crear_usuario


async def _comprar(sesion, usuario, producto, unidades=1):
    return await order_service.crear_pedido(
        sesion,
        usuario,
        OrderCreate(
            items=[
                OrderItemCreate(product_id=producto.id, quantity=unidades)
            ],
            shipping_address="Jr. Alfonso Ugarte 493",
            shipping_city="Trujillo",
            checkout_duration_seconds=120,
        ),
    )


async def test_un_producto_en_oferta_se_cobra_a_precio_de_oferta(sesion):
    """El caso exacto que falló: anunciado a S/ 1, cobrado a S/ 5."""
    usuario = await crear_usuario(sesion)
    producto = await crear_producto(sesion, precio=5.0)
    producto.discount_price = 1.0
    await sesion.commit()

    pedido = await _comprar(sesion, usuario, producto)

    assert pedido.orden.total_amount == 1.0


async def test_la_linea_del_pedido_guarda_el_precio_al_que_se_vendio(sesion):
    """
    Y no el de lista.

    Si mañana se retira la oferta, este pedido tiene que seguir contando lo que
    el cliente pagó de verdad: es lo que sostiene el historial de ventas y, de
    paso, el monto que el modelo de fraude evaluó.
    """
    usuario = await crear_usuario(sesion)
    producto = await crear_producto(sesion, precio=5.0)
    producto.discount_price = 1.0
    await sesion.commit()

    pedido = await _comprar(sesion, usuario, producto, unidades=3)

    assert pedido.orden.items[0].unit_price == 1.0
    assert pedido.orden.total_amount == 3.0


async def test_sin_oferta_se_cobra_el_precio_normal(sesion):
    usuario = await crear_usuario(sesion)
    producto = await crear_producto(sesion, precio=199.0)

    pedido = await _comprar(sesion, usuario, producto, unidades=2)

    assert pedido.orden.total_amount == 398.0


async def test_el_modelo_evalua_el_monto_que_se_cobra(sesion):
    """
    El monto es una de las cinco variables del modelo, así que cobrar uno y
    evaluar otro dejaría la decisión apoyada en un dato que nunca existió.
    """
    usuario = await crear_usuario(sesion)
    producto = await crear_producto(sesion, precio=8000.0)
    producto.discount_price = 12.0
    await sesion.commit()

    pedido = await _comprar(sesion, usuario, producto)

    assert pedido.orden.total_amount == 12.0
    # Con doce soles no hay nada sospechoso; con ocho mil lo habría habido.
    assert pedido.orden.status == OrderStatus.PENDING
    assert pedido.evaluacion.decision != "BLOCKED"
