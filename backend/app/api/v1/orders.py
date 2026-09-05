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
from app.schemas.order import (
    OrderCreate,
    OrderItemResponse,
    OrderListResponse,
    OrderResponse,
    OrderStatusUpdate,
    OrderSummaryResponse,
)
from app.services import email_service, order_service, webhook_security
from app.services.payment_service import leer_notificacion, payment_service

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
    url_de_pago: Optional[str] = None,
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
        payment_url=url_de_pago,
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
    return _a_respuesta(creado.orden, creado.nombres_de_productos, creado.url_de_pago)


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


@router.post("/webhook/mercadopago")
async def mercadopago_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Recibe las notificaciones de pago de MercadoPago.

    Siempre responde 200 salvo cuando la firma no cuadra: si devolviera error
    ante cualquier problema propio, MercadoPago reintentaría la notificación
    indefinidamente.
    """
    try:
        cuerpo = await request.json()
    except Exception:  # noqa: BLE001 - la notificación puede venir sin cuerpo
        cuerpo = {}

    payment_id, es_de_pago = leer_notificacion(dict(request.query_params), cuerpo)

    if not payment_id or not es_de_pago:
        return {"status": "ignored"}

    # Este endpoint es público: su URL viaja en cada preferencia de pago. La
    # firma es lo único que distingue un aviso de MercadoPago de uno inventado.
    if not webhook_security.firma_valida(
        request.headers.get("x-signature"),
        request.headers.get("x-request-id"),
        payment_id,
    ):
        print("Webhook rechazado: la firma no coincide.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Firma invalida"
        )

    try:
        pago = payment_service.verify_payment(payment_id)
        referencia = pago.get("external_reference")

        if not referencia:
            return {"status": "no order reference"}

        resultado = await order_service.registrar_resultado_del_pago(
            db, referencia, pago.get("status")
        )

        if resultado.estado == "orden no encontrada":
            return {"status": "order not found"}

        # El aviso al cliente va en segundo plano y sin poder fallar: el cobro
        # ya está hecho y la orden guardada, así que un problema del servidor de
        # correo no puede afectar a la respuesta que espera MercadoPago.
        if resultado.estado == "completada" and resultado.orden.user is not None:
            background_tasks.add_task(
                email_service.enviar_confirmacion_de_pedido,
                resultado.orden.user.email,
                resultado.orden.user.full_name,
                resultado.orden.id,
                resultado.orden.total_amount,
            )

        return {"status": "success"}

    except Exception as exc:  # noqa: BLE001 - ver la nota del docstring
        print(f"Webhook error: {exc}")
        return {"status": "error", "message": str(exc)}


@router.patch("/{order_id}/release", response_model=OrderResponse)
async def release_order(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """
    Deja seguir una orden retenida por el modelo (solo admin).

    No es lo mismo que cambiarle el estado a mano: además de moverla a PENDING,
    le genera el enlace de pago que nunca tuvo y reinicia el plazo de
    caducidad. Sin eso el cliente se quedaba con un pedido aprobado que no
    podía pagar por ningún sitio.
    """
    orden, url_de_pago = await order_service.liberar_de_revision(db, order_id)
    return _a_respuesta(orden, url_de_pago=url_de_pago)


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
