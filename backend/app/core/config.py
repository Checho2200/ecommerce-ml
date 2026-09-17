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

    # La URL pública del propio backend. Es la que se le da a MercadoPago para
    # que mande ahí las notificaciones de pago, así que en local no sirve de
    # nada apuntarla a localhost: la pasarela no puede alcanzarlo.
    BACKEND_URL: str = "http://localhost:8000"

    # Imágenes del panel de administración (Cloudinary).
    # Una sola variable con todo dentro, tal como la entrega el panel de
    # Cloudinary: cloudinary://<api_key>:<api_secret>@<cloud_name>.
    # Si queda vacía, las imágenes se guardan en la base de datos, que es lo
    # que permite trabajar en local sin dar de alta ninguna cuenta.
    CLOUDINARY_URL: str = ""
    # Carpeta dentro de Cloudinary donde aterriza todo lo que sube el panel,
    # para no mezclarlo con lo que haya en la cuenta.
    CLOUDINARY_FOLDER: str = "sanchez-tech-store"

    # Pagos
    #
    # La tienda cobra con una pasarela simulada y no hay nada que configurar:
    # ninguna credencial, ningún entorno que declarar. Es deliberado. Estuvieron
    # integradas MercadoPago y Niubiz, y las dos se retiraron —la primera
    # rechazaba los cobros sin llegar a registrarlos, la segunda exige una
    # afiliación comercial y una certificación—. Lo que este trabajo demuestra
    # es la detección de fraude, no el cobro.
    #
    # La simulación se declara siempre: en la pantalla, en cada orden
    # (`payment_gateway`) y en /health.

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
