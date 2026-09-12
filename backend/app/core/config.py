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
    # Token de MercadoPago. Sin token, el checkout responde 503 en vez de
    # fingir que cobró.
    MERCADOPAGO_ACCESS_TOKEN: str = ""

    # En qué entorno de MercadoPago se está cobrando: "test" o "produccion".
    #
    # Hasta hace poco no hacía falta declararlo, porque el prefijo del token lo
    # decía: "TEST-" era pruebas y "APP_USR-" producción. **Ya no.** MercadoPago
    # entrega hoy las credenciales de prueba con el prefijo "APP_USR-", el
    # mismo que las de producción, así que adivinarlo por el prefijo da
    # justamente el peor error posible con una pasarela: creer que se está
    # cobrando de verdad cuando no, o al revés.
    #
    # Vacío mantiene el comportamiento anterior —deducirlo del prefijo— para no
    # romper una instalación que ya funcionaba con un token "TEST-".
    MERCADOPAGO_ENTORNO: str = ""

    # ── Niubiz (Visa Perú) ───────────────────────────────────────────────
    #
    # La segunda pasarela. No sustituye a MercadoPago: convive con él, y el
    # comprador elige en el checkout con cuál paga.
    #
    # Las credenciales las entrega Niubiz al afiliar el comercio. Son tres:
    # usuario y contraseña de la API (se mandan como Basic auth para pedir el
    # token de acceso) y el código de comercio. Sin las tres, la opción de
    # pagar con Niubiz no se ofrece —el checkout enseña solo MercadoPago— en
    # lugar de fingir que puede cobrar.
    NIUBIZ_USER: str = ""
    NIUBIZ_PASSWORD: str = ""
    NIUBIZ_MERCHANT_ID: str = ""

    # En qué entorno de Niubiz se cobra: "test" o "produccion".
    #
    # Aquí sí hay que declararlo siempre, porque las credenciales de Niubiz no
    # llevan ninguna marca que distinga un entorno del otro: el mismo usuario y
    # contraseña tienen la forma de siempre en los dos. De esta variable
    # dependen las tres direcciones que se usan —la de la API, la del
    # formulario y la del script del checkout—, así que equivocarla no da un
    # cobro falso: da un error, que es el fallo preferible.
    NIUBIZ_ENTORNO: str = "test"

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
