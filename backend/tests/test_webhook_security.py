"""
Pruebas de la verificación de firma de los webhooks de MercadoPago.

El endpoint que recibe las notificaciones es público, así que la firma es lo
único que separa un aviso real de uno inventado.
"""

import hashlib
import hmac

import pytest

from app.core.config import get_settings
from app.services import webhook_security

CLAVE = "clave-secreta-de-prueba"
DATA_ID = "123456789"
REQUEST_ID = "bc1b1a56-0f3a-4b1b-9e57-2ee4a5cbf3b7"
TS = "1704908010"


def firmar(clave: str, plantilla: str) -> str:
    return hmac.new(clave.encode(), plantilla.encode(), hashlib.sha256).hexdigest()


@pytest.fixture
def con_clave(monkeypatch):
    """Configura una clave de webhook para la prueba."""
    ajustes = get_settings()
    monkeypatch.setattr(ajustes, "MERCADOPAGO_WEBHOOK_SECRET", CLAVE)
    return ajustes


@pytest.fixture
def sin_clave(monkeypatch):
    ajustes = get_settings()
    monkeypatch.setattr(ajustes, "MERCADOPAGO_WEBHOOK_SECRET", "")
    return ajustes


def cabecera_valida() -> str:
    plantilla = webhook_security.construir_plantilla(DATA_ID, REQUEST_ID, TS)
    return f"ts={TS},v1={firmar(CLAVE, plantilla)}"


def test_la_plantilla_sigue_el_formato_de_mercadopago():
    plantilla = webhook_security.construir_plantilla(DATA_ID, REQUEST_ID, TS)

    assert plantilla == f"id:{DATA_ID};request-id:{REQUEST_ID};ts:{TS};"


def test_la_plantilla_omite_el_tramo_que_no_llego():
    """Si la notificación no trae x-request-id, ese tramo no aparece."""
    plantilla = webhook_security.construir_plantilla(DATA_ID, None, TS)

    assert plantilla == f"id:{DATA_ID};ts:{TS};"


def test_el_identificador_alfanumerico_va_en_minusculas():
    plantilla = webhook_security.construir_plantilla("ABC123", None, TS)

    assert plantilla.startswith("id:abc123;")


def test_una_firma_correcta_se_acepta(con_clave):
    assert webhook_security.firma_valida(cabecera_valida(), REQUEST_ID, DATA_ID)


def test_una_firma_de_otra_clave_se_rechaza(con_clave):
    plantilla = webhook_security.construir_plantilla(DATA_ID, REQUEST_ID, TS)
    ajena = f"ts={TS},v1={firmar('clave-del-atacante', plantilla)}"

    assert not webhook_security.firma_valida(ajena, REQUEST_ID, DATA_ID)


def test_no_vale_la_firma_de_otra_notificacion(con_clave):
    """Reenviar una firma válida cambiando el pago al que apunta no cuela."""
    assert not webhook_security.firma_valida(cabecera_valida(), REQUEST_ID, "999999999")


def test_cambiar_el_request_id_invalida_la_firma(con_clave):
    assert not webhook_security.firma_valida(cabecera_valida(), "otro-request-id", DATA_ID)


def test_sin_cabecera_de_firma_se_rechaza(con_clave):
    assert not webhook_security.firma_valida(None, REQUEST_ID, DATA_ID)


def test_una_cabecera_incompleta_se_rechaza(con_clave):
    assert not webhook_security.firma_valida(f"ts={TS}", REQUEST_ID, DATA_ID)
    assert not webhook_security.firma_valida("v1=abc", REQUEST_ID, DATA_ID)


def test_sin_clave_configurada_no_se_exige_firma(sin_clave):
    """
    En desarrollo, y en el despliegue mientras la clave no esté cargada, el
    webhook tiene que seguir aceptando notificaciones: si no, ningún pago
    llegaría a confirmarse.
    """
    assert not webhook_security.hay_clave_configurada()
    assert webhook_security.firma_valida(None, None, DATA_ID)


async def test_el_webhook_rechaza_una_notificacion_mal_firmada(cliente, con_clave):
    respuesta = await cliente.post(
        "/api/v1/orders/webhook/mercadopago",
        params={"type": "payment", "data.id": DATA_ID},
        json={"action": "payment.updated", "data": {"id": DATA_ID}},
        headers={"x-signature": f"ts={TS},v1=firma-inventada", "x-request-id": REQUEST_ID},
    )

    assert respuesta.status_code == 401


async def test_el_webhook_ignora_lo_que_no_es_un_pago(cliente, con_clave):
    """
    Las notificaciones de otros temas se descartan antes de mirar la firma:
    no hay nada que hacer con ellas.
    """
    respuesta = await cliente.post(
        "/api/v1/orders/webhook/mercadopago",
        params={"type": "merchant_order", "data.id": DATA_ID},
        json={},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["status"] == "ignored"
