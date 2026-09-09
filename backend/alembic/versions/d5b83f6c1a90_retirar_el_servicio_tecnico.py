"""Retirar el servicio tecnico

El modulo de ordenes de servicio tecnico —registrar un equipo a reparar y
seguir su diagnostico— se retira del sistema. No formaba parte de lo que la
tesis sostiene: el trabajo es sobre deteccion de fraude en el pago de una
tienda en linea, y las reparaciones no pasan por el checkout, no se evaluan con
el modelo y no aportan ningun dato a los indicadores.

Esta migracion borra la tabla y su tipo enumerado. `downgrade` la reconstruye
tal como estaba en el esquema inicial, asi que el paso es reversible en cuanto
al esquema; las filas que hubiera, no.

Revision ID: d5b83f6c1a90
Revises: a7d2e5c91b40
"""

import sqlalchemy as sa
from alembic import op

revision = "d5b83f6c1a90"
down_revision = "a7d2e5c91b40"
branch_labels = None
depends_on = None


ESTADOS = ("RECEIVED", "DIAGNOSING", "IN_PROGRESS", "COMPLETED", "DELIVERED")


def upgrade() -> None:
    conexion = op.get_bind()

    # Se comprueba antes de borrar en lugar de usar `if_exists`, que la version
    # de Alembic de este proyecto (1.13) todavia no acepta en `drop_table`. Una
    # base creada de cero con el modelo ya retirado no tiene esta tabla, y la
    # migracion tiene que pasar por encima sin fallar.
    if sa.inspect(conexion).has_table("service_orders"):
        op.drop_table("service_orders")

    # PostgreSQL conserva el tipo enumerado despues de borrar la tabla que lo
    # usaba; si se deja, un `downgrade` fallaria al intentar crearlo de nuevo.
    # En SQLite no existe como objeto aparte, de ahi la comprobacion.
    if conexion.dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS servicestatus")


def downgrade() -> None:
    op.create_table(
        "service_orders",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("device_type", sa.String(length=100), nullable=False),
        sa.Column("brand", sa.String(length=100), nullable=True),
        sa.Column("issue_description", sa.Text(), nullable=False),
        sa.Column("diagnosis", sa.Text(), nullable=True),
        sa.Column("status", sa.Enum(*ESTADOS, name="servicestatus"), nullable=False),
        sa.Column("estimated_cost", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
