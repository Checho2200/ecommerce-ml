"""
Modelos de Orden de Compra y sus ítems.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import String, DateTime, Integer, Float, ForeignKey, Enum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class OrderStatus(str, PyEnum):
    PENDING = "PENDING"
    FRAUD_REVIEW = "FRAUD_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    total_amount: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(
        Enum(OrderStatus), default=OrderStatus.PENDING, nullable=False
    )
    shipping_address: Mapped[str] = mapped_column(Text, nullable=True)
    shipping_city: Mapped[str] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    # Desde cuándo el cliente puede pagar esta orden.
    #
    # Casi siempre coincide con `created_at`, pero no cuando el modelo la
    # retuvo: una orden que estuvo tres horas en revisión y se liberó recién
    # ahora lleva tres horas de existencia y cero de poder pagarse. El plazo de
    # caducidad se cuenta desde aquí, porque contarlo desde `created_at`
    # cancelaba justo las órdenes que un administrador acababa de aprobar.
    # Nula en las que nunca llegaron a ser pagables (rechazadas, en revisión).
    payable_since: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Con qué se pagó ──────────────────────────────────────────────────
    #
    # Lo rellena el webhook con lo que responde MercadoPago cuando el cobro se
    # aprueba. Sirve para el seguimiento: ante un contracargo hay que poder
    # decir qué pago fue, con qué tarjeta y a nombre de quién, sin entrar al
    # panel de la pasarela.
    #
    # Se guardan **los cuatro últimos dígitos y nada más**. El número completo,
    # el código de seguridad y la fecha de caducidad no se reciben, no se
    # guardan y no se registran en ningún log: PCI-DSS permite conservar los
    # cuatro últimos precisamente porque no sirven para cobrar, y guardar el
    # resto convertiría esta base en un objetivo que la tienda no tiene por qué
    # ser. La tarjeta la maneja MercadoPago de principio a fin.
    payment_id: Mapped[str] = mapped_column(String(50), nullable=True)
    payment_method: Mapped[str] = mapped_column(String(30), nullable=True)
    card_last_four: Mapped[str] = mapped_column(String(4), nullable=True)
    # El titular tal como lo devuelve la pasarela. Es el dato que delata el
    # caso clásico: la cuenta es de una persona y la tarjeta de otra.
    card_holder: Mapped[str] = mapped_column(String(150), nullable=True)
    paid_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    user = relationship("User", back_populates="orders", lazy="selectin")
    items = relationship("OrderItem", back_populates="order", lazy="selectin")
    fraud_log = relationship("FraudLog", back_populates="order", uselist=False, lazy="selectin")

    def __repr__(self) -> str:
        return f"<Order {self.id[:8]} - S/{self.total_amount} ({self.status})>"


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("orders.id"), nullable=False
    )
    product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("products.id"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)

    # Relationships
    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items", lazy="selectin")

    def __repr__(self) -> str:
        return f"<OrderItem {self.product_id[:8]} x{self.quantity}>"
