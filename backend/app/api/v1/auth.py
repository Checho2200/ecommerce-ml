"""
Endpoints de autenticación: registro, login, perfil y recuperación de contraseña.
"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.core.security import (
    create_access_token,
    create_password_reset_token,
    decode_password_reset_token,
    hash_password,
    reset_token_sigue_vigente,
    verify_password,
)
from app.models.user import User, UserRole
from app.schemas.user import (
    ForgotPasswordRequest,
    MensajeResponse,
    ResetPasswordRequest,
    Token,
    UserLogin,
    UserRegister,
    UserResponse,
    UserUpdate,
)
from app.api.deps import get_current_user
from app.services import email_service

settings = get_settings()

router = APIRouter(prefix="/auth", tags=["Autenticación"])

# Se responde lo mismo exista o no la cuenta. Contestar "ese correo no está
# registrado" convertiría este endpoint en una forma cómoda de averiguar qué
# direcciones tienen cuenta en la tienda.
RESPUESTA_RECUPERACION = (
    "Si el correo corresponde a una cuenta, te enviamos un enlace para "
    "restablecer la contraseña."
)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/hour")
async def register(
    request: Request,
    # `response` no se usa en el cuerpo, pero tiene que estar: con
    # headers_enabled, slowapi escribe las cabeceras de límite (X-RateLimit-*)
    # sobre este objeto tras un retorno correcto. Sin el parámetro, intentaba
    # inyectarlas sobre el modelo Pydantic devuelto y reventaba con un 500 en
    # cada registro o login que sí funcionaba —solo en producción, porque las
    # pruebas corren con el limitador apagado—.
    response: Response,
    data: UserRegister,
    db: AsyncSession = Depends(get_db),
):
    """
    Registra un nuevo usuario con rol CLIENTE.
    Valida que el email no esté ya registrado.
    """
    # Verificar email duplicado
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El email ya está registrado",
        )

    # Crear usuario
    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        phone=data.phone,
        role=UserRole.CLIENTE,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    return user


@router.post("/login", response_model=Token)
@limiter.limit("10/minute")
async def login(
    request: Request,
    response: Response,  # requerido por slowapi con headers_enabled; ver register()
    data: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    """
    Autentica un usuario y retorna un JWT.
    El token incluye user_id y role en el payload.

    El tope de intentos por IP está para que probar contraseñas a ciegas deje
    de ser gratis: sin él, /login acepta miles de intentos por minuto.
    """
    # Buscar usuario por email
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cuenta desactivada. Contacte al administrador.",
        )

    # Generar token
    access_token = create_access_token(
        data={"sub": user.id, "role": user.role}
    )

    return Token(access_token=access_token)


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    """Retorna el perfil del usuario autenticado."""
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_me(
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Actualiza el nombre y el teléfono del usuario autenticado.

    La página de perfil ya ofrecía este formulario, pero el endpoint no
    existía: el guardado devolvía 405 y la pantalla se limitaba a mostrar el
    cambio sin que llegara a la base de datos.

    Ni el correo ni el rol se tocan aquí. El correo identifica la cuenta, y
    dejar que cada quien se cambie el rol convertiría el panel de
    administración en una puerta abierta.
    """
    if data.full_name is not None:
        current_user.full_name = data.full_name
    if data.phone is not None:
        current_user.phone = data.phone

    await db.flush()
    await db.refresh(current_user)

    return current_user


@router.post(
    "/forgot-password",
    response_model=MensajeResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
@limiter.limit("5/hour")
async def forgot_password(
    request: Request,
    response: Response,  # requerido por slowapi con headers_enabled; ver register()
    data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Envía por correo un enlace para elegir una contraseña nueva.

    El envío va en segundo plano porque hablar con el servidor de correo tarda
    lo suyo y no hay razón para que el usuario espere a que termine.
    """
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if user and user.is_active:
        token = create_password_reset_token(user.id, user.hashed_password)
        enlace = f"{settings.FRONTEND_URL}/reset-password?token={token}"
        background_tasks.add_task(
            email_service.enviar_enlace_de_recuperacion,
            user.email,
            user.full_name,
            enlace,
        )

    return MensajeResponse(message=RESPUESTA_RECUPERACION)


@router.post("/reset-password", response_model=MensajeResponse)
@limiter.limit("10/hour")
async def reset_password(
    request: Request,
    response: Response,  # requerido por slowapi con headers_enabled; ver register()
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Cambia la contraseña usando el token que llegó por correo."""
    invalido = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="El enlace no es válido o ya venció. Solicita uno nuevo.",
    )

    payload = decode_password_reset_token(data.token)
    if payload is None:
        raise invalido

    result = await db.execute(select(User).where(User.id == payload.get("sub")))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise invalido

    # El token lleva la huella de la contraseña que estaba vigente cuando se
    # pidió; si ya se cambió, el enlace queda gastado.
    if not reset_token_sigue_vigente(payload, user.hashed_password):
        raise invalido

    user.hashed_password = hash_password(data.new_password)
    await db.flush()

    return MensajeResponse(message="Tu contraseña se actualizó. Ya puedes iniciar sesión.")
