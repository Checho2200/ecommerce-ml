"""
Schemas Pydantic para autenticación y gestión de usuarios.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ValidationInfo, field_validator

from app.core.passwords import ContrasenaDebil, LONGITUD_MAXIMA, LONGITUD_MINIMA
from app.core import passwords


# --- Auth Requests ---
class UserRegister(BaseModel):
    """Schema para registro de nuevo usuario."""
    email: EmailStr
    password: str = Field(..., min_length=LONGITUD_MINIMA, max_length=LONGITUD_MAXIMA)
    full_name: str = Field(..., min_length=2, max_length=150)
    phone: Optional[str] = Field(None, max_length=20)

    # La política completa —longitud, claves de diccionario, el correo dentro
    # de la clave— vive en app/core/passwords.py. Aquí solo se aplica, y se
    # aplica igual en el registro y en el restablecimiento: una regla que solo
    # rige en la puerta de entrada la esquiva quien pide un enlace de
    # recuperación. El login NO la usa: quien ya tiene una contraseña anterior
    # más corta tiene que poder entrar y cambiarla.
    @field_validator("password")
    @classmethod
    def _politica(cls, valor: str, info: ValidationInfo) -> str:
        try:
            return passwords.validar(valor, info.data.get("email"))
        except ContrasenaDebil as error:
            raise ValueError(str(error)) from error


class UserLogin(BaseModel):
    """Schema para login."""
    email: EmailStr
    password: str


# --- Auth Responses ---
class Token(BaseModel):
    """Respuesta con token JWT."""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Datos extraídos del token JWT."""
    user_id: str
    role: str


# --- User Responses ---
class UserResponse(BaseModel):
    """Respuesta pública de usuario (sin password)."""
    id: str
    email: str
    full_name: str
    phone: Optional[str] = None
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    """Schema para actualizar perfil de usuario."""
    full_name: Optional[str] = Field(None, min_length=2, max_length=150)
    phone: Optional[str] = Field(None, max_length=20)


# --- Recuperación de contraseña ---
class ForgotPasswordRequest(BaseModel):
    """Solicitud del enlace para restablecer la contraseña."""
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Nueva contraseña, acompañada del token que llegó por correo."""
    token: str
    new_password: str = Field(..., min_length=LONGITUD_MINIMA, max_length=LONGITUD_MAXIMA)

    @field_validator("new_password")
    @classmethod
    def _politica(cls, valor: str) -> str:
        try:
            # Sin el correo: aquí solo se conoce el token, y el usuario al que
            # pertenece se resuelve después, ya en el endpoint.
            return passwords.validar(valor)
        except ContrasenaDebil as error:
            raise ValueError(str(error)) from error


class MensajeResponse(BaseModel):
    """Respuesta simple para operaciones que no devuelven un recurso."""
    message: str
