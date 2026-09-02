"""
Comprobación de la firma de los webhooks de MercadoPago.

El endpoint que recibe las notificaciones es público: su URL viaja en cada
preferencia de pago. Sin comprobar nada, cualquiera puede lanzarle avisos
inventados. El daño directo es limitado —el manejador vuelve a consultar el
pago contra la API de MercadoPago antes de tocar el pedido— pero cada aviso
falso cuesta una llamada a esa API, y MercadoPago describe esta verificación
como parte de la integración.

Cómo funciona: la notificación llega con dos cabeceras.

    x-signature:  ts=1704908010,v1=618c85345248dd820d5fd456117c2ab2ef8eda45a0282ff693eac24131a5e839
    x-request-id: bc1b1a56-0f3a-4b1b-9e57-2ee4a5cbf3b7

Con ellas se arma la plantilla `id:<data.id>;request-id:<x-request-id>;ts:<ts>;`
y se calcula su HMAC-SHA256 con la clave secreta del panel. Si coincide con
`v1`, el aviso salió de MercadoPago.
"""

import hashlib
import hmac
from typing import Optional

from app.core.config import get_settings

settings = get_settings()


def hay_clave_configurada() -> bool:
    """True si MERCADOPAGO_WEBHOOK_SECRET tiene valor."""
    return bool(settings.MERCADOPAGO_WEBHOOK_SECRET)


def _partes_de_la_firma(x_signature: str) -> dict:
    """Convierte 'ts=123,v1=abc' en {'ts': '123', 'v1': 'abc'}."""
    partes = {}
    for trozo in x_signature.split(","):
        clave, _, valor = trozo.partition("=")
        clave = clave.strip()
        if clave:
            partes[clave] = valor.strip()
    return partes


def construir_plantilla(data_id: str, request_id: Optional[str], ts: str) -> str:
    """
    Arma la cadena que MercadoPago firma.

    Los tramos vacíos se omiten enteros: si la notificación no trae
    x-request-id, la plantilla no lleva `request-id:;`.
    """
    plantilla = ""
    if data_id:
        # MercadoPago normaliza a minúsculas los identificadores alfanuméricos.
        plantilla += f"id:{data_id.lower()};"
    if request_id:
        plantilla += f"request-id:{request_id};"
    if ts:
        plantilla += f"ts:{ts};"
    return plantilla


def firma_valida(
    x_signature: Optional[str],
    x_request_id: Optional[str],
    data_id: Optional[str],
) -> bool:
    """
    Comprueba la firma de una notificación.

    Devuelve True cuando no hay clave configurada: en desarrollo, y en el
    despliegue mientras la clave no se haya cargado, el webhook tiene que
    seguir funcionando. Quien quiera exigirla, la configura.
    """
    if not hay_clave_configurada():
        return True

    if not x_signature or not data_id:
        return False

    partes = _partes_de_la_firma(x_signature)
    ts = partes.get("ts", "")
    recibida = partes.get("v1", "")

    if not ts or not recibida:
        return False

    esperada = hmac.new(
        settings.MERCADOPAGO_WEBHOOK_SECRET.encode("utf-8"),
        construir_plantilla(data_id, x_request_id, ts).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    # compare_digest y no ==: comparar cadena a cadena tarda distinto según
    # cuántos caracteres coincidan, y eso deja adivinar la firma byte a byte.
    return hmac.compare_digest(esperada, recibida)
