"""
Lógica de negocio de los pedidos.

Aquí vive lo que la tienda *hace* con un pedido: reservar inventario, evaluarlo
con el modelo de fraude, decidir su estado, cobrarlo, caducarlo, cancelarlo y
devolver el stock. Nada de esto sabe qué es una petición HTTP.

Por qué está separado del router. `app/api/v1/orders.py` tenía casi seiscientas
líneas donde convivían la validación de la petición, las reglas del negocio, las
consultas a la base y el armado de la respuesta. Eso hace que:

- probar una regla exija levantar la aplicación entera;
- la misma regla se repita —o se olvide— cuando hace falta desde otro sitio
  (un script de mantenimiento, una tarea en segundo plano, el webhook);
- cualquier cambio en la API arrastre la lógica de negocio consigo.

Con la lógica aquí, el router queda como debe: recibe, delega y responde. Los
errores se comunican con las excepciones de `app/services/errors.py`, que la
capa de la API traduce a códigos HTTP.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.fraud_log import FraudLog
from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.models.user import User
from app.schemas.order import OrderCreate
from app.services.errors import OperacionNoPermitida, RecursoNoEncontrado
from app.services.fraud_service import fraud_service
from app.services.payment_service import payment_service

# El stock se descuenta al crear la orden y se devuelve al pasar a uno de estos
# estados. Tenerlos en un conjunto evita el fallo de devolverlo dos veces: una
# orden creada como REJECTED por el modelo de fraude ya recuperó su inventario.
STOCK_LIBERADO = {OrderStatus.CANCELLED, OrderStatus.REJECTED}

# Cuánto aguanta una orden sin pagar antes de soltar su inventario. Se aplica de
# forma perezosa, cuando el propio cliente vuelve a comprar, porque el plan
# gratuito de Render no tiene dónde ejecutar una tarea programada.
PENDIENTE_CADUCA_EN = timedelta(hours=2)

# Plazo durante el cual el cliente puede cancelar su propio pedido.
PLAZO_DE_CANCELACION = timedelta(hours=1)

# Cuánto se supone que tardó el checkout cuando el frontend no lo informa. Es la
# mediana aproximada de una compra normal: un valor neutro para el modelo.
DURACION_DE_CHECKOUT_POR_DEFECTO = 120.0


# ─────────────────────────────────────────────────────────────────────────────
# Utilidades de dominio
# ─────────────────────────────────────────────────────────────────────────────
def en_utc(momento: datetime) -> datetime:
    """
    Devuelve la fecha con zona horaria, asumiendo UTC si no la trae.

    PostgreSQL guarda la zona y la devuelve; SQLite no, así que la misma columna
    vuelve con zona en producción y sin ella en desarrollo y en las pruebas.
    Restar una fecha con zona de otra sin ella revienta con TypeError, y eso
    convertía en error 500 la cancelación de un pedido.
    """
    if momento.tzinfo is None:
        return momento.replace(tzinfo=timezone.utc)
    return momento


@dataclass
class ArticulosReservados:
    """Lo que quedó apartado del inventario para un pedido."""

    lineas: list[OrderItem]
    total: float
    nombres: dict[str, str]
    articulos_de_alto_riesgo: int


@dataclass
class PedidoCreado:
    """Un pedido recién creado y lo que hace falta para presentarlo."""

    orden: Order
    nombres_de_productos: dict[str, str]
    url_de_pago: Optional[str] = None
    evaluacion: object = field(default=None, repr=False)


# ─────────────────────────────────────────────────────────────────────────────
# Inventario
# ─────────────────────────────────────────────────────────────────────────────
async def devolver_stock(db: AsyncSession, orden: Order) -> None:
    """Devuelve al inventario las unidades que la orden tenía reservadas."""
    for linea in orden.items:
        resultado = await db.execute(select(Product).where(Product.id == linea.product_id))
        producto = resultado.scalar_one_or_none()
        if producto:
            producto.stock += linea.quantity


async def caducar_pendientes(db: AsyncSession, user_id: str) -> None:
    """
    Cierra las órdenes que este cliente dejó a medias y devuelve su stock.

    Quien abandona el checkout de MercadoPago deja una orden en PENDING que
    retiene unidades. Como el carrito ya no se vacía hasta que el pago se
    confirma, al reintentar la compra se reservaría dos veces el mismo producto;
    esto lo evita.
    """
    limite = datetime.now(timezone.utc) - PENDIENTE_CADUCA_EN
    resultado = await db.execute(
        select(Order).where(
            Order.user_id == user_id,
            Order.status == OrderStatus.PENDING,
            # Desde que se pudo pagar, no desde que se creó: una orden que
            # estuvo retenida en revisión y se liberó hace un minuto no lleva
            # dos horas esperando pago aunque se creara ayer. `coalesce` cubre
            # las órdenes anteriores a esta columna.
            func.coalesce(Order.payable_since, Order.created_at) < limite,
        )
    )

    for orden in resultado.scalars().all():
        await devolver_stock(db, orden)
        orden.status = OrderStatus.CANCELLED
        print(f"Order {orden.id} caducada por falta de pago; stock devuelto.")

    await db.flush()


async def _reservar_articulos(db: AsyncSession, datos: OrderCreate) -> ArticulosReservados:
    """
    Aparta del inventario lo que pide el cliente y calcula el total.

    Los precios salen de la base, nunca de lo que mande el navegador: si no, un
    cliente podría comprar una tarjeta de video al precio que él escriba.
    """
    total = 0.0
    lineas: list[OrderItem] = []
    # El checkout de MercadoPago muestra el título de cada artículo, así que
    # hace falta el nombre del producto y no su identificador.
    nombres: dict[str, str] = {}
    articulos_de_alto_riesgo = 0

    for pedido_de_linea in datos.items:
        resultado = await db.execute(
            select(Product)
            .options(selectinload(Product.category))
            .where(Product.id == pedido_de_linea.product_id)
        )
        producto = resultado.scalar_one_or_none()

        if not producto or not producto.is_active:
            raise RecursoNoEncontrado(
                f"Producto {pedido_de_linea.product_id} no encontrado o no disponible"
            )

        if producto.stock < pedido_de_linea.quantity:
            raise OperacionNoPermitida(
                f"Stock insuficiente para {producto.name}. "
                f"Disponible: {producto.stock}"
            )

        if producto.category and getattr(producto.category, "is_high_risk", False):
            articulos_de_alto_riesgo += pedido_de_linea.quantity

        producto.stock -= pedido_de_linea.quantity
        total += producto.price * pedido_de_linea.quantity

        nombres[producto.id] = producto.name
        lineas.append(
            OrderItem(
                product_id=producto.id,
                quantity=pedido_de_linea.quantity,
                unit_price=producto.price,
            )
        )

    return ArticulosReservados(lineas, total, nombres, articulos_de_alto_riesgo)


async def _es_direccion_nueva(db: AsyncSession, user_id: str, direccion: str) -> int:
    """1 si el cliente nunca antes envió a esa dirección. Es una de las variables del modelo."""
    resultado = await db.execute(
        select(Order)
        .where(Order.user_id == user_id, Order.shipping_address == direccion)
        .limit(1)
    )
    return 0 if resultado.scalar_one_or_none() else 1


# ─────────────────────────────────────────────────────────────────────────────
# Creación de pedidos
# ─────────────────────────────────────────────────────────────────────────────
def _estado_segun_la_decision(decision: str) -> OrderStatus:
    return {
        "BLOCKED": OrderStatus.REJECTED,
        "REVIEW": OrderStatus.FRAUD_REVIEW,
    }.get(decision, OrderStatus.PENDING)


async def crear_pedido(db: AsyncSession, cliente: User, datos: OrderCreate) -> PedidoCreado:
    """
    Crea un pedido completo: reserva, evaluación de fraude, estado y cobro.

    El orden importa. Primero se reserva el inventario —así dos compras
    simultáneas del último artículo no lo venden dos veces—, después se evalúa,
    y si el modelo bloquea la compra se devuelve lo reservado en el acto.
    """
    await caducar_pendientes(db, cliente.id)

    reserva = await _reservar_articulos(db, datos)
    direccion_nueva = await _es_direccion_nueva(db, cliente.id, datos.shipping_address)
    duracion = datos.checkout_duration_seconds or DURACION_DE_CHECKOUT_POR_DEFECTO

    evaluacion = fraud_service.evaluar(
        total_amount=float(reserva.total),
        high_risk_items_count=reserva.articulos_de_alto_riesgo,
        checkout_duration_seconds=duracion,
        is_new_shipping_address=direccion_nueva,
    )

    estado = _estado_segun_la_decision(evaluacion.decision)
    if estado == OrderStatus.REJECTED:
        # La compra no llega a existir para el inventario: lo apartado vuelve.
        for linea in reserva.lineas:
            resultado = await db.execute(
                select(Product).where(Product.id == linea.product_id)
            )
            producto = resultado.scalar_one_or_none()
            if producto:
                producto.stock += linea.quantity

    orden = Order(
        user_id=cliente.id,
        total_amount=round(reserva.total, 2),
        status=estado,
        shipping_address=datos.shipping_address,
        shipping_city=datos.shipping_city,
    )
    db.add(orden)
    await db.flush()

    db.add(
        FraudLog(
            order_id=orden.id,
            fraud_score=evaluacion.puntaje,
            decision=evaluacion.decision,
            risk_level=evaluacion.nivel_de_riesgo,
            explanation=evaluacion.explicacion,
            detection_time_ms=evaluacion.milisegundos,
            # Cuánto empujó cada variable el puntaje de ESTE pedido: es lo que
            # convierte la decisión en algo auditable.
            contributions=evaluacion.aportes,
            # Y sin esto el reentrenamiento con datos reales no tendría
            # variables que leer: ml/dataset.py las saca de esta columna.
            feature_vector={
                "total_amount": float(reserva.total),
                "high_risk_items_count": int(reserva.articulos_de_alto_riesgo),
                "checkout_duration_seconds": float(duracion),
                "is_new_shipping_address": int(direccion_nueva),
            },
        )
    )

    for linea in reserva.lineas:
        linea.order_id = orden.id
        db.add(linea)

    await db.flush()
    await db.refresh(orden)

    url_de_pago = None
    if orden.status == OrderStatus.PENDING:
        orden.payable_since = orden.created_at
        url_de_pago = _generar_cobro(orden, reserva, cliente.email)

    return PedidoCreado(orden, reserva.nombres, url_de_pago, evaluacion)


def _generar_cobro(orden: Order, reserva: ArticulosReservados, correo: str) -> Optional[str]:
    """
    Pide a MercadoPago el enlace de pago.

    Si la pasarela falla, el pedido igual se devuelve: ya está creado y con su
    inventario reservado, y el cliente puede reintentar el pago. Tumbar la
    compra entera por una caída de la pasarela sería peor.
    """
    articulos = [
        {
            "title": reserva.nombres.get(linea.product_id, "Producto"),
            "quantity": linea.quantity,
            "unit_price": linea.unit_price,
        }
        for linea in reserva.lineas
    ]

    try:
        return payment_service.create_preference(
            order_id=orden.id, items=articulos, payer_email=correo
        )
    except Exception as exc:  # noqa: BLE001 - el pedido no depende de esto
        print(f"Error creating MP preference: {exc}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Cambios de estado
# ─────────────────────────────────────────────────────────────────────────────
async def obtener_pedido(db: AsyncSession, orden_id: str) -> Order:
    resultado = await db.execute(select(Order).where(Order.id == orden_id))
    orden = resultado.scalar_one_or_none()
    if not orden:
        raise RecursoNoEncontrado("Orden no encontrada")
    return orden


async def cambiar_estado(db: AsyncSession, orden_id: str, nuevo_estado: str) -> Order:
    """
    Cambia el estado de un pedido (operación de administración).

    Si el estado nuevo libera inventario y el anterior no lo había liberado, el
    stock vuelve. Antes esto solo cambiaba la etiqueta: cancelar un pedido desde
    el panel dejaba el stock reservado para siempre, al revés que la cancelación
    del cliente, que sí lo devolvía.
    """
    if nuevo_estado not in [estado.value for estado in OrderStatus]:
        raise OperacionNoPermitida(f"Estado inválido: {nuevo_estado}")

    orden = await obtener_pedido(db, orden_id)

    if nuevo_estado in STOCK_LIBERADO and orden.status not in STOCK_LIBERADO:
        await devolver_stock(db, orden)

    orden.status = nuevo_estado
    await db.flush()
    await db.refresh(orden)
    return orden


async def liberar_de_revision(db: AsyncSession, orden_id: str) -> tuple[Order, Optional[str]]:
    """
    Deja seguir una orden que el modelo había retenido.

    No basta con cambiar la etiqueta a PENDING. Una orden retenida nunca llegó
    a tener enlace de pago —`crear_pedido` solo lo pide para las que aprueba el
    modelo—, así que sin generarlo aquí el cliente se quedaría con un pedido
    "pendiente" que no puede pagar por ningún sitio. Y el plazo de caducidad
    arranca ahora, no cuando se creó la orden.

    Devuelve la orden y la URL de pago, que puede ser nula si la pasarela falla:
    igual que al crear el pedido, una caída de MercadoPago no debe deshacer la
    decisión del administrador.
    """
    orden = await obtener_pedido(db, orden_id)

    if orden.status != OrderStatus.FRAUD_REVIEW:
        raise OperacionNoPermitida(
            "Solo se puede liberar una orden que esté en revisión antifraude"
        )

    orden.status = OrderStatus.PENDING
    orden.payable_since = datetime.now(timezone.utc)

    articulos = [
        {
            "title": (linea.product.name if linea.product else "Producto"),
            "quantity": linea.quantity,
            "unit_price": linea.unit_price,
        }
        for linea in orden.items
    ]

    url_de_pago = None
    try:
        url_de_pago = payment_service.create_preference(
            order_id=orden.id, items=articulos, payer_email=orden.user.email
        )
    except Exception as exc:  # noqa: BLE001 - la decisión no depende de esto
        print(f"Error creating MP preference al liberar {orden.id}: {exc}")

    await db.flush()
    await db.refresh(orden)
    return orden, url_de_pago


async def cancelar_pedido_del_cliente(db: AsyncSession, cliente: User, orden_id: str) -> Order:
    """Cancela un pedido propio, si sigue pendiente y dentro del plazo."""
    resultado = await db.execute(
        select(Order).where(Order.id == orden_id, Order.user_id == cliente.id)
    )
    orden = resultado.scalar_one_or_none()

    if not orden:
        raise RecursoNoEncontrado("Orden no encontrada")

    if orden.status != OrderStatus.PENDING:
        raise OperacionNoPermitida(
            "Solo se pueden cancelar órdenes en estado PENDING"
        )

    if datetime.now(timezone.utc) - en_utc(orden.created_at) > PLAZO_DE_CANCELACION:
        raise OperacionNoPermitida(
            "El periodo de cancelación (1 hora) ha expirado. "
            "Por favor, comunícate con soporte."
        )

    orden.status = OrderStatus.CANCELLED
    await devolver_stock(db, orden)

    await db.flush()
    await db.refresh(orden)
    return orden


# ─────────────────────────────────────────────────────────────────────────────
# Confirmación del pago
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class ResultadoDelPago:
    """Qué se hizo con la notificación de un pago."""

    estado: str  # "completada" | "cancelada" | "sin cambios" | "orden no encontrada"
    orden: Optional[Order] = None


async def registrar_resultado_del_pago(
    db: AsyncSession, referencia_externa: str, estado_en_mercadopago: str
) -> ResultadoDelPago:
    """
    Aplica al pedido lo que MercadoPago dice que pasó con su pago.

    Solo se toca un pedido que siga pendiente: las notificaciones se repiten y
    llegan desordenadas, y no se puede volver a cancelar —ni a devolver stock
    de— algo que ya se resolvió.
    """
    resultado = await db.execute(select(Order).where(Order.id == referencia_externa))
    orden = resultado.scalar_one_or_none()

    if not orden:
        return ResultadoDelPago("orden no encontrada")

    if orden.status != OrderStatus.PENDING:
        return ResultadoDelPago("sin cambios", orden)

    if estado_en_mercadopago == "approved":
        orden.status = OrderStatus.COMPLETED
        await db.commit()
        print(f"Order {orden.id} marcada como COMPLETED por el webhook.")
        return ResultadoDelPago("completada", orden)

    if estado_en_mercadopago in ("rejected", "cancelled"):
        # Sin esto un pago rechazado dejaba la orden en PENDING para siempre,
        # con su stock reservado y sin forma de cobrarla.
        orden.status = OrderStatus.CANCELLED
        await devolver_stock(db, orden)
        await db.commit()
        print(f"Order {orden.id} cancelada: MercadoPago devolvió '{estado_en_mercadopago}'.")
        return ResultadoDelPago("cancelada", orden)

    return ResultadoDelPago("sin cambios", orden)
