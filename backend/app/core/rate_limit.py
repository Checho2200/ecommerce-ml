"""
Límite de peticiones por IP.

Existe sobre todo por el inicio de sesión: sin un tope, cualquiera puede
probar contraseñas contra /api/v1/auth/login a la velocidad que le permita la
red. También protege el registro y el envío de correos de recuperación, que
son los dos puntos donde una petición barata para el atacante cuesta trabajo
al servidor.

El almacén es la memoria del proceso. Es suficiente aquí: el backend corre en
una sola instancia del plan gratuito de Render. Con varias instancias haría
falta un Redis compartido.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request


def obtener_ip(request: Request) -> str:
    """
    IP real del cliente.

    Render atiende detrás de un proxy, así que `request.client.host` es
    siempre la IP del propio proxy y todos los usuarios contarían como uno
    solo. La original viaja en X-Forwarded-For, donde el primer elemento es
    quien inició la petición.
    """
    reenviada = request.headers.get("x-forwarded-for")
    if reenviada:
        return reenviada.split(",")[0].strip()
    return get_remote_address(request)


limiter = Limiter(key_func=obtener_ip, headers_enabled=True)
