"""
Schemas Pydantic para autenticación y gestión de usuarios.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


# --- Auth Requests ---
class UserRegister(BaseModel):
    """Schema para registro de nuevo usuario."""
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=100)
    full_name: str = Field(..., min_length=2, max_length=150)
    phone: Optional[str] = Field(None, max_length=20)


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
