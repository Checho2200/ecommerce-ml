"""
Endpoints de órdenes de compra.

Esta capa solo hace tres cosas: recibir la petición, delegar en
`app/services/order_service.py` y presentar el resultado. Las reglas del negocio
—reservar inventario, evaluar el fraude, decidir el estado, devolver stock,
plazos de cancelación— viven en el servicio, no aquí.

Los errores de negocio llegan como excepciones de `app/services/errors.py` y los
traduce a HTTP el manejador registrado en `app/main.py`, así que en este archivo
no hay `HTTPException` salvo para lo que sí es un asunto de la capa web: la
autorización de una petición y el rechazo de un webhook mal firmado.
"""

import math
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, inspect as sa_inspect, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin
from app.core.database import get_db
from app.models.order import Order, OrderItem
from app.models.user import User
from app.core.config import get_settings
from app.schemas.order import (
    PagoSimuladoRequest,
    PagoSimuladoResponse,
    OrderCreate,
    OrderItemResponse,
    OrderListResponse,
    OrderResponse,
    OrderStatusUpdate,
    OrderSummaryResponse,
)
from app.services import email_service, order_service

router = APIRouter(prefix="/orders", tags=["Órdenes"])


# ─────────────────────────────────────────────────────────────────────────────
# Presentación: del modelo de datos a la respuesta de la API
# ─────────────────────────────────────────────────────────────────────────────
def _nombre_del_producto(item: OrderItem, nombres: Optional[dict] = None) -> Optional[str]:
    """
    Nombre del producto de una línea, SIN provocar una consulta.

    Aquí estaba el fallo que dejaba el checkout en error 500: leer
    `item.product.name` sobre una línea recién creada dispara una carga
    perezosa, y una carga perezosa dentro de una función síncrona llamada desde
    código async revienta con MissingGreenlet. Al crear la orden los nombres ya
    se conocen —se consultaron para armar el pedido—, así que se pasan; y cuando
    la orden viene de una consulta, la relación ya está cargada. Si no se da
    ninguno de los dos casos se devuelve None en vez de ir a la base.
    """
    if nombres and item.product_id in nombres:
        return nombres[item.product_id]

    if "product" in sa_inspect(item).unloaded:
        return None

    return item.product.name if item.product else None


def _a_respuesta(
    orden: Order,
    nombres_de_productos: Optional[dict] = None,
) -> OrderResponse:
    """Convierte una orden y su evaluación de fraude en la respuesta pública."""
    return OrderResponse(
        id=orden.id,
        user_id=orden.user_id,
        total_amount=orden.total_amount,
        status=orden.status,
        shipping_address=orden.shipping_address,
        shipping_city=orden.shipping_city,
        items=[
            OrderItemResponse(
                id=linea.id,
                product_id=linea.product_id,
                product_name=_nombre_del_producto(linea, nombres_de_productos),
                quantity=linea.quantity,
                unit_price=linea.unit_price,
            )
            for linea in orden.items
        ],
        fraud_score=orden.fraud_log.fraud_score if orden.fraud_log else None,
        fraud_decision=orden.fraud_log.decision if orden.fraud_log else None,
        fraud_explanation=orden.fraud_log.explanation if orden.fraud_log else None,
        fraud_log_id=orden.fraud_log.id if orden.fraud_log else None,
        # `orden.user` viene cargado con la orden (lazy="selectin"), así que
        # esto no dispara una consulta por fila del listado.
        user_email=orden.user.email if orden.user else None,
        user_name=orden.user.full_name if orden.user else None,
        payment_id=orden.payment_id,
        payment_method=orden.payment_method,
        payment_gateway=orden.payment_gateway,
        # Si este servidor sabe cobrar con Niubiz. Depende de la configuración,
        # no de la orden, pero viaja aquí porque es justo donde el checkout lo
        # necesita: al recibir la orden recién creada tiene que decidir qué
        # botones de pago enseñar.
        card_last_four=orden.card_last_four,
        card_holder=orden.card_holder,
        paid_at=orden.paid_at,
        created_at=orden.created_at,
    )


async def _pagina(
    db: AsyncSession, consulta, page: int, per_page: int
) -> OrderListResponse:
    """Pagina una consulta de órdenes. Lo comparten el listado del panel y el del cliente."""
    total = (
        await db.execute(select(func.count()).select_from(consulta.subquery()))
    ).scalar() or 0

    resultado = await db.execute(
        consulta.order_by(Order.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )

    return OrderListResponse(
        items=[_a_respuesta(orden) for orden in resultado.scalars().all()],
        total=total,
        page=page,
        pages=math.ceil(total / per_page) if total > 0 else 1,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────
@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    data: OrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Crea una orden de compra: reserva inventario, la evalúa y genera el cobro."""
    creado = await order_service.crear_pedido(db, current_user, data)
    return _a_respuesta(creado.orden, creado.nombres_de_productos)


@router.get("", response_model=OrderListResponse)
async def list_orders(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=50),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Lista todas las órdenes con filtros (solo admin)."""
    consulta = select(Order)
    if status_filter:
        consulta = consulta.where(Order.status == status_filter)
    return await _pagina(db, consulta, page, per_page)


@router.get("/summary", response_model=OrderSummaryResponse)
async def orders_summary(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """
    Cuántos pedidos hay en cada estado y cuánto suman (solo admin).

    Va declarado antes que `/{order_id}` a propósito: FastAPI resuelve las
    rutas en orden y, puesto después, "summary" se leería como un id de orden.
    """
    filas = (
        await db.execute(
            select(Order.status, func.count(Order.id), func.sum(Order.total_amount))
            .group_by(Order.status)
        )
    ).all()

    por_estado: dict[str, int] = {}
    total = 0
    facturado = 0.0
    for estado, cuantos, suma in filas:
        clave = getattr(estado, "value", str(estado))
        por_estado[clave] = cuantos
        total += cuantos
        # Solo cuenta lo que se cobró: un pedido pendiente todavía no es venta,
        # y uno rechazado no lo será nunca.
        if clave in ("APPROVED", "COMPLETED"):
            facturado += float(suma or 0.0)

    return OrderSummaryResponse(
        total=total,
        by_status=por_estado,
        revenue=round(facturado, 2),
        awaiting_review=por_estado.get("FRAUD_REVIEW", 0),
    )


@router.get("/my-orders", response_model=OrderListResponse)
async def list_my_orders(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista las órdenes del usuario autenticado."""
    consulta = select(Order).where(Order.user_id == current_user.id)
    return await _pagina(db, consulta, page, per_page)


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Detalle de una orden. El admin ve todas; el cliente, solo las suyas."""
    orden = await order_service.obtener_pedido(db, order_id)

    if current_user.role != "ADMIN" and orden.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para ver esta orden",
        )

    return _a_respuesta(orden)


@router.post("/{order_id}/pago-simulado", response_model=PagoSimuladoResponse)
async def pagar_simulado(
    order_id: str,
    datos: PagoSimuladoRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Cobra un pedido con la pasarela simulada.

    No se mueve dinero y el sistema no lo esconde: la orden queda marcada con
    `payment_gateway = "simulado"` y `/health` informa de que la tienda está en
    este modo.

    Del número de tarjeta que llega aquí solo sobreviven los cuatro últimos
    dígitos, que son los que se guardan. El resto se usa para validar y se
    descarta; no se escribe en la orden ni en ningún log.
    """
    orden = await order_service.obtener_pedido(db, order_id)

    if orden.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para pagar esta orden",
        )

    aplicado, cobro = await order_service.confirmar_pago_simulado(
        db,
        order_id,
        numero=datos.numero,
        mes=datos.mes,
        anio=datos.anio,
        cvv=datos.cvv,
        titular=datos.titular,
    )

    # El aviso al cliente va en segundo plano y sin poder fallar, igual que con
    # las pasarelas reales: el pedido ya está resuelto y guardado.
    if aplicado.estado == "completada" and aplicado.orden is not None and aplicado.orden.user is not None:
        background_tasks.add_task(
            email_service.enviar_confirmacion_de_pedido,
            aplicado.orden.user.email,
            aplicado.orden.user.full_name,
            aplicado.orden.id,
            aplicado.orden.total_amount,
        )

    return PagoSimuladoResponse(
        aprobado=cobro.aprobado,
        estado_del_pedido=aplicado.estado,
        motivo=cobro.motivo,
        codigo=cobro.codigo,
        # La referencia sale de la orden y no de la respuesta del cobro: es la
        # que quedó guardada, así que el comprobante enseña exactamente lo mismo
        # que el panel de administración.
        referencia=aplicado.orden.payment_id if aplicado.orden else None,
    )


@router.patch("/{order_id}/release", response_model=OrderResponse)
async def release_order(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """
    Deja seguir una orden retenida por el modelo (solo admin).

    No es lo mismo que cambiarle el estado a mano: una orden en revisión que ya
    estaba pagada se da por buena, y una que nunca llegó a pagarse vuelve a
    PENDING con el plazo de caducidad reiniciado, para que el cliente pueda
    pagarla desde sus compras.
    """
    orden = await order_service.liberar_de_revision(db, order_id)
    return _a_respuesta(orden)


@router.patch("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: str,
    data: OrderStatusUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Cambia el estado de una orden (solo admin)."""
    orden = await order_service.cambiar_estado(db, order_id, data.status)
    return _a_respuesta(orden)


@router.patch("/my-orders/{order_id}/cancel", response_model=OrderResponse)
async def cancel_my_order(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancela una orden propia, si sigue pendiente y dentro del plazo."""
    orden = await order_service.cancelar_pedido_del_cliente(db, current_user, order_id)
    return _a_respuesta(orden)
