"""
Pruebas del parseo de notificaciones de MercadoPago.

Existen porque el webhook solo entendia el formato antiguo (IPN) y descartaba
en silencio las notificaciones actuales, con lo que un pedido pagado se quedaba
en PENDING para siempre.
"""

from app.services.payment_service import leer_notificacion as _leer_notificacion


def test_acepta_el_webhook_actual_con_type_en_la_query():
    payment_id, es_de_pago = _leer_notificacion(
        {"type": "payment", "data.id": "123456"},
        {"action": "payment.updated", "data": {"id": "123456"}},
    )
    assert payment_id == "123456"
    assert es_de_pago


def test_acepta_la_notificacion_que_solo_trae_cuerpo():
    payment_id, es_de_pago = _leer_notificacion(
        {},
        {"action": "payment.created", "data": {"id": "789"}},
    )
    assert payment_id == "789"
    assert es_de_pago


def test_acepta_el_ipn_antiguo_con_topic_e_id():
    payment_id, es_de_pago = _leer_notificacion({"topic": "payment", "id": "42"}, {})
    assert payment_id == "42"
    assert es_de_pago


def test_ignora_las_notificaciones_que_no_son_de_pagos():
    payment_id, es_de_pago = _leer_notificacion(
        {"type": "merchant_order", "data.id": "999"}, {}
    )
    assert payment_id == "999"
    assert not es_de_pago


def test_ignora_una_notificacion_sin_identificador():
    payment_id, es_de_pago = _leer_notificacion({"type": "payment"}, {})
    assert payment_id is None
    assert es_de_pago
