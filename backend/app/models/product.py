"""
Modelos de Producto y Categoría.
Las categorías incluyen un flag is_high_risk para marcar
productos de alto valor (GPUs, CPUs) relevantes para detección de fraude.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, DateTime, Integer, Float, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    is_high_risk: Mapped[bool] = mapped_column(Boolean, default=False)
    image_url: Mapped[str] = mapped_column(String(500), nullable=True)

    # Jerarquía de dos niveles: una categoría raíz (parent_id nulo) agrupa
    # subcategorías. Así "Memorias RAM" contiene "DDR3", "DDR4" y "DDR5", y
    # "Procesadores" contiene las líneas de Intel y AMD. Es la estructura
    # habitual de una tienda de cómputo y la que permite filtrar fino.
    parent_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("categories.id"), nullable=True, index=True
    )

    # Relationships
    products = relationship("Product", back_populates="category", lazy="selectin")
    # remote_side apunta al lado "uno" de la auto-referencia: el padre.
    parent = relationship(
        "Category", remote_side=[id], back_populates="children", lazy="selectin"
    )
    children = relationship(
        "Category", back_populates="parent", lazy="selectin", order_by="Category.name"
    )

    def __repr__(self) -> str:
        return f"<Category {self.name} (high_risk={self.is_high_risk})>"


class Product(Base):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    discount_price: Mapped[float] = mapped_column(Float, nullable=True)
    stock: Mapped[int] = mapped_column(Integer, default=0)
    image_url: Mapped[str] = mapped_column(String(500), nullable=True)
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("categories.id"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    category = relationship("Category", back_populates="products", lazy="selectin")
    order_items = relationship("OrderItem", back_populates="product", lazy="selectin")
    reviews = relationship("ProductReview", back_populates="product", lazy="selectin")

    @property
    def precio_efectivo(self) -> float:
        """
        Lo que el cliente paga de verdad.

        `price` es el precio de lista y `discount_price` el de oferta, y hasta
        ahora cada parte del sistema decidía por su cuenta cuál mirar: el
        catálogo enseñaba el de oferta y tachaba el otro, pero el carrito, el
        pedido y el cobro usaban `price`. La tienda anunciaba un precio y
        cobraba otro más alto.

        Que exista este único sitio es lo que impide que vuelva a pasar.
        Coincide a propósito con el `coalesce(discount_price, price)` que ya
        usaba el listado del catálogo para ordenar por precio.
        """
        return self.discount_price if self.discount_price is not None else self.price

    def __repr__(self) -> str:
        return f"<Product {self.name} - S/{self.precio_efectivo}>"
