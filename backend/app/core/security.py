"""
Módulo de seguridad: hashing de contraseñas y manejo de JWT.
"""

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import jwt, JWTError
import bcrypt

from app.core.config import get_settings

settings = get_settings()


# --- Password Hashing ---
def hash_password(password: str) -> str:
    """Genera hash bcrypt de la contraseña."""
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica contraseña contra hash almacenado."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


# --- JWT Tokens ---
def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Genera un JWT con payload personalizado.
    El payload incluye 'sub' (user_id) y 'role'.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decodifica y valida un JWT.
    Retorna el payload si es válido, None si ha expirado o es inválido.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


# --- Tokens de restablecimiento de contraseña ---
PROPOSITO_RESET = "password_reset"


def _huella_de_contrasena(hashed_password: str) -> str:
    """
    Huella corta del hash actual de la contraseña.

    Va dentro del token de restablecimiento para que el enlace deje de servir
    en cuanto la contraseña cambia. Sin esto un enlace usado seguiría siendo
    válido hasta caducar, y quien lo tuviera (por ejemplo, alguien con acceso
    al buzón) podría volver a entrar. Es una huella, no el hash: no permite
    reconstruir la contraseña.
    """
    return hashlib.sha256(hashed_password.encode("utf-8")).hexdigest()[:16]


def create_password_reset_token(user_id: str, hashed_password: str) -> str:
    """Genera el token de un solo uso que viaja en el enlace de recuperación."""
    expira = datetime.now(timezone.utc) + timedelta(
        minutes=settings.RESET_TOKEN_EXPIRE_MINUTES
    )
    return jwt.encode(
        {
            "sub": user_id,
            "purpose": PROPOSITO_RESET,
            "pwd": _huella_de_contrasena(hashed_password),
            "exp": expira,
        },
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def decode_password_reset_token(token: str) -> Optional[dict]:
    """
    Valida un token de restablecimiento y devuelve su payload.

    Devuelve None si caducó, si la firma no cuadra o si es un token de acceso
    normal: un JWT de sesión no debe servir para cambiar una contraseña.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None

    if payload.get("purpose") != PROPOSITO_RESET:
        return None

    return payload


def reset_token_sigue_vigente(payload: dict, hashed_password: str) -> bool:
    """Comprueba que la contraseña no haya cambiado desde que se pidió el enlace."""
    return payload.get("pwd") == _huella_de_contrasena(hashed_password)
