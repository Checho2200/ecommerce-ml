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
    # Cuánto empujó cada variable el puntaje, en escala logit: positivo hacia
    # fraude, negativo hacia compra legítima.
    contributions: Optional[Dict[str, float]] = None


class FraudLabelRequest(BaseModel):
    """Lo que un administrador dice que realmente pasó con un pedido."""
    is_fraud: bool


class FraudLogResponse(BaseModel):
    """Respuesta de log de fraude (admin)."""
    id: str
    order_id: str
    fraud_score: float
    feature_vector: Optional[Dict[str, Any]] = None
    contributions: Optional[Dict[str, float]] = None
    decision: str
    risk_level: Optional[str] = None
    explanation: Optional[str] = None
    admin_notes: Optional[str] = None
    is_actual_fraud: bool
    # Nulo mientras nadie lo haya revisado: es lo que separa "legítimo
    # confirmado" de "todavía sin mirar".
    reviewed_at: Optional[datetime] = None
    detection_time_ms: Optional[float] = None
    evaluated_at: datetime

    model_config = {"from_attributes": True}


class FraudMetricsResponse(BaseModel):
    """
    Métricas del modelo de fraude, medidas sobre los pedidos ya revisados.

    Los porcentajes van de 0 a 100. `precision` y `recall` solo tienen sentido
    cuando hay pedidos etiquetados de las dos clases; con `reviewed_count` en
    cero, todo lo demás es cero.
    """
    total_evaluations: int
    detected_fraud_rate: float
    undetected_fraud_rate: float
    average_detection_time_ms: float

    # Matriz de confusión sobre lo revisado
    reviewed_count: int = 0
    true_positives: int = 0
    false_positives: int = 0
    true_negatives: int = 0
    false_negatives: int = 0

    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0

    # En soles: lo que se evitó perder, lo que se perdió igual y la ganancia
    # que se dejó de hacer al frenar compras buenas.
    loss_prevented: float = 0.0
    loss_absorbed: float = 0.0
    revenue_lost: float = 0.0

