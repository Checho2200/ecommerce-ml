"""
Gestión de órdenes de servicio técnico.
- Clientes: crear y ver sus órdenes de servicio.
- Admin: listar todas, actualizar estado y diagnóstico.
"""

import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.models.service_order import ServiceOrder, ServiceStatus
from app.models.user import User
from app.schemas.service_order import (
    ServiceOrderCreate,
    ServiceOrderUpdate,
    ServiceOrderResponse,
    ServiceOrderListResponse,
)
from app.api.deps import get_current_user, require_admin

router = APIRouter(prefix="/service-orders", tags=["Servicio Técnico"])


def _build_service_response(service: ServiceOrder) -> ServiceOrderResponse:
    """Construye la respuesta de una orden de servicio."""
    return ServiceOrderResponse(
        id=service.id,
        user_id=service.user_id,
        user_name=service.user.full_name if service.user else None,
        device_type=service.device_type,
        brand=service.brand,
        issue_description=service.issue_description,
        diagnosis=service.diagnosis,
        status=service.status,
        estimated_cost=service.estimated_cost,
        created_at=service.created_at,
    )


@router.post("", response_model=ServiceOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_service_order(
    data: ServiceOrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Registrar nueva orden de servicio técnico."""
    service = ServiceOrder(
        user_id=current_user.id,
        device_type=data.device_type,
        brand=data.brand,
        issue_description=data.issue_description,
    )
    db.add(service)
    await db.flush()
    await db.refresh(service)

    return _build_service_response(service)


@router.get("", response_model=ServiceOrderListResponse)
async def list_service_orders(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=50),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Lista todas las órdenes de servicio (solo admin)."""
    query = select(ServiceOrder)

    if status_filter:
        query = query.where(ServiceOrder.status == status_filter)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    query = query.offset((page - 1) * per_page).limit(per_page)
    query = query.order_by(ServiceOrder.created_at.desc())

    result = await db.execute(query)
    services = result.scalars().all()

    return ServiceOrderListResponse(
        items=[_build_service_response(s) for s in services],
        total=total,
        page=page,
        pages=math.ceil(total / per_page) if total > 0 else 1,
    )


@router.get("/my-services", response_model=ServiceOrderListResponse)
async def list_my_service_orders(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista las órdenes de servicio del usuario autenticado."""
    query = select(ServiceOrder).where(ServiceOrder.user_id == current_user.id)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    query = query.offset((page - 1) * per_page).limit(per_page)
    query = query.order_by(ServiceOrder.created_at.desc())

    result = await db.execute(query)
    services = result.scalars().all()

    return ServiceOrderListResponse(
        items=[_build_service_response(s) for s in services],
        total=total,
        page=page,
        pages=math.ceil(total / per_page) if total > 0 else 1,
    )


@router.get("/{service_id}", response_model=ServiceOrderResponse)
async def get_service_order(
    service_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtener detalle de una orden de servicio."""
    result = await db.execute(
        select(ServiceOrder).where(ServiceOrder.id == service_id)
    )
    service = result.scalar_one_or_none()

    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Orden de servicio no encontrada",
        )

    if current_user.role != "ADMIN" and service.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permiso para ver esta orden de servicio",
        )

    return _build_service_response(service)


@router.patch("/{service_id}", response_model=ServiceOrderResponse)
async def update_service_order(
    service_id: str,
    data: ServiceOrderUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Actualizar una orden de servicio (solo admin)."""
    result = await db.execute(
        select(ServiceOrder).where(ServiceOrder.id == service_id)
    )
    service = result.scalar_one_or_none()

    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Orden de servicio no encontrada",
        )

    update_data = data.model_dump(exclude_unset=True)

    # Validar estado si se envía
    if "status" in update_data:
        try:
            update_data["status"] = ServiceStatus(update_data["status"])
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Estado inválido. Valores válidos: {[s.value for s in ServiceStatus]}",
            )

    for field, value in update_data.items():
        setattr(service, field, value)

    await db.flush()
    await db.refresh(service)

    return _build_service_response(service)
