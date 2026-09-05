"""
Schemas Pydantic para órdenes de compra.
"""

from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


# --- OrderItem ---
class OrderItemCreate(BaseModel):
    """Item dentro de una orden."""
    product_id: str
    quantity: int = Field(..., gt=0)


class OrderItemResponse(BaseModel):
    """Respuesta de item de orden."""
    id: int
    product_id: str
    product_name: Optional[str] = None
    quantity: int
    unit_price: float

    model_config = {"from_attributes": True}


# --- Order ---
class OrderCreate(BaseModel):
    """Crear nueva orden de compra."""
    items: List[OrderItemCreate] = Field(..., min_length=1)
    shipping_address: str = Field(..., min_length=5)
    shipping_city: str = Field(..., min_length=2, max_length=100)
    checkout_duration_seconds: Optional[float] = None


class OrderStatusUpdate(BaseModel):
    """Actualizar estado de una orden (admin)."""
    status: str


class OrderResponse(BaseModel):
    """Respuesta de orden con items."""
    id: str
    user_id: str
    total_amount: float
    status: str
    shipping_address: Optional[str] = None
    shipping_city: Optional[str] = None
    items: List[OrderItemResponse] = []
    fraud_score: Optional[float] = None
    fraud_decision: Optional[str] = None
    fraud_explanation: Optional[str] = None
    fraud_log_id: Optional[str] = None
    payment_url: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class OrderListResponse(BaseModel):
    """Respuesta paginada de órdenes."""
    items: List[OrderResponse]
    total: int
    page: int
    pages: int


class OrderSummaryResponse(BaseModel):
    """
    Resumen de la tienda para el panel: cuántos pedidos hay en cada estado y
    cuánto dinero representan.

    Existe para que el panel no tenga que pedir la lista de órdenes una vez por
    estado solo para leer el `total` de cada respuesta. Es una consulta
    agrupada, no seis paginadas.
    """

    total: int
    # Estado del pedido -> cuántos hay. Solo aparecen los que existen.
    by_status: Dict[str, int]
    # Cobrado de verdad: pedidos aprobados o completados.
    revenue: float
    # Pedidos que el modelo dejó retenidos y esperan que alguien los mire.
    awaiting_review: int
