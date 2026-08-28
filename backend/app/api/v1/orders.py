"""
Gestión de órdenes de compra.
- Clientes: crear órdenes y ver sus propias órdenes.
- Admin: listar todas, ver detalle, cambiar estado.
"""

import math
from typing import Optional

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.models.fraud_log import FraudLog
from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.models.user import User
from app.schemas.order import (
    OrderCreate,
    OrderStatusUpdate,
    OrderResponse,
    OrderListResponse,
    OrderItemResponse,
)
from app.api.deps import get_current_user, require_admin
from sqlalchemy.orm import selectinload
from app.services.fraud_service import fraud_service
from app.services.payment_service import payment_service
from fastapi import Request

router = APIRouter(prefix="/orders", tags=["Órdenes"])

# El stock se descuenta al crear la orden y se devuelve al pasar a uno de estos
# estados. Tenerlos en un conjunto evita el fallo de devolverlo dos veces: una
# orden creada como REJECTED por el modelo de fraude ya recupero su inventario.
STOCK_LIBERADO = {OrderStatus.CANCELLED, OrderStatus.REJECTED}


def _leer_notificacion(query: dict, body: dict) -> tuple:
    """
    Saca (payment_id, es_de_pago) de una notificacion de MercadoPago.

    Hay dos formatos vivos: los webhooks actuales mandan "type" en la query y
    {"action", "data": {"id"}} en el cuerpo JSON, y el IPN antiguo manda solo
    "topic" e "id" en la query. Se aceptan los dos.
    """
    topic = query.get("type") or query.get("topic") or body.get("type") or ""
    action = query.get("action") or body.get("action") or ""
    payment_id = (
        query.get("data.id")
        or query.get("id")
        or (body.get("data") or {}).get("id")
    )

    es_de_pago = topic == "payment" or str(action).startswith("payment.")
    return payment_id, es_de_pago


async def _restore_stock(db: AsyncSession, order: Order) -> None:
    """Devuelve al inventario las unidades que la orden tenia reservadas."""
    for item in order.items:
        result = await db.execute(select(Product).where(Product.id == item.product_id))
        product = result.scalar_one_or_none()
        if product:
            product.stock += item.quantity


def _build_order_response(order: Order) -> OrderResponse:
    """Construye la respuesta de una orden con items y datos de fraude."""
    items = []
    for item in order.items:
        items.append(OrderItemResponse(
            id=item.id,
            product_id=item.product_id,
            product_name=item.product.name if item.product else None,
            quantity=item.quantity,
            unit_price=item.unit_price,
        ))

    return OrderResponse(
        id=order.id,
        user_id=order.user_id,
        total_amount=order.total_amount,
        status=order.status,
        shipping_address=order.shipping_address,
        shipping_city=order.shipping_city,
        items=items,
        fraud_score=order.fraud_log.fraud_score if order.fraud_log else None,
        fraud_decision=order.fraud_log.decision if order.fraud_log else None,
        fraud_explanation=order.fraud_log.explanation if order.fraud_log else None,
        fraud_log_id=order.fraud_log.id if order.fraud_log else None,
        payment_url=getattr(order, "payment_url", None),
        created_at=order.created_at,
    )


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    data: OrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Crear una nueva orden de compra.
    Calcula el total basado en precios actuales y valida stock.
    """
    total_amount = 0.0
    order_items = []
    # El checkout de MercadoPago muestra el titulo de cada item, asi que hace
    # falta el nombre del producto y no su UUID.
    product_names: dict = {}

    # Fraud Evaluation Variables
    high_risk_items_count = 0
    
    for item_data in data.items:
        # Obtener producto con su categoría
        result = await db.execute(
            select(Product).options(selectinload(Product.category)).where(Product.id == item_data.product_id)
        )
        product = result.scalar_one_or_none()

        if not product or not product.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Producto {item_data.product_id} no encontrado o no disponible",
            )

        if product.stock < item_data.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Stock insuficiente para {product.name}. Disponible: {product.stock}",
            )

        # Contar items de alto riesgo
        if product.category and getattr(product.category, "is_high_risk", False):
            high_risk_items_count += item_data.quantity

        # Reservar stock
        product.stock -= item_data.quantity
        subtotal = product.price * item_data.quantity
        total_amount += subtotal

        product_names[product.id] = product.name
        order_items.append(OrderItem(
            product_id=product.id,
            quantity=item_data.quantity,
            unit_price=product.price,
        ))

    # Determinar si la dirección es nueva
    past_order_result = await db.execute(
        select(Order).where(
            Order.user_id == current_user.id,
            Order.shipping_address == data.shipping_address
        ).limit(1)
    )
    is_new_shipping_address = 0 if past_order_result.scalar_one_or_none() else 1
    
    # Obtener duración del checkout
    checkout_duration = data.checkout_duration_seconds or 120.0
    
    # Evaluar fraude con LightGBM
    fraud_score, decision, risk_level, explanation, detection_time_ms = fraud_service.evaluate_transaction(
        total_amount=float(total_amount),
        high_risk_items_count=high_risk_items_count,
        checkout_duration_seconds=checkout_duration,
        is_new_shipping_address=is_new_shipping_address
    )
    
    # Asignar estado según decisión
    if decision == "BLOCKED":
        order_status = OrderStatus.REJECTED
        # Devolver el stock reservado ya que se bloqueó
        for item in order_items:
            result = await db.execute(select(Product).where(Product.id == item.product_id))
            p = result.scalar_one_or_none()
            if p:
                p.stock += item.quantity
    elif decision == "REVIEW":
        order_status = OrderStatus.FRAUD_REVIEW
    else:
        order_status = OrderStatus.PENDING

    # Crear orden
    order = Order(
        user_id=current_user.id,
        total_amount=round(total_amount, 2),
        status=order_status,
        shipping_address=data.shipping_address,
        shipping_city=data.shipping_city,
    )
    db.add(order)
    await db.flush()
    
    # Crear log de fraude
    fraud_log = FraudLog(
        order_id=order.id,
        fraud_score=fraud_score,
        decision=decision,
        risk_level=risk_level,
        explanation=explanation,
        detection_time_ms=detection_time_ms,
        # Sin esto el reentrenamiento con datos reales no tendría variables que
        # leer: ml/train.py saca las features de esta columna.
        feature_vector={
            "total_amount": float(total_amount),
            "high_risk_items_count": int(high_risk_items_count),
            "checkout_duration_seconds": float(checkout_duration),
            "is_new_shipping_address": int(is_new_shipping_address),
        },
    )
    db.add(fraud_log)

    # Asociar items
    for item in order_items:
        item.order_id = order.id
        db.add(item)

    await db.flush()
    await db.refresh(order)

    # Generate Payment URL if PENDING
    payment_url = None
    if order.status == OrderStatus.PENDING:
        mp_items = []
        for item in order_items:
            mp_items.append({
                "title": product_names.get(item.product_id, "Producto"),
                "quantity": item.quantity,
                "unit_price": item.unit_price
            })
            
        try:
            payment_url = payment_service.create_preference(
                order_id=order.id,
                items=mp_items,
                payer_email=current_user.email
            )
            # Temporarily attach to order object for the response builder
            order.payment_url = payment_url
        except Exception as e:
            print(f"Error creating MP preference: {e}")
            # If MP fails, we still return the order, but without payment_url
            pass

    return _build_order_response(order)


@router.get("", response_model=OrderListResponse)
async def list_orders(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=50),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Lista todas las órdenes con filtros (solo admin)."""
    query = select(Order)

    if status_filter:
        query = query.where(Order.status == status_filter)

    # Contar total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Paginar
    query = query.offset((page - 1) * per_page).limit(per_page)
    query = query.order_by(Order.created_at.desc())

    result = await db.execute(query)
    orders = result.scalars().all()

    return OrderListResponse(
        items=[_build_order_response(o) for o in orders],
        total=total,
        page=page,
        pages=math.ceil(total / per_page) if total > 0 else 1,
    )


@router.get("/my-orders", response_model=OrderListResponse)
async def list_my_orders(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista las órdenes del usuario autenticado."""
    query = select(Order).where(Order.user_id == current_user.id)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    query = query.offset((page - 1) * per_page).limit(per_page)
    query = query.order_by(Order.created_at.desc())

    result = await db.execute(query)
    orders = result.scalars().all()

    return OrderListResponse(
        items=[_build_order_response(o) for o in orders],
        total=total,
        page=page,
        pages=math.ceil(total / per_page) if total > 0 else 1,
    )


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtener detalle de una orden. Admin ve todas, cliente solo las suyas."""
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Orden no encontrada",
        )

    if not current_user.role == "ADMIN" and order.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para ver esta orden",
        )

    return _build_order_response(order)


@router.post("/webhook/mercadopago")
async def mercadopago_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Recibe notificaciones de MercadoPago cuando un pago es creado o actualizado.
    """
    # MercadoPago avisa de dos formas segun la version de la integracion: los
    # webhooks actuales mandan "type" en la query y {"action", "data": {"id"}}
    # en el cuerpo JSON, mientras que el IPN antiguo solo manda "topic" e "id".
    # Antes solo se miraban "action" y "topic" de la query, asi que una
    # notificacion moderna (type=payment, action=payment.updated) se descartaba
    # y el pedido se quedaba en PENDING aunque el pago estuviera aprobado.
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001 - la notificacion puede venir sin cuerpo
        body = {}

    payment_id, es_de_pago = _leer_notificacion(dict(request.query_params), body)

    if not payment_id or not es_de_pago:
        return {"status": "ignored"}

    try:
        # Verificar el estado real en MercadoPago
        payment_info = payment_service.verify_payment(payment_id)
        
        status_mp = payment_info.get("status")
        external_reference = payment_info.get("external_reference") # This is our order_id

        if not external_reference:
            return {"status": "no order reference"}

        # Find the order
        result = await db.execute(select(Order).where(Order.id == external_reference))
        order = result.scalar_one_or_none()

        if not order:
            return {"status": "order not found"}

        if order.status == OrderStatus.PENDING:
            if status_mp == "approved":
                order.status = OrderStatus.COMPLETED
                await db.commit()
                print(f"Order {order.id} marcada como COMPLETED por el webhook.")
            elif status_mp in ("rejected", "cancelled"):
                # Sin esto un pago rechazado dejaba la orden en PENDING para
                # siempre, con su stock reservado y sin forma de cobrarla.
                order.status = OrderStatus.CANCELLED
                await _restore_stock(db, order)
                await db.commit()
                print(f"Order {order.id} cancelada: MercadoPago devolvio '{status_mp}'.")
            
        return {"status": "success"}

    except Exception as e:
        print(f"Webhook error: {e}")
        # Return 200 anyway so MP doesn't keep retrying forever if it's a structural error
        # In a real app we might return 500 so they retry.
        return {"status": "error", "message": str(e)}



@router.patch("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: str,
    data: OrderStatusUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Cambiar el estado de una orden (solo admin)."""
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Orden no encontrada",
        )

    # Validar que el nuevo estado es válido
    try:
        new_status = OrderStatus(data.status)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Estado inválido. Valores válidos: {[s.value for s in OrderStatus]}",
        )

    # Antes esto solo cambiaba la etiqueta: cancelar o rechazar un pedido desde
    # el panel dejaba el stock reservado para siempre, al reves que la
    # cancelacion del cliente, que si lo devolvia.
    if new_status in STOCK_LIBERADO and order.status not in STOCK_LIBERADO:
        await _restore_stock(db, order)

    order.status = new_status
    await db.flush()
    await db.refresh(order)

    return _build_order_response(order)


@router.patch("/my-orders/{order_id}/cancel", response_model=OrderResponse)
async def cancel_my_order(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancelar una orden propia, permitido solo dentro de 1 hora y si está PENDING."""
    result = await db.execute(
        select(Order).where(Order.id == order_id, Order.user_id == current_user.id)
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Orden no encontrada",
        )

    if order.status != OrderStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se pueden cancelar órdenes en estado PENDING",
        )

    # Validar 1 hora de límite
    time_elapsed = datetime.now(timezone.utc) - order.created_at
    if time_elapsed > timedelta(hours=1):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El periodo de cancelación (1 hora) ha expirado. Por favor, comunícate con soporte.",
        )

    order.status = OrderStatus.CANCELLED
    await _restore_stock(db, order)

    await db.flush()
    await db.refresh(order)

    return _build_order_response(order)
