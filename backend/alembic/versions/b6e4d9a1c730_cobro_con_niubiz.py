"""Cobro con Niubiz

Añade a `orders` las dos columnas que hacen falta para cobrar con la segunda
pasarela, sin tocar nada de lo que ya usaba MercadoPago.

`purchase_number` existe porque Niubiz identifica cada cobro por un número de
hasta doce dígitos y el identificador de las órdenes es un UUID. Se asigna la
primera vez que alguien elige pagar con Niubiz y se conserva, porque la clave de
sesión y la autorización tienen que llevar el mismo número.

`payment_gateway` dice con cuál de las dos pasarelas se cobró. Sin ella, un
`payment_id` suelto no indica en qué panel buscarlo, que es lo primero que hace
falta ante un contracargo.

Las dos son nulas en las órdenes que ya existen, y eso es exacto: ninguna pasó
por Niubiz. Las anteriores se dejan con `payment_gateway` nulo en lugar de
rellenarlas con "mercadopago" porque una orden sin pagar no se cobró por ningún
sitio; las que sí se pagaron se marcan, que de esas sí se sabe.

Revision ID: b6e4d9a1c730
Revises: d5b83f6c1a90
"""

from alembic import op
import sqlalchemy as sa

revision = "b6e4d9a1c730"
down_revision = "d5b83f6c1a90"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "orders", sa.Column("purchase_number", sa.String(length=12), nullable=True)
    )
    op.add_column(
        "orders", sa.Column("payment_gateway", sa.String(length=20), nullable=True)
    )
    # Único, pero sin exigir valor: dos cobros de Niubiz no pueden compartir
    # número, y las órdenes que nunca pasaron por Niubiz no tienen ninguno.
    #
    # Va como índice único y no como restricción de tabla porque SQLite —que es
    # la base con la que se trabaja en local— no sabe añadir una restricción a
    # una tabla que ya existe, y un índice sí. En PostgreSQL, que es lo que
    # corre en el despliegue, las dos formas son la misma cosa.
    op.create_index(
        "uq_orders_purchase_number", "orders", ["purchase_number"], unique=True
    )
    # Lo que ya estaba cobrado, lo cobró MercadoPago: era la única pasarela.
    op.execute(
        "UPDATE orders SET payment_gateway = 'mercadopago' WHERE payment_id IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_index("uq_orders_purchase_number", table_name="orders")
    op.drop_column("orders", "payment_gateway")
    op.drop_column("orders", "purchase_number")
