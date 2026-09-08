"""Con qué tarjeta se pagó cada orden

Añade a `orders` el identificador del pago en MercadoPago, el medio empleado,
los cuatro últimos dígitos de la tarjeta, el nombre del titular y el momento
del cobro. El webhook ya recibía todo eso en la respuesta de la pasarela y lo
descartaba: solo miraba el estado.

Sirve para el seguimiento. Ante un contracargo, o ante una compra que el modelo
retuvo, hay que poder decir qué pago fue y con qué tarjeta sin salir del panel
a buscarlo en MercadoPago. Y el titular es el dato que delata el caso más
común de fraude con tarjeta robada: la cuenta es de una persona y la tarjeta
está a nombre de otra.

**Solo los cuatro últimos dígitos.** El número completo, el código de seguridad
y la caducidad no se piden, no se reciben y no se guardan: PCI-DSS permite
conservar los cuatro últimos precisamente porque no sirven para cobrar con
ellos. La tarjeta la maneja MercadoPago de principio a fin.

Todas las columnas son nulas: las órdenes que ya existen nunca tuvieron estos
datos, y las que no llegan a pagarse —rechazadas, en revisión, caducadas— no
los tendrán nunca.

Revision ID: a7d2e5c91b40
Revises: f1a4c8b32e50
"""

from alembic import op
import sqlalchemy as sa

revision = "a7d2e5c91b40"
down_revision = "f1a4c8b32e50"
branch_labels = None
depends_on = None


COLUMNAS = (
    ("payment_id", sa.String(length=50)),
    ("payment_method", sa.String(length=30)),
    ("card_last_four", sa.String(length=4)),
    ("card_holder", sa.String(length=150)),
    ("paid_at", sa.DateTime(timezone=True)),
)


def upgrade() -> None:
    for nombre, tipo in COLUMNAS:
        op.add_column("orders", sa.Column(nombre, tipo, nullable=True))


def downgrade() -> None:
    for nombre, _ in reversed(COLUMNAS):
        op.drop_column("orders", nombre)
