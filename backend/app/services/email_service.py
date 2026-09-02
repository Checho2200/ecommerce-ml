"""
Envío de correo saliente por SMTP.

Cubre dos avisos: el enlace para restablecer la contraseña y la confirmación
de un pedido pagado.

Si no hay SMTP_HOST configurado el servicio no falla: escribe el mensaje en el
log del servidor y sigue. Así el flujo completo se puede probar en local sin
dar de alta un proveedor de correo, y una caída del proveedor en producción no
tumba la compra —el pedido ya está pagado y registrado; el correo es un aviso,
no parte de la transacción.
"""

import smtplib
from email.message import EmailMessage

from app.core.config import get_settings

settings = get_settings()


def esta_configurado() -> bool:
    """True si hay un servidor SMTP al que enviar."""
    return bool(settings.SMTP_HOST)


def _remitente() -> str:
    return settings.SMTP_FROM or settings.SMTP_USER or "no-reply@grupostsperu.com"


def enviar_correo(destinatario: str, asunto: str, cuerpo: str) -> bool:
    """
    Envía un correo de texto plano. Devuelve True si salió de verdad.

    Nunca lanza: quien llama está atendiendo una petición del usuario y un
    fallo del correo no debe convertirse en un error de la API.
    """
    if not esta_configurado():
        print(
            "[correo] SMTP no configurado; el mensaje no se envió.\n"
            f"  Para:    {destinatario}\n"
            f"  Asunto:  {asunto}\n"
            f"{cuerpo}"
        )
        return False

    mensaje = EmailMessage()
    mensaje["From"] = _remitente()
    mensaje["To"] = destinatario
    mensaje["Subject"] = asunto
    mensaje.set_content(cuerpo)

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as servidor:
            if settings.SMTP_STARTTLS:
                servidor.starttls()
            if settings.SMTP_USER:
                servidor.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            servidor.send_message(mensaje)
        return True
    except Exception as exc:  # noqa: BLE001 - se reporta, no se propaga
        print(f"[correo] No se pudo enviar a {destinatario}: {exc}")
        return False


def enviar_enlace_de_recuperacion(destinatario: str, nombre: str, enlace: str) -> bool:
    """Correo con el enlace para elegir una contraseña nueva."""
    minutos = settings.RESET_TOKEN_EXPIRE_MINUTES
    cuerpo = (
        f"Hola {nombre}:\n\n"
        "Recibimos una solicitud para restablecer la contraseña de tu cuenta en "
        f"{settings.APP_NAME}. Para elegir una nueva, entra aquí:\n\n"
        f"{enlace}\n\n"
        f"El enlace vence en {minutos} minutos y sirve una sola vez.\n\n"
        "Si no fuiste tú, no hace falta que hagas nada: tu contraseña actual "
        "sigue siendo válida.\n\n"
        "Grupo STS SAC"
    )
    return enviar_correo(destinatario, "Restablece tu contraseña", cuerpo)


def enviar_confirmacion_de_pedido(
    destinatario: str, nombre: str, order_id: str, total: float
) -> bool:
    """Correo que confirma un pedido cuyo pago ya fue aprobado."""
    cuerpo = (
        f"Hola {nombre}:\n\n"
        f"Confirmamos el pago de tu pedido {order_id[:8].upper()} por "
        f"S/ {total:.2f}. Ya lo estamos preparando.\n\n"
        f"Puedes seguir su estado en {settings.FRONTEND_URL}/orders\n\n"
        "Gracias por tu compra.\n\n"
        "Grupo STS SAC"
    )
    return enviar_correo(destinatario, "Confirmación de tu pedido", cuerpo)
