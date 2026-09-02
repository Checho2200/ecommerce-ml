"""
Sanchez Tech Store — Backend API
Entry point de la aplicación FastAPI.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.requests import Request

from app.core.config import get_settings
from app.core.database import create_tables
from app.core.rate_limit import limiter
from app.services.errors import ErrorDeNegocio

# Importar modelos para que SQLAlchemy los registre
import app.models  # noqa: F401

# Importar routers
from app.api.v1.auth import router as auth_router
from app.api.v1.products import router as products_router
from app.api.v1.categories import router as categories_router
from app.api.v1.orders import router as orders_router
from app.api.v1.service_orders import router as service_orders_router
from app.api.v1.fraud import router as fraud_router
from app.api.v1.reviews import router as reviews_router
from app.api.v1.upload import router as upload_router
from app.services.fraud_service import fraud_service
from app.services.payment_service import payment_service

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Ciclo de vida de la aplicación.
    - Startup: prepara el esquema en desarrollo y carga el modelo ML.
    - Shutdown: libera recursos.
    """
    # === STARTUP ===
    print(f"🚀 Iniciando {settings.APP_NAME}...")

    # El esquema se crea al vuelo solo en SQLite, que es la base de desarrollo
    # y la de las pruebas. En PostgreSQL manda Alembic: el despliegue ejecuta
    # `python -m app.scripts.apply_migrations` antes de arrancar. Crear las
    # tablas también aquí dejaría dos fuentes de verdad para el esquema y las
    # migraciones se volverían decorativas.
    if settings.DATABASE_URL.startswith("sqlite"):
        await create_tables()
        print("📦 Tablas creadas/verificadas (SQLite)")
    else:
        print("📦 Esquema gestionado por Alembic")

    # Cargar modelo LightGBM de detección de fraude (Fase 4 completada)
    fraud_service.load_model()

    print(f"✅ {settings.APP_NAME} listo!")
    yield

    # === SHUTDOWN ===
    print(f"👋 Cerrando {settings.APP_NAME}...")


# Crear app
app = FastAPI(
    title=settings.APP_NAME,
    description="API para e-commerce de periféricos y componentes de hardware con detección de fraude basada en LightGBM",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Límite de peticiones por IP (ver app/core/rate_limit.py)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(ErrorDeNegocio)
async def manejar_error_de_negocio(request: Request, error: ErrorDeNegocio):
    """
    Traduce a HTTP las reglas del negocio que no se cumplieron.

    Los servicios lanzan errores de dominio —"no hay stock", "esa orden no
    existe"— sin saber nada de códigos de estado. La traducción ocurre aquí, en
    un único sitio, de modo que la capa de negocio no dependa de FastAPI y se
    pueda usar igual desde un script o una tarea en segundo plano.
    """
    return JSONResponse(status_code=error.codigo_http, content={"detail": error.mensaje})

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "http://localhost:3000",
        "http://localhost:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Montar routers bajo /api/v1
API_PREFIX = "/api/v1"
app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(products_router, prefix=API_PREFIX)
app.include_router(categories_router, prefix=API_PREFIX)
app.include_router(orders_router, prefix=API_PREFIX)
app.include_router(service_orders_router, prefix=API_PREFIX)
app.include_router(fraud_router, prefix=API_PREFIX)
app.include_router(reviews_router, prefix=f"{API_PREFIX}/reviews", tags=["Reviews"])
app.include_router(upload_router, prefix=API_PREFIX)

# Servir archivos estáticos (imágenes subidas)
static_dir = Path("static")
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint."""
    return {
        "app": settings.APP_NAME,
        "status": "running",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health():
    """
    Estado del servicio.

    Consulta la base de datos de verdad en lugar de responder "connected" sin
    comprobar nada, que era lo que hacía antes. Como efecto secundario útil,
    el ping periódico que mantiene despierto a Render también mantiene activa
    la base en Neon, que igualmente se suspende por inactividad.
    """
    import sqlalchemy

    from app.core.database import engine

    try:
        async with engine.connect() as conn:
            await conn.execute(sqlalchemy.text("SELECT 1"))
        database = "connected"
    except Exception as exc:  # noqa: BLE001 - se reporta, no se propaga
        print(f"Health check: fallo al consultar la base de datos: {exc}")
        database = "unavailable"

    return {
        "status": "healthy" if database == "connected" else "degraded",
        "database": database,
        "ml_model": "loaded" if fraud_service.is_loaded() else "not_loaded",
        # Solo dice si hay token cargado, nunca el token en si: sirve para
        # comprobar desde fuera que la variable de entorno llego al servidor.
        "payments": "configured" if payment_service.is_configured else "not_configured",
    }
