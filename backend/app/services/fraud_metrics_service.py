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

import statistics
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fraud_log import FraudLog
from app.models.order import Order
from app.services.errors import OperacionNoPermitida

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


def _mediana(valores: list[float]) -> float:
    """
    El valor central de una lista, o 0.0 si está vacía.

    Se usa para el tiempo de detección. Ver `PeriodoDelHistorial.tiempo_medio_ms`
    para por qué la mediana y no el promedio.
    """
    if not valores:
        return 0.0
    return round(float(statistics.median(valores)), 2)


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
# Cuánto falta para entrenar con los pedidos de la tienda
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class ProgresoDeDatosReales:
    """Etiquetas acumuladas frente a las que pide el entrenamiento."""

    etiquetados: int
    fraudes: int
    legitimos: int
    minimo_total: int
    minimo_por_clase: int

    @property
    def suficientes(self) -> bool:
        return (
            self.etiquetados >= self.minimo_total
            and self.fraudes >= self.minimo_por_clase
            and self.legitimos >= self.minimo_por_clase
        )


async def progreso_hacia_datos_reales(db: AsyncSession) -> ProgresoDeDatosReales:
    """
    Cuántos pedidos etiquetados lleva la tienda y cuántos le faltan.

    El modelo que está sirviendo hoy se entrenó con un conjunto sintético del
    dominio, porque una tienda que acaba de abrir no tiene contracargos que
    aprender. En cuanto haya bastantes casos revisados de las dos clases, el
    reentrenamiento usa las transacciones reales y deja el sintético.

    Merece la pena enseñarlo en el panel: sin esto, "el modelo está entrenado"
    suena a que aprendió de la tienda, y no es lo que pasó todavía.

    La condición no se repite aquí: se lee de `ml/dataset.py`, que es quien la
    aplica. Copiar los números permitiría que el panel prometiera un umbral y
    el entrenamiento exigiera otro.
    """
    from ml.dataset import MINIMO_POR_CLASE, MINIMO_TOTAL

    etiquetas = (
        (
            await db.execute(
                select(FraudLog.is_actual_fraud).where(FraudLog.reviewed_at.is_not(None))
            )
        )
        .scalars()
        .all()
    )

    fraudes = sum(1 for es_fraude in etiquetas if es_fraude)
    return ProgresoDeDatosReales(
        etiquetados=len(etiquetas),
        fraudes=fraudes,
        legitimos=len(etiquetas) - fraudes,
        minimo_total=MINIMO_TOTAL,
        minimo_por_clase=MINIMO_POR_CLASE,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Historial: las mismas decisiones, repartidas en el tiempo
# ─────────────────────────────────────────────────────────────────────────────
#
# `calcular` responde "cómo va el modelo"; esto responde "cómo ha ido". Son
# preguntas distintas: un promedio sobre toda la vida de la tienda esconde que
# los bloqueos se dispararon la semana pasada.

GRANULARIDADES = (
    "day",
    "week",
    "month",
    "bimester",
    "quarter",
    "semester",
    "year",
)

# Las escalas que se cuentan por meses, y cuántos meses ocupa cada período.
# Todas se anclan a enero: el primer bimestre del año es enero-febrero, el
# primer trimestre enero-marzo, el primer semestre enero-junio. Anclarlos al
# calendario y no a "hace dos meses desde hoy" es lo que hace que dos consultas
# hechas en fechas distintas devuelvan los mismos bloques y se puedan comparar
# entre sí, que es justo para lo que sirven en un informe.
MESES_POR_PERIODO = {"month": 1, "bimester": 2, "quarter": 3, "semester": 6}

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
PERIODOS_POR_DEFECTO = {
    "day": 90,
    "week": 26,
    "month": 24,
    "bimester": 12,
    "quarter": 8,
    "semester": 6,
    "year": 5,
}
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
    # ── Los dos indicadores tal como los define la tesis ─────────────────────
    #
    #   DTF (%)  = fraudes detectados     / total de transacciones x 100
    #   NFND (%) = fraudes no detectados  / total de transacciones x 100
    #
    # Se dividen entre TODAS las transacciones del período, no solo entre las
    # fraudulentas. Son cosas distintas y conviene no confundirlas: las dos
    # tasas de arriba responden «de los fraudes que hubo, cuántos frenamos»
    # —la exhaustividad del modelo, que es la que puede pasar del 90 %—,
    # mientras que DTF y NFND responden «de todo lo que vendimos, qué
    # proporción fue fraude que frenamos, y cuál fraude que se nos coló».
    # Al dividir entre el total, el techo de DTF es la propia tasa de fraude
    # de la tienda: si el 7 % de las compras son fraude, DTF no puede pasar
    # del 7 % ni aunque se detecten todas.
    #
    # Estas dos sí se calculan siempre que haya transacciones, porque su
    # denominador no depende de que alguien haya etiquetado nada.
    dtf: float | None
    nfnd: float | None
    # Alertas que resultaron ser compras buenas: el administrador las revisó y
    # las etiquetó como legítimas. Es la otra mitad del expediente del modelo,
    # y la que le duele al negocio.
    falsas_alertas: int
    # De todo lo que el modelo frenó y alguien pudo comprobar, qué proporción
    # era fraude de verdad. Va en None cuando en el período no se frenó y
    # revisó nada: sin alertas comprobadas no hay precisión que calcular, y un
    # cero diría "todo lo que frenó estaba bien" que es justo lo contrario.
    precision: float | None
    # Éste sí se mide siempre: no necesita etiquetas, lo cronometra el propio
    # servicio en cada evaluación.
    #
    # Es la MEDIANA, no el promedio, por dos razones. La primera es que el
    # informe de entrenamiento ya definía así este indicador («mediana de
    # evaluaciones de una sola transacción») y tener el panel promediando
    # significaba que la misma cifra se calculaba de dos maneras distintas
    # según dónde se mirara. La segunda es que el promedio se rompe en cuanto
    # la ventana cruza el día en que entró el modelo: cuatrocientas
    # evaluaciones que tardaron horas —cuando decidía una persona— y
    # quinientas que tardaron un milisegundo dan una media de dos horas, que
    # no describe ni a unas ni a otras y esconde justo la mejora que el
    # indicador existe para enseñar.
    tiempo_medio_ms: float
    # Los tiempos del período, para poder calcular la mediana de la ventana
    # entera. No viaja a la respuesta: la mediana de las medianas no es la
    # mediana, así que hay que llegar a los valores.
    tiempos_ms: list[float] = field(default_factory=list)


def _ahora() -> datetime:
    """
    El instante actual según el reloj de la tienda.

    Está en una función suya, y no escrito dentro de `historial`, para poder
    fijarlo desde las pruebas. Sin ese punto de anclaje, una prueba que fecha
    sus datos con la hora de ahora y acto seguido pide el historial —que
    vuelve a preguntar la hora— falla si la medianoche peruana cae justo entre
    las dos llamadas: la ventana se corre un día entero y los datos aparecen
    en el período de al lado. Ocurre una vez al día durante unos segundos, que
    es lo peor que puede pasarle a una prueba: falla sola, de madrugada, y al
    revisarla por la mañana vuelve a pasar.
    """
    return datetime.now(ZONA_DE_LA_TIENDA)


def _periodo_de(dia: date, granularidad: str) -> date:
    """
    Lleva un día al comienzo del período que lo contiene.

    El día para "day", el lunes para "week", el 1 de enero para "year" y, para
    las escalas de meses, el primer mes de su bloque contado desde enero.

    Trabaja sobre un `date` y no sobre un instante porque las fechas que elige
    una persona en el calendario del panel ya vienen sin hora: convertirlas a
    medianoche solo para volver a quitarles la hora aquí abre la puerta a que
    la conversión de zona las corra un día.
    """
    if granularidad == "week":
        return dia - timedelta(days=dia.weekday())
    if granularidad == "year":
        return dia.replace(month=1, day=1)

    meses = MESES_POR_PERIODO.get(granularidad)
    if meses:
        primer_mes = ((dia.month - 1) // meses) * meses + 1
        return dia.replace(month=primer_mes, day=1)

    return dia


def _inicio_del_periodo(momento: datetime, granularidad: str) -> date:
    """El comienzo del período que contiene ese instante, en hora de la tienda."""
    return _periodo_de(momento.astimezone(ZONA_DE_LA_TIENDA).date(), granularidad)


def fin_del_periodo(inicio: date, granularidad: str) -> date:
    """
    El último día que todavía cae dentro del período que empieza en `inicio`.

    Hace falta para dos cosas: poner el límite superior de la consulta, y poder
    decir en la pantalla y en el reporte «del 1 al 30 de junio» en vez de «el
    período que empieza el 1 de junio», que es lo mismo pero no se entiende.
    """
    if granularidad == "week":
        return inicio + timedelta(days=6)
    if granularidad == "year":
        return inicio.replace(month=12, day=31)

    meses = MESES_POR_PERIODO.get(granularidad)
    if meses:
        # Se salta al primer día del período siguiente y se retrocede uno: así
        # los meses de 28, 30 y 31 días salen bien sin casos especiales.
        absoluto = (inicio.year * 12 + inicio.month - 1) + meses
        return date(absoluto // 12, absoluto % 12 + 1, 1) - timedelta(days=1)

    return inicio


def _periodo_anterior(inicio: date, granularidad: str) -> date:
    if granularidad == "week":
        return inicio - timedelta(days=7)
    if granularidad == "year":
        return inicio.replace(year=inicio.year - 1, month=1, day=1)

    meses = MESES_POR_PERIODO.get(granularidad)
    if meses:
        # Se cuenta en meses absolutos desde el año cero y se vuelve a fecha.
        # Restar días no sirve: los meses no miden lo mismo, y un bimestre no
        # son "61 días atrás".
        absoluto = (inicio.year * 12 + inicio.month - 1) - meses
        return date(absoluto // 12, absoluto % 12 + 1, 1)

    return inicio - timedelta(days=1)


def _cuantos_periodos(primero: date, ultimo: date, granularidad: str) -> int:
    """
    Cuántos períodos hay entre dos comienzos, contando los dos extremos.

    Se cuenta retrocediendo con `_periodo_anterior` en lugar de dividir la
    diferencia en días: un bimestre no son «61 días» y la división se
    equivocaría cada vez que el rango cruzara febrero. El bucle se corta en
    cuanto pasa del máximo, para que pedir «desde el año 1900» no cueste un
    millón de vueltas antes de rechazarse.
    """
    cuantos = 1
    cursor = ultimo
    while cursor > primero and cuantos <= PERIODOS_MAXIMOS:
        cursor = _periodo_anterior(cursor, granularidad)
        cuantos += 1
    return cuantos


def _ventana(
    granularidad: str,
    periodos: int | None,
    desde: date | None,
    hasta: date | None,
) -> tuple[date, date, int]:
    """
    Decide qué tramo de calendario se va a mirar: (primero, último, cuántos).

    Sin fechas se mira lo de siempre: los últimos N períodos hasta hoy. Con
    ellas manda el calendario, que es lo que hace falta para responder «cómo
    fue el 14 de agosto» o «cómo fue el mes pasado» sin contar períodos hacia
    atrás a mano.

    Las fechas se redondean al período que las contiene, no se parten por la
    mitad: si alguien pide del 14 al 20 de agosto en escala mensual, la
    respuesta es agosto entero. Devolver un trozo de mes rotulado «agosto»
    daría un porcentaje que no es el de agosto.
    """
    if desde and hasta and desde > hasta:
        raise OperacionNoPermitida(
            "La fecha inicial del rango no puede ser posterior a la final."
        )

    hoy = _inicio_del_periodo(_ahora(), granularidad)

    # Un rango que se mete en el futuro se recorta al período en curso. No hay
    # compras por venir, y dibujar meses vacíos por delante haría parecer que
    # la tienda dejó de vender.
    ultimo = min(_periodo_de(hasta, granularidad), hoy) if hasta else hoy

    if desde is None:
        cuantos = periodos or PERIODOS_POR_DEFECTO[granularidad]
        cuantos = max(1, min(cuantos, PERIODOS_MAXIMOS))
        # Se retrocede contando, no restando días, para que los meses de 28 y
        # de 31 días cuenten lo mismo.
        primero = ultimo
        for _ in range(cuantos - 1):
            primero = _periodo_anterior(primero, granularidad)
        return primero, ultimo, cuantos

    primero = min(_periodo_de(desde, granularidad), ultimo)
    cuantos = _cuantos_periodos(primero, ultimo, granularidad)
    if cuantos > PERIODOS_MAXIMOS:
        # Se dice en vez de recortar en silencio: un reporte que dice cubrir
        # cinco años y trae los últimos 366 días es peor que un error.
        raise OperacionNoPermitida(
            f"El rango pedido no cabe en un solo reporte: son más de "
            f"{PERIODOS_MAXIMOS} períodos en esta escala. Acorta el rango o "
            f"elige una escala más amplia."
        )
    return primero, ultimo, cuantos


async def historial(
    db: AsyncSession,
    granularidad: str = "day",
    periodos: int | None = None,
    desde: date | None = None,
    hasta: date | None = None,
) -> list[PeriodoDelHistorial]:
    """
    Las decisiones del modelo agrupadas por día, semana, mes o año, de la más
    antigua a la más reciente.

    Con `desde` y `hasta` se pide un tramo concreto del calendario —un día
    suelto, la semana pasada, el trimestre que se va a citar en la tesis— en
    lugar de la ventana que termina hoy. Ver `_ventana` para cómo se combinan
    con `periodos`.

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

    primero, ultimo, cuantos = _ventana(granularidad, periodos, desde, hasta)

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
            # Los dos límites son medianoches peruanas: la del primer día de
            # la ventana y la del día siguiente al último, que se deja fuera.
            # El tope superior no estaba antes porque la ventana siempre
            # terminaba hoy y no había nada más reciente que traer; con un
            # rango elegido a mano sí lo hay, y sin este filtro la consulta se
            # traería toda la vida posterior de la tienda para descartarla
            # después en Python.
            .where(
                FraudLog.evaluated_at
                >= datetime.combine(primero, time.min, tzinfo=ZONA_DE_LA_TIENDA)
            )
            .where(
                FraudLog.evaluated_at
                < datetime.combine(
                    fin_del_periodo(ultimo, granularidad) + timedelta(days=1),
                    time.min,
                    tzinfo=ZONA_DE_LA_TIENDA,
                )
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
             "falsas_alertas": 0, "tiempos": []},
        )
        decision = getattr(decision, "value", decision)
        monto = float(monto or 0.0)

        cubo["evaluaciones"] += 1
        cubo["suma_puntaje"] += float(puntaje or 0.0)
        if milisegundos is not None:
            cubo["tiempos"].append(float(milisegundos))

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
            elif decision in DECISIONES_DE_ALERTA:
                # Frenó una compra buena. No entra en ninguna de las dos tasas
                # de fraude, pero sin contarla la precisión no existe.
                cubo["falsas_alertas"] += 1

    # Se recorre la ventana completa hacia atrás y se le da la vuelta, así el
    # resultado sale en orden cronológico y sin huecos.
    serie: list[PeriodoDelHistorial] = []
    inicio = ultimo
    for _ in range(cuantos):
        c = cubos.get(inicio)
        reales = c["fraudes_reales"] if c else 0
        falsas = c["falsas_alertas"] if c else 0
        detectados = c["detectados"] if c else 0
        # El denominador de DTF y NFND: todas las transacciones del período.
        evaluaciones = c["evaluaciones"] if c else 0
        alertas_comprobadas = detectados + falsas
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
                fraudes_detectados=detectados,
                fraudes_no_detectados=c["no_detectados"] if c else 0,
                tasa_de_deteccion=round(detectados / reales, 4) if reales else None,
                tasa_de_no_deteccion=round(c["no_detectados"] / reales, 4) if reales else None,
                dtf=round(detectados / evaluaciones, 4) if evaluaciones else None,
                nfnd=(
                    round(c["no_detectados"] / evaluaciones, 4) if evaluaciones else None
                ),
                falsas_alertas=falsas,
                precision=(
                    round(detectados / alertas_comprobadas, 4)
                    if alertas_comprobadas
                    else None
                ),
                tiempo_medio_ms=_mediana(c["tiempos"]) if c else 0.0,
                tiempos_ms=c["tiempos"] if c else [],
            )
        )
        inicio = _periodo_anterior(inicio, granularidad)

    serie.reverse()
    return serie
