"""
Modelo de registro de evaluación de fraude.
Almacena el score, las features utilizadas y la decisión tomada
para cada orden evaluada. Crucial para auditoría y reentrenamiento.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import String, DateTime, Float, ForeignKey, Enum, Text, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class FraudDecision(str, PyEnum):
    APPROVED = "APPROVED"
    REVIEW = "REVIEW"
    BLOCKED = "BLOCKED"


class FraudLog(Base):
    __tablename__ = "fraud_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    order_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("orders.id"), unique=True, nullable=False
    )
    fraud_score: Mapped[float] = mapped_column(Float, nullable=False)
    feature_vector: Mapped[dict] = mapped_column(JSON, nullable=True)
    decision: Mapped[str] = mapped_column(
        Enum(FraudDecision), nullable=False
    )
    # Nivel de riesgo (LOW / MEDIUM / HIGH) y explicación legible que acompañan
    # a la decisión. `orders.py` los devuelve en la respuesta del pedido.
    risk_level: Mapped[str] = mapped_column(String(10), nullable=True)
    explanation: Mapped[str] = mapped_column(Text, nullable=True)
    admin_notes: Mapped[str] = mapped_column(Text, nullable=True)
    # Aporte de cada variable al puntaje, calculado con los valores SHAP que
    # LightGBM produce de forma nativa. Es lo que permite decirle al
    # administrador POR QUE se tomo la decision, en vez de una frase generica.
    contributions: Mapped[dict] = mapped_column(JSON, nullable=True)
    is_actual_fraud: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    # Cuando un administrador reviso el pedido y lo etiqueto. Sin esta marca no
    # se puede distinguir "legitimo confirmado" de "todavia nadie lo miro", y
    # esa diferencia es justo la que hace falta para calcular la precision del
    # modelo: is_actual_fraud=False significaba las dos cosas a la vez.
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    detection_time_ms: Mapped[float] = mapped_column(
        Float, nullable=True
    )
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    order = relationship("Order", back_populates="fraud_log")

    def __repr__(self) -> str:
        return f"<FraudLog order={self.order_id[:8]} score={self.fraud_score} ({self.decision})>"
