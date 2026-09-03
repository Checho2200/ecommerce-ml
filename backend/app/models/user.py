"""
Modelo de Usuario con roles (CLIENTE / ADMIN).
"""

import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import String, Boolean, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class UserRole(str, PyEnum):
    CLIENTE = "CLIENTE"
    ADMIN = "ADMIN"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=True)
    role: Mapped[str] = mapped_column(
        Enum(UserRole), default=UserRole.CLIENTE, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    #
    # Se cargan bajo demanda (lazy="select"), no de forma anticipada. El usuario
    # se lee en CADA petición autenticada para validar el token; con selectin,
    # ese único SELECT arrastraba otros tres —pedidos, órdenes de servicio y
    # reseñas del usuario— que ningún endpoint llega a usar. Contra PostgreSQL
    # en Neon, donde cada viaje a la base cuesta cientos de milisegundos, eran
    # cuatro consultas por petición en lugar de una. Quien de verdad necesite
    # estas colecciones puede pedirlas con selectinload() en su propia consulta.
    orders = relationship("Order", back_populates="user")
    service_orders = relationship("ServiceOrder", back_populates="user")
    reviews = relationship("ProductReview", back_populates="user")

    def __repr__(self) -> str:
        return f"<User {self.email} ({self.role})>"
