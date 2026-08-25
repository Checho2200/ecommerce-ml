"""
Schemas Pydantic para órdenes de servicio técnico.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class ServiceOrderCreate(BaseModel):
    """Registrar nueva orden de servicio técnico."""
    device_type: str = Field(..., min_length=2, max_length=100)
    brand: Optional[str] = Field(None, max_length=100)
    issue_description: str = Field(..., min_length=10)


class ServiceOrderUpdate(BaseModel):
    """Actualizar orden de servicio (admin)."""
    diagnosis: Optional[str] = None
    status: Optional[str] = None
    estimated_cost: Optional[float] = Field(None, ge=0)


class ServiceOrderResponse(BaseModel):
    """Respuesta de orden de servicio."""
    id: str
    user_id: str
    user_name: Optional[str] = None
    device_type: str
    brand: Optional[str] = None
    issue_description: str
    diagnosis: Optional[str] = None
    status: str
    estimated_cost: Optional[float] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ServiceOrderListResponse(BaseModel):
    """Respuesta paginada de órdenes de servicio."""
    items: List[ServiceOrderResponse]
    total: int
    page: int
    pages: int
