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


# ─────────────────────────────────────────────────────────────────────────────
# El entorno declarado
# ─────────────────────────────────────────────────────────────────────────────
#
# MercadoPago dejó de prefijar con `TEST-` las credenciales de prueba: hoy salen
# del panel con `APP_USR-`, igual que las de producción. Deducir el entorno del
# prefijo pasó de ser suficiente a ser peligroso, porque falla en silencio y en
# la dirección peor: dar por real un cobro que no lo es, o al revés.


def _servicio(monkeypatch, token: str, entorno: str = ""):
    from app.core import config
    from app.services import payment_service as modulo

    ajustes = config.get_settings()
    monkeypatch.setattr(ajustes, "MERCADOPAGO_ACCESS_TOKEN", token, raising=False)
    monkeypatch.setattr(ajustes, "MERCADOPAGO_ENTORNO", entorno, raising=False)
    return modulo.PaymentService()


def test_un_token_de_prueba_moderno_se_reconoce_si_se_declara(monkeypatch):
    """El caso que rompía: credenciales de prueba con prefijo de producción."""
    servicio = _servicio(monkeypatch, "APP_USR-7978012700209274-abc", entorno="test")

    assert servicio.es_de_prueba


def test_sin_declararlo_ese_mismo_token_pasa_por_produccion(monkeypatch):
    """
    Es el comportamiento heredado y por eso hay que declarar el entorno. La
    prueba lo fija para que nadie lo lea como un descuido.
    """
    servicio = _servicio(monkeypatch, "APP_USR-7978012700209274-abc")

    assert not servicio.es_de_prueba


def test_lo_declarado_manda_sobre_el_prefijo(monkeypatch):
    """
    Un token `TEST-` con el entorno declarado como producción cuenta como
    producción. Si el prefijo ganara, declarar el entorno no serviría de nada
    justo cuando hace falta.
    """
    servicio = _servicio(monkeypatch, "TEST-1234", entorno="produccion")

    assert not servicio.es_de_prueba


def test_el_entorno_acepta_las_formas_en_que_se_escribe(monkeypatch):
    for escrito in ("test", "TEST", " Pruebas ", "sandbox"):
        assert _servicio(monkeypatch, "APP_USR-1", entorno=escrito).es_de_prueba


def test_sin_token_no_hay_pagos_configurados(monkeypatch):
    servicio = _servicio(monkeypatch, "", entorno="test")

    assert not servicio.is_configured
