"""
Schemas Pydantic para evaluación de fraude.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel


class FraudEvaluationRequest(BaseModel):
    """Request para evaluar riesgo de fraude en una transacción."""
    order_id: str
    user_id: str
    total_amount: float
    items_count: int
    high_risk_items_count: int
    shipping_city: str
    # Metadata adicional para features
    checkout_duration_seconds: Optional[float] = None
    is_new_shipping_address: Optional[bool] = None


class FraudEvaluationResponse(BaseModel):
    """Resultado de la evaluación de fraude."""
    order_id: str
    fraud_score: float
    decision: str  # APPROVED, REVIEW, BLOCKED
    risk_level: str  # LOW, MEDIUM, HIGH
    explanation: Optional[str] = None


class FraudLogResponse(BaseModel):
    """Respuesta de log de fraude (admin)."""
    id: str
    order_id: str
    fraud_score: float
    feature_vector: Optional[Dict[str, Any]] = None
    decision: str
    admin_notes: Optional[str] = None
    is_actual_fraud: bool
    detection_time_ms: Optional[float] = None
    evaluated_at: datetime

    model_config = {"from_attributes": True}


class FraudMetricsResponse(BaseModel):
    """Métricas del modelo de fraude."""
    total_evaluations: int
    detected_fraud_rate: float
    undetected_fraud_rate: float
    average_detection_time_ms: float

