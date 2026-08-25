"""
Registro central de todos los modelos ORM.
Importar este módulo asegura que SQLAlchemy registre todas las tablas.
"""

from app.models.user import User, UserRole
from app.models.product import Product, Category
from app.models.order import Order, OrderItem, OrderStatus
from app.models.fraud_log import FraudLog, FraudDecision
from app.models.service_order import ServiceOrder, ServiceStatus
from app.models.review import ProductReview

__all__ = [
    "User",
    "UserRole",
    "Product",
    "Category",
    "Order",
    "OrderItem",
    "OrderStatus",
    "FraudLog",
    "FraudDecision",
    "ServiceOrder",
    "ServiceStatus",
    "ProductReview",
]
