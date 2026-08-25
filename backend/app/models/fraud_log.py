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
    admin_notes: Mapped[str] = mapped_column(Text, nullable=True)
    is_actual_fraud: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
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
