"""
Pruebas del cobro con Niubiz de punta a punta.

La diferencia de fondo con MercadoPago es que aquí no hay webhook: la respuesta
a la autorización es la confirmación, y llega dentro de la misma petición que la
pide. Eso quita el fallo que deja un pedido pendiente aunque la tarjeta ya se
haya cobrado, pero trae uno propio que hay que sujetar.

La dirección de retorno es pública —la llama el navegador del comprador, sin
sesión— así que cualquiera puede mandarle lo que quiera. Lo que impide que eso
haga daño es una distinción: que Niubiz rechace una tarjeta cancela el pedido,
pero que Niubiz no conteste no lo toca. Sin esa distinción, mandar basura a esa
dirección con el identificador de un pedido ajeno lo cancelaría.
"""

from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.services import order_service
from app.services.niubiz_service import ErrorDeNiubiz, niubiz_service

from tests.conftest import crear_producto, crear_usuario, token_de


RESPUESTA_APROBADA = {
    "dataMap": {
        "ACTION_CODE": "000",
        "ACTION_DESCRIPTION": "Aprobado y registrado exitosamente",
        "CARD": "455687******8232",
        "BRAND": "visa",
        "TRANSACTION_ID": "776655",
    }
}


async def _pedido_esperando_pago(sesion, usuario, producto, unidades: int = 1):
    """Un pedido creado y pendiente, con su stock ya reservado."""
    orden = Order(
        user_id=usuario.id,
        total_amount=producto.price * unidades,
        status=OrderStatus.PENDING,
        shipping_address="Jr. Alfonso Ugarte 493",
        shipping_city="Trujillo",
        purchase_number="000000001234",
    )
    sesion.add(orden)
    await sesion.flush()
    sesion.add(
        OrderItem(
            order_id=orden.id,
            product_id=producto.id,
            quantity=unidades,
            unit_price=producto.price,
        )
    )
    producto.stock -= unidades
    await sesion.commit()
    await sesion.refresh(orden)
    return orden


async def _stock_de(sesion, producto_id: str) -> int:
    return (await sesion.get(Product, producto_id)).stock


# ── El cobro sale bien ───────────────────────────────────────────────────────
async def test_un_pago_aprobado_completa_el_pedido(sesion, monkeypatch):
    usuario = await crear_usuario(sesion)
    producto = await crear_producto(sesion)
    orden = await _pedido_esperando_pago(sesion, usuario, producto)

    async def autorizar_falso(**_):
        return RESPUESTA_APROBADA

    monkeypatch.setattr(niubiz_service, "autorizar", autorizar_falso)

    resultado = await order_service.confirmar_pago_de_niubiz(sesion, orden.id, "tok")

    assert resultado.estado == "completada"
    await sesion.refresh(orden)
    assert orden.status == OrderStatus.COMPLETED
    assert orden.paid_at is not None


async def test_el_cobro_queda_apuntado_con_su_pasarela_y_su_tarjeta(sesion, monkeypatch):
    """
    Ante un contracargo hay que poder decir qué pago fue y en qué panel está.

    Ahora hay dos paneles donde mirar, así que el nombre de la pasarela no es
    un adorno: sin él, un identificador de pago suelto no lleva a ninguna
    parte.
    """
    usuario = await crear_usuario(sesion)
    producto = await crear_producto(sesion)
    orden = await _pedido_esperando_pago(sesion, usuario, producto)

    async def autorizar_falso(**_):
        return RESPUESTA_APROBADA

    monkeypatch.setattr(niubiz_service, "autorizar", autorizar_falso)
    await order_service.confirmar_pago_de_niubiz(sesion, orden.id, "tok")

    await sesion.refresh(orden)
    assert orden.payment_gateway == "niubiz"
    assert orden.payment_id == "776655"
    assert orden.card_last_four == "8232"


# ── El cobro sale mal ────────────────────────────────────────────────────────
async def test_una_tarjeta_rechazada_cancela_el_pedido_y_devuelve_el_stock(
    sesion, monkeypatch
):
    """
    Un rechazo es definitivo: esa compra no va a completarse.

    Sin esto el pedido se quedaría en PENDING para siempre, reteniendo un
    inventario que nadie va a pagar.
    """
    usuario = await crear_usuario(sesion)
    producto = await crear_producto(sesion, stock=10)
    orden = await _pedido_esperando_pago(sesion, usuario, producto, unidades=3)
    assert await _stock_de(sesion, producto.id) == 7

    async def autorizar_falso(**_):
        raise ErrorDeNiubiz("Tarjeta rechazada", es_rechazo=True)

    monkeypatch.setattr(niubiz_service, "autorizar", autorizar_falso)

    resultado = await order_service.confirmar_pago_de_niubiz(sesion, orden.id, "tok")

    assert resultado.estado == "cancelada"
    await sesion.refresh(orden)
    assert orden.status == OrderStatus.CANCELLED
    assert await _stock_de(sesion, producto.id) == 10


async def test_si_niubiz_no_contesta_el_pedido_no_se_toca(sesion, monkeypatch):
    """
    Esta es la prueba que protege la dirección de retorno.

    Que la pasarela no conteste no dice nada sobre la tarjeta, así que el
    pedido sigue esperando pago y se puede reintentar. Si en este caso también
    se cancelara, cualquiera que conociera el identificador de un pedido ajeno
    podría anularlo mandando basura a una dirección que no pide autenticación.
    """
    usuario = await crear_usuario(sesion)
    producto = await crear_producto(sesion, stock=10)
    orden = await _pedido_esperando_pago(sesion, usuario, producto, unidades=3)

    async def autorizar_falso(**_):
        raise ErrorDeNiubiz("No se pudo contactar con Niubiz")

    monkeypatch.setattr(niubiz_service, "autorizar", autorizar_falso)

    resultado = await order_service.confirmar_pago_de_niubiz(sesion, orden.id, "tok")

    assert resultado.estado == "sin cambios"
    await sesion.refresh(orden)
    assert orden.status == OrderStatus.PENDING
    # Y el inventario sigue apartado para ese pedido, que no ha muerto.
    assert await _stock_de(sesion, producto.id) == 7


async def test_un_pedido_ya_pagado_no_se_vuelve_a_cobrar(sesion, monkeypatch):
    """
    El retorno se puede recargar, y el formulario reenviar.

    Se corta antes de llamar a la pasarela: un segundo cargo sobre la misma
    tarjeta no se arregla con una disculpa.
    """
    usuario = await crear_usuario(sesion)
    producto = await crear_producto(sesion)
    orden = await _pedido_esperando_pago(sesion, usuario, producto)
    orden.status = OrderStatus.COMPLETED
    await sesion.commit()

    async def autorizar_falso(**_):
        raise AssertionError("no debería haberse llamado a Niubiz")

    monkeypatch.setattr(niubiz_service, "autorizar", autorizar_falso)

    resultado = await order_service.confirmar_pago_de_niubiz(sesion, orden.id, "tok")

    assert resultado.estado == "sin cambios"


# ── El número de compra ──────────────────────────────────────────────────────
async def test_el_numero_de_compra_se_asigna_una_vez_y_se_conserva(sesion):
    """
    La clave de sesión y la autorización tienen que llevar el mismo número.

    Un comprador que abre el formulario, lo cierra y vuelve a intentarlo debe
    reusar el suyo; generar uno nuevo en cada intento rompería la
    correspondencia entre el pedido y lo que se ve en el panel de Niubiz.
    """
    usuario = await crear_usuario(sesion)
    producto = await crear_producto(sesion)
    orden = await _pedido_esperando_pago(sesion, usuario, producto)
    orden.purchase_number = None
    await sesion.commit()

    primero = await order_service.asignar_numero_de_compra(sesion, orden)
    segundo = await order_service.asignar_numero_de_compra(sesion, orden)

    assert primero == segundo
    assert len(primero) <= 12 and primero.isdigit()


# ── Quién puede pagar qué ────────────────────────────────────────────────────
async def test_nadie_puede_abrir_una_sesion_de_pago_de_otro(cliente, sesion):
    dueno = await crear_usuario(sesion, email="dueno@ejemplo.com")
    await crear_usuario(sesion, email="intruso@ejemplo.com")
    producto = await crear_producto(sesion)
    orden = await _pedido_esperando_pago(sesion, dueno, producto)
    # Se guarda antes de la petición: después, la sesión de la prueba tiene los
    # objetos expirados por el commit que hizo la aplicación.
    orden_id = orden.id

    token = await token_de(cliente, "intruso@ejemplo.com")
    respuesta = await cliente.post(
        f"/api/v1/orders/{orden_id}/niubiz/sesion",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert respuesta.status_code == 403


async def test_sin_credenciales_la_tienda_no_ofrece_niubiz(cliente, sesion, monkeypatch):
    """
    Mejor no ofrecerlo que ofrecerlo y fallar con la tarjeta ya en la mano.

    El checkout se entera por este campo de la orden, no adivinándolo.
    """
    monkeypatch.setattr(
        type(niubiz_service), "esta_configurado", property(lambda self: False)
    )

    usuario = await crear_usuario(sesion)
    producto = await crear_producto(sesion)
    orden = await _pedido_esperando_pago(sesion, usuario, producto)

    token = await token_de(cliente, "cliente@ejemplo.com")
    detalle = await cliente.get(
        f"/api/v1/orders/{orden.id}", headers={"Authorization": f"Bearer {token}"}
    )

    assert detalle.status_code == 200
    assert detalle.json()["niubiz_disponible"] is False

    sesion_de_pago = await cliente.post(
        f"/api/v1/orders/{orden.id}/niubiz/sesion",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert sesion_de_pago.status_code == 503
