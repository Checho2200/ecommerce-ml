"""Cuándo una orden pasó a ser pagable

Añade `orders.payable_since`. El plazo que caduca las órdenes sin pagar se
contaba desde `created_at`, y eso cancelaba precisamente las que un
administrador acababa de liberar de la revisión antifraude: una orden retenida
tres horas nacía ya vencida en el momento de aprobarse.

La columna es nula en las órdenes que nunca fueron pagables (rechazadas, o
todavía en revisión). Para las que ya existen se rellena con `created_at`, que
es exactamente lo que la lógica anterior asumía, así que la migración no cambia
el comportamiento de ninguna orden actual.

Revision ID: f1a4c8b32e50
Revises: e3c7a1f9d240
"""

from alembic import op
import sqlalchemy as sa

revision = "f1a4c8b32e50"
down_revision = "e3c7a1f9d240"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "orders", sa.Column("payable_since", sa.DateTime(timezone=True), nullable=True)
    )
    # Las órdenes que ya estaban esperando pago conservan su plazo original.
    op.execute(
        "UPDATE orders SET payable_since = created_at WHERE status = 'PENDING'"
    )


def downgrade() -> None:
    op.drop_column("orders", "payable_since")
