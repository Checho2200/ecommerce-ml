"""
Pruebas del rastro que deja un pago.

Un antifraude sin trazabilidad sirve de poco: cuando llega un contracargo hay
que poder decir qué pago fue, con qué tarjeta y a nombre de quién. Y hay una
señal que solo se ve con esos datos — que la cuenta sea de una persona y la
tarjeta esté a nombre de otra.

La otra mitad de estas pruebas es lo que **no** se guarda. Los cuatro últimos
dígitos son lo único que PCI-DSS permite conservar sin más, precisamente
porque no sirven para cobrar; el número completo y el código de seguridad no
pueden acabar en la base ni por descuido.
"""

from datetime import datetime, timezone

from app.models.order import Order, OrderStatus
from app.services import order_service
from app.services.payment_service import datos_del_pago
from tests.conftest import crear_usuario

# La forma en que MercadoPago responde un pago con tarjeta.
PAGO_APROBADO = {
    "id": 1234567890,
    "status": "approved",
    "payment_method_id": "visa",
    "external_reference": None,  # lo pone la prueba
    "card": {
        "first_six_digits": "450995",
        "last_four_digits": "3704",
        "expiration_month": 11,
        "expiration_year": 2030,
        "cardholder": {"name": "APRO", "identification": {"number": "123456789"}},
    },
}


def test_solo_se_extraen_los_cuatro_ultimos_digitos_y_el_titular():
    extraido = datos_del_pago(PAGO_APROBADO)

    assert extraido["card_last_four"] == "3704"
    assert extraido["card_holder"] == "APRO"
    assert extraido["payment_method"] == "visa"
    assert extraido["payment_id"] == "1234567890"

    # Lo que no puede salir de aquí bajo ningún concepto.
    plano = str(extraido)
    assert "450995" not in plano, "el BIN del emisor no hace falta para el seguimiento"
    assert "expiration" not in extraido
    assert not any("cvv" in clave.lower() or "security" in clave.lower() for clave in extraido)


def test_un_pago_sin_tarjeta_no_inventa_datos():
    # Yape, efectivo o transferencia: no hay tarjeta y no debe aparecer una.
    extraido = datos_del_pago({"id": 42, "status": "approved", "payment_method_id": "yape"})

    assert extraido["payment_method"] == "yape"
    assert extraido["card_last_four"] is None
    assert extraido["card_holder"] is None


async def test_el_cobro_aprobado_deja_el_rastro_en_la_orden(sesion):
    usuario = await crear_usuario(sesion)
    orden = Order(
        user_id=usuario.id,
        total_amount=350.0,
        status=OrderStatus.PENDING,
        shipping_address="Jr. Pizarro 456",
        shipping_city="Trujillo",
    )
    sesion.add(orden)
    await sesion.commit()

    resultado = await order_service.registrar_resultado_del_pago(
        sesion, orden.id, "approved", datos_del_pago(PAGO_APROBADO)
    )

    assert resultado.estado == "completada"
    assert resultado.orden.status == OrderStatus.COMPLETED
    assert resultado.orden.card_last_four == "3704"
    assert resultado.orden.card_holder == "APRO"
    assert resultado.orden.payment_method == "visa"
    assert resultado.orden.payment_id == "1234567890"
    # Y cuándo se cobró, que no es lo mismo que cuándo se hizo el pedido.
    assert resultado.orden.paid_at is not None
    assert resultado.orden.paid_at <= datetime.now(timezone.utc)


async def test_un_pago_rechazado_no_deja_rastro_de_tarjeta(sesion):
    usuario = await crear_usuario(sesion)
    orden = Order(
        user_id=usuario.id,
        total_amount=350.0,
        status=OrderStatus.PENDING,
        shipping_address="Jr. Pizarro 456",
        shipping_city="Trujillo",
    )
    sesion.add(orden)
    await sesion.commit()

    resultado = await order_service.registrar_resultado_del_pago(
        sesion, orden.id, "rejected", datos_del_pago(PAGO_APROBADO)
    )

    assert resultado.estado == "cancelada"
    # No se cobró, así que no hay pago del que dejar constancia.
    assert resultado.orden.card_last_four is None
    assert resultado.orden.paid_at is None


async def test_la_orden_responde_quien_compro_y_con_que(cliente, sesion):
    from app.models.user import UserRole
    from tests.conftest import cabeceras_de

    admin = await crear_usuario(sesion, email="admin@ejemplo.com", rol=UserRole.ADMIN)
    orden = Order(
        user_id=admin.id,
        total_amount=350.0,
        status=OrderStatus.PENDING,
        shipping_address="Jr. Pizarro 456",
        shipping_city="Trujillo",
    )
    sesion.add(orden)
    await sesion.commit()
    await order_service.registrar_resultado_del_pago(
        sesion, orden.id, "approved", datos_del_pago(PAGO_APROBADO)
    )

    cabeceras = await cabeceras_de(cliente, "admin@ejemplo.com")
    cuerpo = (await cliente.get("/api/v1/orders", headers=cabeceras)).json()
    fila = next(o for o in cuerpo["items"] if o["id"] == orden.id)

    assert fila["user_email"] == "admin@ejemplo.com"
    assert fila["card_last_four"] == "3704"
    assert fila["card_holder"] == "APRO"
    assert fila["payment_method"] == "visa"
