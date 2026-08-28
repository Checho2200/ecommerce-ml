"""
Pruebas del servicio de pagos.

La mas importante es la primera: antes el token de MercadoPago tenia un valor
por defecto escrito en el codigo, asi que una instalacion sin configurar creia
poder cobrar y fallaba con un error opaco al llamar a la API.
"""

import pytest
from fastapi import HTTPException

from app.services.payment_service import PaymentService


def test_sin_token_el_servicio_se_declara_no_configurado():
    servicio = PaymentService()
    servicio.sdk = None

    assert not servicio.is_configured


def test_sin_token_crear_preferencia_responde_503_y_no_llama_a_mercadopago():
    servicio = PaymentService()
    servicio.sdk = None

    with pytest.raises(HTTPException) as error:
        servicio.create_preference(
            order_id="una-orden",
            items=[{"title": "Teclado", "quantity": 1, "unit_price": 99.0}],
            payer_email="cliente@ejemplo.com",
        )

    assert error.value.status_code == 503


def test_sin_token_verificar_pago_responde_503():
    servicio = PaymentService()
    servicio.sdk = None

    with pytest.raises(HTTPException) as error:
        servicio.verify_payment("123456")

    assert error.value.status_code == 503
