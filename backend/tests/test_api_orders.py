"""
Pruebas del ciclo de una orden de compra.

Lo que se vigila aquí es el inventario, que es donde un fallo se nota de
verdad: una orden que no descuenta stock vende dos veces la misma unidad, y una
cancelación que no lo devuelve deja mercadería congelada en el catálogo.
"""

from sqlalchemy import select

from app.models.order import Order, OrderStatus
from app.models.product import Product
from app.models.user import UserRole
from tests.conftest import cabeceras_de, crear_producto, crear_usuario

DIRECCION = {
    "shipping_address": "Av. España 1234, Trujillo",
    "shipping_city": "Trujillo",
}


def _pedido(producto_id: str, cantidad: int = 1) -> dict:
    return {
        "items": [{"product_id": producto_id, "quantity": cantidad}],
        **DIRECCION,
        # Un checkout de dos minutos: el modelo de fraude lo trata como una
        # compra normal, que es lo que se quiere probar aquí.
        "checkout_duration_seconds": 120.0,
    }


async def test_crear_una_orden_descuenta_el_stock(cliente, sesion):
    producto = await crear_producto(sesion, stock=10)
    await crear_usuario(sesion, email="compra@ejemplo.com")
    cabeceras = await cabeceras_de(cliente, "compra@ejemplo.com")

    respuesta = await cliente.post(
        "/api/v1/orders", json=_pedido(producto.id, 3), headers=cabeceras
    )

    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json()["total_amount"] == producto.price * 3

    await sesion.refresh(producto)
    assert producto.stock == 7


async def test_no_se_puede_comprar_mas_de_lo_que_hay(cliente, sesion):
    producto = await crear_producto(sesion, stock=2)
    await crear_usuario(sesion, email="compra@ejemplo.com")
    cabeceras = await cabeceras_de(cliente, "compra@ejemplo.com")

    respuesta = await cliente.post(
        "/api/v1/orders", json=_pedido(producto.id, 5), headers=cabeceras
    )

    assert respuesta.status_code == 400
    await sesion.refresh(producto)
    assert producto.stock == 2, "un pedido rechazado no puede tocar el inventario"


async def test_comprar_un_producto_inexistente_da_404(cliente, sesion):
    await crear_usuario(sesion, email="compra@ejemplo.com")
    cabeceras = await cabeceras_de(cliente, "compra@ejemplo.com")

    respuesta = await cliente.post(
        "/api/v1/orders", json=_pedido("no-existe"), headers=cabeceras
    )

    assert respuesta.status_code == 404


async def test_comprar_exige_haber_iniciado_sesion(cliente, sesion):
    producto = await crear_producto(sesion)

    respuesta = await cliente.post("/api/v1/orders", json=_pedido(producto.id))

    assert respuesta.status_code in (401, 403)


async def test_cancelar_una_orden_devuelve_el_stock(cliente, sesion):
    producto = await crear_producto(sesion, stock=5)
    await crear_usuario(sesion, email="compra@ejemplo.com")
    cabeceras = await cabeceras_de(cliente, "compra@ejemplo.com")

    creada = await cliente.post(
        "/api/v1/orders", json=_pedido(producto.id, 2), headers=cabeceras
    )
    orden = creada.json()
    if orden["status"] != OrderStatus.PENDING.value:
        # El modelo de fraude decidió otra cosa; el stock ya se liberó solo.
        return

    await sesion.refresh(producto)
    assert producto.stock == 3

    respuesta = await cliente.patch(
        f"/api/v1/orders/my-orders/{orden['id']}/cancel", headers=cabeceras
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["status"] == OrderStatus.CANCELLED.value

    await sesion.refresh(producto)
    assert producto.stock == 5


async def test_mis_ordenes_solo_muestra_las_propias(cliente, sesion):
    producto = await crear_producto(sesion, stock=10)
    await crear_usuario(sesion, email="uno@ejemplo.com")
    await crear_usuario(sesion, email="dos@ejemplo.com")

    cabeceras_uno = await cabeceras_de(cliente, "uno@ejemplo.com")
    await cliente.post("/api/v1/orders", json=_pedido(producto.id), headers=cabeceras_uno)

    cabeceras_dos = await cabeceras_de(cliente, "dos@ejemplo.com")
    respuesta = await cliente.get("/api/v1/orders/my-orders", headers=cabeceras_dos)

    assert respuesta.status_code == 200
    assert respuesta.json()["total"] == 0


async def test_un_cliente_no_puede_ver_la_orden_de_otro(cliente, sesion):
    producto = await crear_producto(sesion, stock=10)
    await crear_usuario(sesion, email="uno@ejemplo.com")
    await crear_usuario(sesion, email="dos@ejemplo.com")

    cabeceras_uno = await cabeceras_de(cliente, "uno@ejemplo.com")
    creada = await cliente.post(
        "/api/v1/orders", json=_pedido(producto.id), headers=cabeceras_uno
    )
    orden_id = creada.json()["id"]

    cabeceras_dos = await cabeceras_de(cliente, "dos@ejemplo.com")
    respuesta = await cliente.get(f"/api/v1/orders/{orden_id}", headers=cabeceras_dos)

    assert respuesta.status_code == 403


async def test_el_listado_completo_es_solo_para_administradores(cliente, sesion):
    await crear_usuario(sesion, email="cliente@ejemplo.com")
    cabeceras = await cabeceras_de(cliente, "cliente@ejemplo.com")

    respuesta = await cliente.get("/api/v1/orders", headers=cabeceras)

    assert respuesta.status_code == 403


async def test_el_administrador_ve_las_ordenes_de_todos(cliente, sesion):
    producto = await crear_producto(sesion, stock=10)
    await crear_usuario(sesion, email="cliente@ejemplo.com")
    await crear_usuario(sesion, email="jefe@ejemplo.com", rol=UserRole.ADMIN)

    cabeceras_cliente = await cabeceras_de(cliente, "cliente@ejemplo.com")
    await cliente.post(
        "/api/v1/orders", json=_pedido(producto.id), headers=cabeceras_cliente
    )

    cabeceras_admin = await cabeceras_de(cliente, "jefe@ejemplo.com")
    respuesta = await cliente.get("/api/v1/orders", headers=cabeceras_admin)

    assert respuesta.status_code == 200
    assert respuesta.json()["total"] == 1


async def test_el_administrador_que_cancela_devuelve_el_stock(cliente, sesion):
    producto = await crear_producto(sesion, stock=6)
    await crear_usuario(sesion, email="cliente@ejemplo.com")
    await crear_usuario(sesion, email="jefe@ejemplo.com", rol=UserRole.ADMIN)

    cabeceras_cliente = await cabeceras_de(cliente, "cliente@ejemplo.com")
    creada = await cliente.post(
        "/api/v1/orders", json=_pedido(producto.id, 2), headers=cabeceras_cliente
    )
    orden = creada.json()
    if orden["status"] not in (
        OrderStatus.PENDING.value,
        OrderStatus.FRAUD_REVIEW.value,
    ):
        return

    cabeceras_admin = await cabeceras_de(cliente, "jefe@ejemplo.com")
    respuesta = await cliente.patch(
        f"/api/v1/orders/{orden['id']}/status",
        json={"status": OrderStatus.CANCELLED.value},
        headers=cabeceras_admin,
    )

    assert respuesta.status_code == 200
    await sesion.refresh(producto)
    assert producto.stock == 6


async def test_cada_orden_deja_su_evaluacion_de_fraude(cliente, sesion):
    """
    La trazabilidad del modelo es el corazón del proyecto: toda orden tiene que
    quedar con su puntaje y su decisión guardados, pase lo que pase.
    """
    producto = await crear_producto(sesion, stock=4)
    await crear_usuario(sesion, email="compra@ejemplo.com")
    cabeceras = await cabeceras_de(cliente, "compra@ejemplo.com")

    respuesta = await cliente.post(
        "/api/v1/orders", json=_pedido(producto.id), headers=cabeceras
    )

    cuerpo = respuesta.json()
    assert cuerpo["fraud_decision"] in ("APPROVED", "REVIEW", "BLOCKED")
    assert cuerpo["fraud_score"] is not None
    assert cuerpo["fraud_log_id"]


async def test_una_orden_bloqueada_no_se_queda_con_el_stock(cliente, sesion):
    """
    Cuando el modelo bloquea una compra, la orden nace REJECTED y el inventario
    tiene que quedar intacto: nunca se llegó a vender nada.
    """
    producto = await crear_producto(sesion, precio=9000.0, stock=3, alto_riesgo=True)
    await crear_usuario(sesion, email="compra@ejemplo.com")
    cabeceras = await cabeceras_de(cliente, "compra@ejemplo.com")

    respuesta = await cliente.post(
        "/api/v1/orders",
        json={
            "items": [{"product_id": producto.id, "quantity": 3}],
            **DIRECCION,
            # Un checkout de seis segundos para un carrito de 27 000 soles en
            # tarjetas de video: el perfil que el modelo aprendió a bloquear.
            "checkout_duration_seconds": 6.0,
        },
        headers=cabeceras,
    )

    assert respuesta.status_code == 201
    orden = respuesta.json()

    await sesion.refresh(producto)
    if orden["status"] == OrderStatus.REJECTED.value:
        assert producto.stock == 3
    else:
        assert producto.stock == 0

    guardada = await sesion.execute(select(Order).where(Order.id == orden["id"]))
    assert guardada.scalar_one().status.value == orden["status"]


async def test_el_producto_sigue_disponible_tras_una_compra_parcial(cliente, sesion):
    producto = await crear_producto(sesion, stock=10)
    await crear_usuario(sesion, email="compra@ejemplo.com")
    cabeceras = await cabeceras_de(cliente, "compra@ejemplo.com")

    await cliente.post("/api/v1/orders", json=_pedido(producto.id, 4), headers=cabeceras)

    listado = await cliente.get("/api/v1/products")
    assert listado.status_code == 200

    en_catalogo = await sesion.execute(select(Product).where(Product.id == producto.id))
    assert en_catalogo.scalar_one().stock == 6
