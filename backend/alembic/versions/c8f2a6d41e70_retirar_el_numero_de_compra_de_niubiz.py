"""Retirar el número de compra de Niubiz

La tienda cobra ahora con una única pasarela simulada, y las integraciones de
MercadoPago y Niubiz se retiraron del código. `orders.purchase_number` existía
solo porque Niubiz identifica cada cobro por un número de doce dígitos y los
pedidos de esta tienda se identifican por un UUID; sin Niubiz, la columna no
tiene a quién servir.

Se puede borrar sin perder nada: nunca llegó a haber un cobro por Niubiz en
producción, así que la columna está vacía en todas las filas. Lo que sí se queda
es `payment_gateway`, que ahora dice "simulado" y es lo que impide confundir un
pedido cobrado por la simulación con uno cobrado de verdad.

Revision ID: c8f2a6d41e70
Revises: b6e4d9a1c730
"""

from alembic import op
import sqlalchemy as sa

revision = "c8f2a6d41e70"
down_revision = "b6e4d9a1c730"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # El índice primero: en PostgreSQL caería solo con la columna, pero en
    # SQLite quedaría huérfano y la siguiente migración tropezaría con él.
    op.drop_index("uq_orders_purchase_number", table_name="orders")
    op.drop_column("orders", "purchase_number")


def downgrade() -> None:
    op.add_column(
        "orders", sa.Column("purchase_number", sa.String(length=12), nullable=True)
    )
    op.create_index(
        "uq_orders_purchase_number", "orders", ["purchase_number"], unique=True
    )
