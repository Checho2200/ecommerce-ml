"""Etiquetado de revision y aportes por variable en fraud_logs

Dos columnas nuevas:

- `reviewed_at`: cuando un administrador reviso el pedido y lo etiqueto. Antes
  solo existia `is_actual_fraud`, un booleano que valia False tanto para "se
  reviso y era legitimo" como para "nadie lo ha mirado". Con esa ambiguedad no
  se podia calcular la precision del modelo, porque no habia forma de contar
  verdaderos negativos.
- `contributions`: cuanto empujo cada variable el puntaje de ese pedido, para
  poder explicar la decision.

Revision ID: c4f1a9e27b30
Revises: bda8925f7f8a
"""

from alembic import op
import sqlalchemy as sa


revision = "c4f1a9e27b30"
down_revision = "bda8925f7f8a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("fraud_logs", sa.Column("contributions", sa.JSON(), nullable=True))
    op.add_column(
        "fraud_logs",
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Los pedidos que ya estaban marcados como fraude real si fueron revisados
    # por alguien: se les pone una marca de tiempo para no perder ese trabajo.
    op.execute(
        "UPDATE fraud_logs SET reviewed_at = evaluated_at WHERE is_actual_fraud = true"
    )


def downgrade() -> None:
    op.drop_column("fraud_logs", "reviewed_at")
    op.drop_column("fraud_logs", "contributions")
