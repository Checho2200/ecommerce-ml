"""
Pruebas de la liberación de una orden retenida por el modelo.

El botón "Dejar pasar" del panel promete que el cliente ya puede pagar. Estas
pruebas son las que sostienen esa promesa: que la orden reciba el enlace de
pago que nunca tuvo, y que no la cancele el plazo de caducidad por el tiempo
que pasó esperando a que alguien la revisara.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.models.order import Order, OrderItem, OrderStatus
from app.models.user import UserRole
from app.services import order_service
from app.services.errors import OperacionNoPermitida

from tests.conftest import cabeceras_de, crear_producto, crear_usuario


async def _orden_retenida(sesion, usuario, producto, creada_hace=timedelta(0)):
    orden = Order(
        user_id=usuario.id,
        total_amount=producto.price,
        status=OrderStatus.FRAUD_REVIEW,
        shipping_address="Jr. Alfonso Ugarte 493",
        shipping_city="Trujillo",
        created_at=datetime.now(timezone.utc) - creada_hace,
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
    await sesion.commit()
    await sesion.refresh(orden)
    return orden


@pytest.mark.asyncio
async def test_liberar_deja_la_orden_lista_para_pagarse(sesion):
    usuario = await crear_usuario(sesion)
    producto = await crear_producto(sesion)
    orden = await _orden_retenida(sesion, usuario, producto)

    assert orden.payable_since is None, "una orden retenida nunca fue pagable"

    liberada, _url = await order_service.liberar_de_revision(sesion, orden.id)

    assert liberada.status == OrderStatus.PENDING
    # Sin esta marca, el plazo se contaría desde que se creó la orden.
    assert liberada.payable_since is not None


@pytest.mark.asyncio
async def test_no_se_libera_lo_que_no_estaba_en_revision(sesion):
    usuario = await crear_usuario(sesion)
    producto = await crear_producto(sesion)
    orden = await _orden_retenida(sesion, usuario, producto)
    orden.status = OrderStatus.REJECTED
    await sesion.commit()

    with pytest.raises(OperacionNoPermitida):
        await order_service.liberar_de_revision(sesion, orden.id)


@pytest.mark.asyncio
async def test_una_orden_recien_liberada_no_caduca_por_lo_que_esperó(sesion):
    """
    El caso que motivó la columna `payable_since`.

    Una orden que estuvo un día entera en revisión y se aprueba ahora llevaba,
    contando desde `created_at`, mucho más de las dos horas del plazo: la
    siguiente compra del mismo cliente la habría cancelado y devuelto su stock,
    justo después de que un administrador decidiera dejarla pasar.
    """
    usuario = await crear_usuario(sesion)
    producto = await crear_producto(sesion)
    orden = await _orden_retenida(sesion, usuario, producto, creada_hace=timedelta(days=1))

    await order_service.liberar_de_revision(sesion, orden.id)
    await order_service.caducar_pendientes(sesion, usuario.id)
    await sesion.refresh(orden)

    assert orden.status == OrderStatus.PENDING


@pytest.mark.asyncio
async def test_una_orden_pendiente_de_verdad_sigue_caducando(sesion):
    """La corrección anterior no debe desactivar el plazo para todo lo demás."""
    usuario = await crear_usuario(sesion)
    producto = await crear_producto(sesion)
    orden = await _orden_retenida(sesion, usuario, producto, creada_hace=timedelta(days=1))
    orden.status = OrderStatus.PENDING
    orden.payable_since = datetime.now(timezone.utc) - timedelta(days=1)
    await sesion.commit()

    await order_service.caducar_pendientes(sesion, usuario.id)
    await sesion.refresh(orden)

    assert orden.status == OrderStatus.CANCELLED


@pytest.mark.asyncio
async def test_liberar_es_solo_para_administradores(cliente, sesion):
    usuario = await crear_usuario(sesion, email="cliente@ejemplo.com")
    producto = await crear_producto(sesion)
    orden = await _orden_retenida(sesion, usuario, producto)
    # El id se guarda ahora: cada petición hace commit y deja caducado el
    # objeto, y releerlo desde una prueba síncrona ya no se puede.
    orden_id = orden.id

    cabeceras = await cabeceras_de(cliente, "cliente@ejemplo.com")
    respuesta = await cliente.patch(f"/api/v1/orders/{orden_id}/release", headers=cabeceras)
    assert respuesta.status_code == 403

    await crear_usuario(sesion, email="admin@ejemplo.com", rol=UserRole.ADMIN)
    cabeceras = await cabeceras_de(cliente, "admin@ejemplo.com")
    respuesta = await cliente.patch(f"/api/v1/orders/{orden_id}/release", headers=cabeceras)
    assert respuesta.status_code == 200
    assert respuesta.json()["status"] == "PENDING"
