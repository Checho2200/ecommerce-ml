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


# ── De qué entorno es el token ───────────────────────────────────────────────
#
# Con un token de pruebas hay que mandar al comprador a `sandbox_init_point`, y
# con uno de producción a `init_point`. Equivocarse manda a alguien a un
# checkout donde su pago no existe, así que conviene tenerlo sujeto.


class _SdkFalso:
    """Un SDK de MercadoPago que devuelve una preferencia ya escrita."""

    def __init__(self, respuesta: dict):
        self._respuesta = respuesta

    def preference(self):
        return self

    def create(self, datos: dict) -> dict:
        return {"response": self._respuesta}


PREFERENCIA = {
    "init_point": "https://mercadopago.com/checkout/produccion",
    "sandbox_init_point": "https://sandbox.mercadopago.com/checkout/pruebas",
}


def _servicio_con(token: str) -> PaymentService:
    servicio = PaymentService()
    servicio.access_token = token
    servicio.sdk = _SdkFalso(PREFERENCIA)
    return servicio


def _preferencia_de(servicio: PaymentService) -> str:
    return servicio.create_preference(
        order_id="una-orden",
        items=[{"title": "Teclado", "quantity": 1, "unit_price": 99.0}],
        payer_email="cliente@ejemplo.com",
    )


def test_un_token_de_pruebas_manda_al_checkout_de_pruebas():
    servicio = _servicio_con("TEST-1234567890")

    assert servicio.es_de_prueba
    assert _preferencia_de(servicio) == PREFERENCIA["sandbox_init_point"]


def test_un_token_de_produccion_manda_al_checkout_real():
    servicio = _servicio_con("APP_USR-1234567890")

    assert not servicio.es_de_prueba
    assert _preferencia_de(servicio) == PREFERENCIA["init_point"]


def test_un_token_de_produccion_que_contiene_test_sigue_siendo_de_produccion():
    # Se mira el prefijo `TEST-`, no un "TEST" en cualquier posición. Con la
    # comprobación anterior, un token real que lo llevara dentro habría mandado
    # a los compradores al checkout de pruebas, donde su pago no existe.
    servicio = _servicio_con("APP_USR-CONTEST-99")

    assert not servicio.es_de_prueba
    assert _preferencia_de(servicio) == PREFERENCIA["init_point"]


def test_el_token_sale_de_la_configuracion_y_no_solo_del_entorno(monkeypatch):
    # Es lo que hace que ponerlo en `backend/.env` funcione. Antes se leía con
    # os.getenv, que no mira ese archivo: el token estaba escrito donde dice la
    # documentación y el checkout respondía 503 igualmente.
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "MERCADOPAGO_ACCESS_TOKEN", "TEST-desde-el-env")

    servicio = PaymentService()

    assert servicio.is_configured
    assert servicio.es_de_prueba
