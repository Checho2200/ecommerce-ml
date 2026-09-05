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
from datetime import date, datetime, time, timedelta, timezone

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


# ─────────────────────────────────────────────────────────────────────────────
# Historial: las mismas decisiones, repartidas en el tiempo
# ─────────────────────────────────────────────────────────────────────────────
#
# `calcular` responde "cómo va el modelo"; esto responde "cómo ha ido". Son
# preguntas distintas: un promedio sobre toda la vida de la tienda esconde que
# los bloqueos se dispararon la semana pasada.

GRANULARIDADES = ("day", "week", "month", "year")

# Los cortes del historial son los del reloj de la tienda, no los de UTC. Con
# UTC, una compra de las ocho de la noche en Trujillo cae en el informe del día
# siguiente, y el "hoy" del panel empieza a las siete de la tarde. Perú no
# aplica horario de verano desde 1994, así que un desfase fijo es exacto y
# evita depender de la base de zonas horarias del sistema, que en Windows no
# viene instalada.
ZONA_DE_LA_TIENDA = timezone(timedelta(hours=-5), "America/Lima")

# Cuántos períodos devolver cuando nadie pide un número. Un trimestre de días,
# medio año de semanas o dos años de meses: en los tres casos, la ventana en la
# que todavía se distingue una tendencia de un accidente.
PERIODOS_POR_DEFECTO = {"day": 90, "week": 26, "month": 24, "year": 5}
PERIODOS_MAXIMOS = 366


@dataclass
class PeriodoDelHistorial:
    """Un día, una semana, un mes o un año de decisiones del modelo."""

    # Fecha de inicio del período, en ISO. La etiqueta legible la arma el panel,
    # que es quien sabe en qué idioma y con qué formato la va a enseñar.
    inicio: date
    evaluaciones: int
    aprobadas: int
    en_revision: int
    bloqueadas: int
    # Lo que se dejó pasar y lo que se frenó, en soles. Es la lectura que
    # entiende un gerente: cuánta plata pasó por cada rama de la decisión.
    monto_aprobado: float
    monto_retenido: float
    puntaje_medio: float

    # ── Los tres indicadores que mide la tesis ───────────────────────────────
    #
    # Los dos primeros solo tienen sentido sobre los pedidos que alguien revisó
    # y etiquetó: sin saber cuáles eran fraude de verdad no se puede decir
    # cuántos se detectaron. Por eso van en None —y no en cero— cuando el
    # período no tiene ningún fraude confirmado: un cero diría "no detectamos
    # nada", y lo cierto es "no hay con qué medirlo".
    revisados: int
    fraudes_reales: int
    fraudes_detectados: int
    fraudes_no_detectados: int
    tasa_de_deteccion: float | None
    tasa_de_no_deteccion: float | None
    # Éste sí se mide siempre: no necesita etiquetas, lo cronometra el propio
    # servicio en cada evaluación.
    tiempo_medio_ms: float


def _inicio_del_periodo(momento: datetime, granularidad: str) -> date:
    """Lleva un instante al comienzo de su día, su semana (lunes), su mes o su año."""
    dia = momento.astimezone(ZONA_DE_LA_TIENDA).date()
    if granularidad == "week":
        return dia - timedelta(days=dia.weekday())
    if granularidad == "month":
        return dia.replace(day=1)
    if granularidad == "year":
        return dia.replace(month=1, day=1)
    return dia


def _periodo_anterior(inicio: date, granularidad: str) -> date:
    if granularidad == "week":
        return inicio - timedelta(days=7)
    if granularidad == "month":
        # Retroceder un mes sin depender de cuántos días tenga: el día 1 del
        # mes anterior es el día anterior al 1 de éste, normalizado.
        return (inicio - timedelta(days=1)).replace(day=1)
    if granularidad == "year":
        return inicio.replace(year=inicio.year - 1, month=1, day=1)
    return inicio - timedelta(days=1)


async def historial(
    db: AsyncSession,
    granularidad: str = "day",
    periodos: int | None = None,
) -> list[PeriodoDelHistorial]:
    """
    Las decisiones del modelo agrupadas por día, semana, mes o año, de la más
    antigua a la más reciente.

    El agrupamiento se hace en Python y no con `date_trunc` porque la tienda
    corre sobre PostgreSQL en producción y sobre SQLite en desarrollo, y cada
    uno escribe esa función a su manera. Con el volumen de una tienda —miles de
    evaluaciones, no millones— traer las filas del rango y contarlas aquí sale
    igual de rápido y funciona en las dos bases sin ramas por dialecto.

    Los períodos sin ninguna evaluación se devuelven en cero en lugar de
    faltar: una gráfica a la que le faltan los días tranquilos miente sobre la
    tendencia, porque une dos picos con una línea recta.
    """
    if granularidad not in GRANULARIDADES:
        granularidad = "day"
    cuantos = periodos or PERIODOS_POR_DEFECTO[granularidad]
    cuantos = max(1, min(cuantos, PERIODOS_MAXIMOS))

    ultimo = _inicio_del_periodo(datetime.now(ZONA_DE_LA_TIENDA), granularidad)

    # El primer período de la ventana: se retrocede contando, no restando días,
    # para que los meses de 28 y de 31 días cuenten lo mismo.
    primero = ultimo
    for _ in range(cuantos - 1):
        primero = _periodo_anterior(primero, granularidad)

    filas = (
        await db.execute(
            select(
                FraudLog.decision,
                FraudLog.fraud_score,
                FraudLog.evaluated_at,
                FraudLog.reviewed_at,
                FraudLog.is_actual_fraud,
                FraudLog.detection_time_ms,
                Order.total_amount,
            )
            .join(Order, Order.id == FraudLog.order_id)
            # El filtro sale en UTC porque así están guardadas las fechas; el
            # límite es la medianoche peruana del primer período.
            .where(
                FraudLog.evaluated_at
                >= datetime.combine(primero, time.min, tzinfo=ZONA_DE_LA_TIENDA)
            )
        )
    ).all()

    cubos: dict[date, dict] = {}
    for decision, puntaje, evaluado, revisado, es_fraude, milisegundos, monto in filas:
        if evaluado is None:
            continue
        if evaluado.tzinfo is None:
            # SQLite devuelve fechas ingenuas; se leen como UTC, que es como se
            # escribieron.
            evaluado = evaluado.replace(tzinfo=timezone.utc)
        inicio = _inicio_del_periodo(evaluado, granularidad)
        if inicio < primero or inicio > ultimo:
            continue

        cubo = cubos.setdefault(
            inicio,
            {"evaluaciones": 0, "aprobadas": 0, "en_revision": 0, "bloqueadas": 0,
             "monto_aprobado": 0.0, "monto_retenido": 0.0, "suma_puntaje": 0.0,
             "revisados": 0, "fraudes_reales": 0, "detectados": 0, "no_detectados": 0,
             "suma_ms": 0.0, "con_tiempo": 0},
        )
        decision = getattr(decision, "value", decision)
        monto = float(monto or 0.0)

        cubo["evaluaciones"] += 1
        cubo["suma_puntaje"] += float(puntaje or 0.0)
        if milisegundos is not None:
            cubo["suma_ms"] += float(milisegundos)
            cubo["con_tiempo"] += 1

        if decision == "REVIEW":
            cubo["en_revision"] += 1
            cubo["monto_retenido"] += monto
        elif decision == "BLOCKED":
            cubo["bloqueadas"] += 1
            cubo["monto_retenido"] += monto
        else:
            cubo["aprobadas"] += 1
            cubo["monto_aprobado"] += monto

        # Un fraude está "detectado" si el modelo no lo dejó pasar, sea porque
        # lo bloqueó o porque lo mandó a revisión. Es la misma definición que
        # usa `calcular`, y la que corresponde al indicador: lo que importa es
        # que la compra no siguió su curso, no por cuál de las dos ramas.
        if revisado is not None:
            cubo["revisados"] += 1
            if es_fraude:
                cubo["fraudes_reales"] += 1
                if decision in DECISIONES_DE_ALERTA:
                    cubo["detectados"] += 1
                else:
                    cubo["no_detectados"] += 1

    # Se recorre la ventana completa hacia atrás y se le da la vuelta, así el
    # resultado sale en orden cronológico y sin huecos.
    serie: list[PeriodoDelHistorial] = []
    inicio = ultimo
    for _ in range(cuantos):
        c = cubos.get(inicio)
        reales = c["fraudes_reales"] if c else 0
        serie.append(
            PeriodoDelHistorial(
                inicio=inicio,
                evaluaciones=c["evaluaciones"] if c else 0,
                aprobadas=c["aprobadas"] if c else 0,
                en_revision=c["en_revision"] if c else 0,
                bloqueadas=c["bloqueadas"] if c else 0,
                monto_aprobado=round(c["monto_aprobado"], 2) if c else 0.0,
                monto_retenido=round(c["monto_retenido"], 2) if c else 0.0,
                puntaje_medio=round(c["suma_puntaje"] / c["evaluaciones"], 4) if c and c["evaluaciones"] else 0.0,
                revisados=c["revisados"] if c else 0,
                fraudes_reales=reales,
                fraudes_detectados=c["detectados"] if c else 0,
                fraudes_no_detectados=c["no_detectados"] if c else 0,
                tasa_de_deteccion=round(c["detectados"] / reales, 4) if reales else None,
                tasa_de_no_deteccion=round(c["no_detectados"] / reales, 4) if reales else None,
                tiempo_medio_ms=round(c["suma_ms"] / c["con_tiempo"], 2) if c and c["con_tiempo"] else 0.0,
            )
        )
        inicio = _periodo_anterior(inicio, granularidad)

    serie.reverse()
    return serie
