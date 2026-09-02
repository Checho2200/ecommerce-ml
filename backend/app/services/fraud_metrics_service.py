"""
Cómo se mide el modelo de fraude con los pedidos de la tienda.

Está separado del router por la misma razón que la lógica de pedidos: es
conocimiento del negocio —qué cuenta como acierto, qué cuesta cada error— y no
tiene nada que ver con HTTP. Además así se puede probar, y calcular desde un
script o un informe, sin levantar la API.

Una advertencia que acompaña siempre a estos números y que conviene repetir en
cualquier lectura: **un pedido bloqueado nunca llega a cobrarse**, así que nunca
tendrá un contracargo que lo confirme como fraude. Los aciertos más valiosos del
modelo son, por construcción, los más difíciles de etiquetar, y estas métricas
los subestiman.
"""

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fraud_log import FraudLog
from app.models.order import Order

# Proporción del precio que es ganancia. Sirve para poner en soles lo que cuesta
# bloquear una compra legítima: no se pierde el pedido entero, se pierde lo que
# se habría ganado con él. Es el mismo valor que usa ml/evaluacion.py.
MARGEN_BRUTO = 0.15

# Una decisión distinta de APPROVED es una alerta: el pedido no siguió su curso
# normal, sea porque se bloqueó o porque se mandó a revisión.
DECISIONES_DE_ALERTA = ("REVIEW", "BLOCKED")


@dataclass
class MetricasDelModelo:
    """Rendimiento del modelo sobre los pedidos que alguien revisó."""

    total_evaluaciones: int
    revisados: int
    verdaderos_positivos: int
    falsos_positivos: int
    verdaderos_negativos: int
    falsos_negativos: int
    precision: float
    exhaustividad: float
    f1: float
    perdida_evitada: float
    perdida_asumida: float
    venta_perdida: float
    tiempo_medio_ms: float


def _f1(precision: float, exhaustividad: float) -> float:
    if precision + exhaustividad == 0:
        return 0.0
    return 2 * precision * exhaustividad / (precision + exhaustividad)


async def calcular(db: AsyncSession) -> MetricasDelModelo:
    """
    Arma la matriz de confusión y su equivalente en dinero.

    Solo cuentan los pedidos revisados. Uno que nadie miró no dice nada del
    modelo, y meterlo entre los legítimos —que es lo que pasaba cuando el único
    dato era `is_actual_fraud=False`— inventaba aciertos que nadie comprobó.
    """
    total = (await db.execute(select(func.count(FraudLog.id)))).scalar() or 0
    tiempo_medio = float(
        (await db.execute(select(func.avg(FraudLog.detection_time_ms)))).scalar() or 0.0
    )

    # Un solo viaje a la base con todo lo que hace falta.
    revisados = (
        await db.execute(
            select(FraudLog.decision, FraudLog.is_actual_fraud, Order.total_amount)
            .join(Order, Order.id == FraudLog.order_id)
            .where(FraudLog.reviewed_at.is_not(None))
        )
    ).all()

    verdaderos_positivos = falsos_positivos = 0
    verdaderos_negativos = falsos_negativos = 0
    perdida_evitada = perdida_asumida = venta_perdida = 0.0

    for decision, es_fraude, monto in revisados:
        decision = getattr(decision, "value", decision)
        alerta = decision in DECISIONES_DE_ALERTA
        monto = float(monto or 0.0)

        if es_fraude and alerta:
            verdaderos_positivos += 1
            perdida_evitada += monto
        elif es_fraude:
            falsos_negativos += 1
            perdida_asumida += monto
        elif alerta:
            falsos_positivos += 1
            # Solo un bloqueo pierde la venta; una revisión que termina bien
            # deja pasar el pedido.
            if decision == "BLOCKED":
                venta_perdida += monto * MARGEN_BRUTO
        else:
            verdaderos_negativos += 1

    fraudes_reales = verdaderos_positivos + falsos_negativos
    alertas = verdaderos_positivos + falsos_positivos

    precision = verdaderos_positivos / alertas if alertas else 0.0
    exhaustividad = verdaderos_positivos / fraudes_reales if fraudes_reales else 0.0

    return MetricasDelModelo(
        total_evaluaciones=total,
        revisados=len(revisados),
        verdaderos_positivos=verdaderos_positivos,
        falsos_positivos=falsos_positivos,
        verdaderos_negativos=verdaderos_negativos,
        falsos_negativos=falsos_negativos,
        precision=precision,
        exhaustividad=exhaustividad,
        f1=_f1(precision, exhaustividad),
        perdida_evitada=perdida_evitada,
        perdida_asumida=perdida_asumida,
        venta_perdida=venta_perdida,
        tiempo_medio_ms=tiempo_medio,
    )
