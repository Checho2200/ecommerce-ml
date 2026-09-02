"""
Configuración central de la aplicación.
Carga variables desde .env usando Pydantic BaseSettings.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Sanchez Tech Store"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./sanchez_ecommerce.db"

    # Security
    SECRET_KEY: str = "tu-clave-secreta-cambiar-en-produccion-min-32-chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Cuánto vive el enlace de "olvidé mi contraseña". Corto a propósito: el
    # enlace llega por correo y no se puede revocar desde el servidor.
    RESET_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS
    FRONTEND_URL: str = "http://localhost:3000"

    # Pagos
    # Clave secreta del webhook, que se genera en el panel de MercadoPago
    # (Tus integraciones -> Webhooks). Sirve para comprobar la firma de cada
    # notificación. Si se deja vacía, la firma no se exige.
    MERCADOPAGO_WEBHOOK_SECRET: str = ""

    # Correo saliente (SMTP). Si SMTP_HOST queda vacío, la aplicación no envía
    # nada: escribe el mensaje en el log del servidor. Eso permite probar el
    # flujo completo en local sin dar de alta un proveedor de correo.
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    SMTP_STARTTLS: bool = True

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    """Singleton cacheado de la configuración."""
    return Settings()
