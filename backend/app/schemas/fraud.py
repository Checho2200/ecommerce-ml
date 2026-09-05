"""
Schemas Pydantic para evaluación de fraude.
"""

from datetime import date, datetime
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



class FraudHistoryPeriod(BaseModel):
    """
    Un período del historial: cuántas compras evaluó el modelo y qué decidió.

    "Pasaron" son las aprobadas, que siguieron su curso hasta el cobro; "no
    pasaron" son las retenidas —las que quedaron en revisión y las bloqueadas—,
    que nunca llegaron a la pasarela de pago.
    """

    # Fecha de inicio del período (el día, el lunes de la semana, o el día 1).
    period_start: date
    evaluations: int
    approved: int
    in_review: int
    blocked: int
    approved_amount: float
    held_amount: float
    average_score: float

    # Los tres indicadores de la tesis. Los dos primeros van nulos cuando el
    # período no tiene ningún fraude confirmado: un cero diría "no se detectó
    # nada" y lo cierto es que no hay con qué medirlo.
    reviewed: int = 0
    actual_frauds: int = 0
    detected_frauds: int = 0
    undetected_frauds: int = 0
    detection_rate: Optional[float] = None
    undetected_rate: Optional[float] = None
    average_detection_time_ms: float = 0.0


class FraudHistoryResponse(BaseModel):
    """El historial completo, más el total de la ventana consultada."""

    granularity: str
    periods: list[FraudHistoryPeriod]
    total_evaluations: int
    total_approved: int
    total_held: int

    # Los mismos indicadores sobre la ventana entera. Se calculan sumando los
    # casos y dividiendo una sola vez, no promediando las tasas de cada
    # período: el promedio de porcentajes le da el mismo peso a un mes con un
    # caso que a uno con cien.
    total_reviewed: int = 0
    total_actual_frauds: int = 0
    total_detected_frauds: int = 0
    total_undetected_frauds: int = 0
    detection_rate: Optional[float] = None
    undetected_rate: Optional[float] = None
    average_detection_time_ms: float = 0.0


class FraudModelInfo(BaseModel):
    """
    Con qué se publicó el modelo que está decidiendo ahora mismo.

    No son las métricas de la tienda —esas salen de `/fraud/metrics` y se
    mueven con cada revisión—, sino las que el entrenamiento midió sobre su
    partición de prueba antes de publicar. Sirven para responder la pregunta
    "¿el modelo que está corriendo es el bueno?" sin abrir el informe.
    """

    loaded: bool
    trained_at: Optional[str] = None
    data_source: Optional[str] = None
    approve_below: float
    block_above: float
    average_precision: Optional[float] = None
    roc_auc: Optional[float] = None
    # Los indicadores de la tesis, tal como quedaron al publicarse.
    detection_rate: Optional[float] = None
    detection_time_ms: Optional[float] = None

    # Con qué se reconstruye la aritmética de una decisión:
    # puntaje = sigmoide(base_value + suma de los aportes por variable).
    base_value: Optional[float] = None
    n_trees: Optional[int] = None
    features: list[str] = []
