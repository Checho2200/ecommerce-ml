"""
Pruebas del momento en que el modelo frena una compra sospechosa.

El sistema retenía en el checkout: una compra que el modelo mandaba a revisión
no llegaba a tener enlace de pago, y el cliente veía «tu pedido está en
revisión» sin poder hacer nada. Eso hace dos cosas malas a la vez. A un cliente
legítimo se le pide que espere sin saber cuánto, y muchos no vuelven. Y al
revisor se le pide que decida sin la señal más útil que existe —si el titular de
la tarjeta coincide con el de la cuenta—, porque esa señal no existe hasta que
se paga.

Ahora se retiene **después del cobro y antes de preparar el pedido**, que es lo
que hacen las tiendas y funciona porque el fraude no cuesta la mercadería hasta
que sale del almacén. Solo un bloqueo impide pagar.

Lo que se comprueba aquí es el recorrido entero de esa decisión: que una compra
en revisión pueda pagarse, que el pago la deje retenida en vez de completada, y
que soltarla la dé por buena sin volver a cobrarla.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.models.fraud_log import FraudLog
from app.models.order import Order, OrderItem, OrderStatus
from app.services import order_service

from tests.conftest import crear_producto, crear_usuario


async def _orden_con_evaluacion(
    sesion, usuario, producto, decision: str, pagada: bool = False
):
    """Un pedido con la evaluación que el modelo le dejó."""
    orden = Order(
        user_id=usuario.id,
        total_amount=producto.price,
        status=OrderStatus.PENDING,
        shipping_address="Jr. Alfonso Ugarte 493",
        shipping_city="Trujillo",
        paid_at=datetime.now(timezone.utc) if pagada else None,
    )
    sesion.add(orden)
    await sesion.flush()
    sesion.add(
        OrderItem(
            order_id=orden.id,
            product_id=producto.id,
            quantity=1,
            unit_price=producto.price,
        )
    )
    sesion.add(
        FraudLog(
            order_id=orden.id,
            fraud_score=0.55,
            decision=decision,
            detection_time_ms=2.0,
        )
    )
    await sesion.commit()
    await sesion.refresh(orden)
    return orden


# ── Al crear el pedido ───────────────────────────────────────────────────────


def test_una_compra_en_revision_nace_pagable():
    """
    Es el cambio de fondo: solo un bloqueo impide pagar. Si REVIEW volviera a
    nacer en FRAUD_REVIEW, el cliente se quedaría otra vez sin poder pagar.
    """
    assert order_service._estado_segun_la_decision("REVIEW") == OrderStatus.PENDING
    assert order_service._estado_segun_la_decision("APPROVED") == OrderStatus.PENDING


def test_una_compra_bloqueada_sigue_sin_llegar_a_la_pasarela():
    """
    El bloqueo es lo único que corta el checkout, y tiene que seguir haciéndolo:
    es el caso en que el modelo está seguro.
    """
    assert order_service._estado_segun_la_decision("BLOCKED") == OrderStatus.REJECTED


# ── Al confirmarse el pago ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_el_pago_de_una_compra_marcada_la_deja_retenida(sesion):
    usuario = await crear_usuario(sesion)
    producto = await crear_producto(sesion)
    orden = await _orden_con_evaluacion(sesion, usuario, producto, "REVIEW")

    resultado = await order_service.registrar_resultado_del_pago(
        sesion,
        orden.id,
        "approved",
        {"payment_id": "SIM-1", "card_last_four": "4242", "card_holder": "OTRO NOMBRE"},
    )

    assert resultado.estado == "retenida"
    await sesion.refresh(orden)
    assert orden.status == OrderStatus.FRAUD_REVIEW
    # Y con la tarjeta guardada, que es la señal que el revisor no tenía antes.
    assert orden.card_last_four == "4242"
    assert orden.card_holder == "OTRO NOMBRE"
    assert orden.paid_at is not None


@pytest.mark.asyncio
async def test_el_pago_de_una_compra_aprobada_la_completa(sesion):
    usuario = await crear_usuario(sesion)
    producto = await crear_producto(sesion)
    orden = await _orden_con_evaluacion(sesion, usuario, producto, "APPROVED")

    resultado = await order_service.registrar_resultado_del_pago(
        sesion, orden.id, "approved", {"payment_id": "SIM-2"}
    )

    assert resultado.estado == "completada"
    await sesion.refresh(orden)
    assert orden.status == OrderStatus.COMPLETED


@pytest.mark.asyncio
async def test_un_pago_rechazado_cancela_igual_estuviera_marcada_o_no(sesion):
    """La retención es para los pagos que prosperan; un rechazo se cancela."""
    usuario = await crear_usuario(sesion)
    producto = await crear_producto(sesion)
    orden = await _orden_con_evaluacion(sesion, usuario, producto, "REVIEW")

    resultado = await order_service.registrar_resultado_del_pago(
        sesion, orden.id, "rejected"
    )

    assert resultado.estado == "cancelada"
    await sesion.refresh(orden)
    assert orden.status == OrderStatus.CANCELLED


# ── Al soltarla ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_soltar_una_retenida_ya_pagada_la_da_por_buena(sesion):
    """
    No hay nada que cobrar: el cliente ya pagó. Soltarla es dejar que se
    prepare. Si volviera a PENDING con un enlace nuevo, se le estaría pidiendo
    que pagara dos veces.
    """
    usuario = await crear_usuario(sesion)
    producto = await crear_producto(sesion)
    orden = await _orden_con_evaluacion(
        sesion, usuario, producto, "REVIEW", pagada=True
    )
    orden.status = OrderStatus.FRAUD_REVIEW
    await sesion.commit()

    suelta, url = await order_service.liberar_de_revision(sesion, orden.id)

    assert suelta.status == OrderStatus.COMPLETED
    assert url is None


@pytest.mark.asyncio
async def test_soltar_una_retenida_sin_pagar_le_da_su_enlace(sesion, monkeypatch):
    """
    El caso heredado: pedidos retenidos con las reglas anteriores, que nunca
    llegaron a la pasarela. Sin enlace, el cliente se quedaría con un pedido
    «pendiente» que no puede pagar por ningún sitio.
    """
    monkeypatch.setattr(
        order_service.payment_service,
        "create_preference",
        lambda **_: "https://mercadopago.example/checkout",
    )

    usuario = await crear_usuario(sesion)
    producto = await crear_producto(sesion)
    orden = await _orden_con_evaluacion(sesion, usuario, producto, "REVIEW")
    orden.status = OrderStatus.FRAUD_REVIEW
    await sesion.commit()

    suelta, url = await order_service.liberar_de_revision(sesion, orden.id)

    assert suelta.status == OrderStatus.PENDING
    assert url == "https://mercadopago.example/checkout"
    # Y el plazo de caducidad arranca ahora, no cuando se creó el pedido.
    # SQLite devuelve la fecha sin zona, así que se le pone la que tiene.
    assert suelta.payable_since is not None
    desde = suelta.payable_since
    if desde.tzinfo is None:
        desde = desde.replace(tzinfo=timezone.utc)
    assert datetime.now(timezone.utc) - desde < timedelta(minutes=1)
