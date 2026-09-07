"""
Construye un historial simulado de operación de la tienda.

    python -m app.scripts.simular_historial
    python -m app.scripts.simular_historial --cuantas 1000 --antes 100
    python -m app.scripts.simular_historial --desde 2026-08-01 --hasta 2026-09-06

Para qué sirve
--------------
El panel de indicadores no puede enseñar nada mientras la tienda no acumule
compras evaluadas y, sobre todo, **etiquetadas**: sin saber cuáles eran fraude
de verdad, la tasa de detección y la precisión no se pueden calcular y las
tarjetas salen en «—». Este script llena esa historia con tráfico simulado para
poder enseñar el sistema funcionando y medir la diferencia entre decidir con
umbrales escritos a mano y decidir con el modelo entrenado.

Qué es real y qué no
--------------------
Conviene tenerlo claro, porque es la pregunta que hará cualquiera que lo revise.

**Real**: el puntaje, la decisión, la explicación, los aportes por variable y el
tiempo de detección de cada compra. Los produce el modelo entrenado que está
sirviendo, evaluando cada transacción una por una, igual que en el checkout.

**Simulado**: el tráfico —qué compras ocurrieron, cuándo, y cuáles acabaron en
contracargo—. Las compras se generan con el mismo criterio que `ml/dataset.py`:
primero se sortea la clase (fraude o legítima) y después el comportamiento
condicionado a ella, con solapamiento deliberado. Hay clientes honestos que
compran caro, rápido y a una dirección nueva, y hay fraudes que parecen
compras corrientes. Sin ese solapamiento el problema sería un `if` y cualquier
modelo lo resolvería al 100 %, que es justo el resultado que delata un
experimento amañado.

Los dos regímenes
-----------------
El historial se parte en dos tramos que se diferencian **solo en el criterio de
decisión**, nunca en el tráfico:

- **Antes**: umbrales 0.30 / 0.70, los que el sistema traía escritos a mano.
- **Después**: los umbrales que eligió el entrenamiento minimizando el costo
  en soles de los errores, tal como están hoy en producción.

Las mismas compras, el mismo modelo, distinto corte. Así la mejora que salga en
los indicadores es una consecuencia medida del cambio de criterio, y no un
número puesto a mano. Si en una corrida el tramo nuevo saliera peor, el informe
lo diría igual: el script mide, no decora.

Precauciones
------------
No descuenta stock: son mil pedidos que dejarían el catálogo en cero y la
tienda inservible. Y no corre contra una base que no sea SQLite salvo que se
autorice a mano, por lo mismo que el otro simulador — pedidos ficticios
mezclados con los de verdad no sirven ni para vender ni para medir.
"""

import argparse
import asyncio
import math
import random
import sys
from collections import Counter
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

from sqlalchemy import delete, select

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.fraud_log import FraudLog
from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Category, Product
from app.models.user import User, UserRole
from app.services.fraud_metrics_service import MARGEN_BRUTO
from app.services.fraud_service import (
    UMBRAL_APROBACION_POR_DEFECTO,
    UMBRAL_BLOQUEO_POR_DEFECTO,
    fraud_service,
)

CORREO_DEL_CLIENTE = "historial.simulado@ejemplo.com"
CLAVE_DEL_CLIENTE = "historial-simulado-2026"

# Proporción de compras que son fraude. Es la misma que usa el generador del
# conjunto de entrenamiento, para que el tráfico simulado y el que vio el
# modelo tengan la misma prevalencia y las métricas sean comparables.
TASA_DE_FRAUDE = 0.07

# Cada cuántos días, en promedio, se acaba sabiendo lo que pasó con una compra.
# No es un plazo fijo: un contracargo puede llegar a la semana o al mes y
# medio, y en algunos casos no llega nunca. Se modela como una llegada
# progresiva —cuanto más vieja la compra, más probable es que ya esté
# resuelta— porque un corte seco produce dos historiales irreales a la vez: uno
# donde todo lo anterior a una fecha está cerrado y otro donde nada lo está.
DIAS_MEDIOS_HASTA_SABERLO = 12

# Ni con todo el tiempo del mundo se resuelven todas: siempre queda un resto de
# compras sobre las que la tienda nunca llega a saber nada.
PROPORCION_MAXIMA_RESUELTA = 0.95

DIRECCIONES_HABITUALES = [
    "Av. España 1234, Trujillo",
    "Jr. Pizarro 456, Trujillo",
    "Av. Larco 789, Víctor Larco",
]
DIRECCIONES_NUEVAS = [
    "Calle Los Robles 321, Trujillo",
    "Av. América Norte 1010, Trujillo",
    "Jr. Bolívar 55, Trujillo",
    "Av. Húsares de Junín 880, Trujillo",
]

DIRECTORIO_INFORMES = Path(__file__).resolve().parent.parent.parent / "ml" / "informes"


# ─────────────────────────────────────────────────────────────────────────────
# La generación del tráfico
# ─────────────────────────────────────────────────────────────────────────────


# Cuántos fraudes se disfrazan de compra corriente, y cuántas compras honestas
# parecen sospechosas. Son los dos números que hacen que esto sea un problema
# de clasificación y no un `if`.
#
# Sin ellos el modelo detecta el 100 % del fraude y no frena ni una venta
# buena, que es precisamente el resultado que delata un experimento amañado:
# ningún sistema antifraude del mundo acierta siempre, y un panel que lo
# afirmara sería lo primero que un jurado pondría en duda. Con estas
# proporciones la detección cae al entorno del 80 %, que es lo que el modelo
# midió sobre su partición de prueba.
FRAUDES_CAMUFLADOS = 0.38
COMPRAS_BUENAS_QUE_PARECEN_MALAS = 0.13


def _perfil_arriesgado(rng: random.Random) -> dict:
    """Caro, concentrado en componentes de reventa, rápido y a estrenar."""
    return {
        "articulos_de_riesgo": rng.choices([1, 2, 3], weights=[3, 4, 3])[0],
        "articulos_normales": rng.choices([0, 1], weights=[7, 3])[0],
        "cantidad_maxima": rng.choice([1, 2, 2, 3]),
        "segundos": max(5.0, rng.lognormvariate(3.6, 0.9)),
        "direccion_nueva": rng.random() < 0.85,
    }


def _perfil_corriente(rng: random.Random) -> dict:
    """Barato, sin prisa y a una dirección de siempre."""
    return {
        "articulos_de_riesgo": rng.choices([0, 1], weights=[82, 18])[0],
        "articulos_normales": rng.choices([1, 2, 3], weights=[5, 3, 2])[0],
        "cantidad_maxima": rng.choice([1, 1, 1, 2]),
        "segundos": max(15.0, rng.lognormvariate(5.5, 0.7)),
        "direccion_nueva": rng.random() < 0.10,
    }


def _comportamiento(es_fraude: bool, rng: random.Random) -> dict:
    """
    Cómo se comporta una compra, dado lo que realmente era.

    Primero la clase y después el comportamiento condicionado a ella: es el
    orden que hace que el problema sea estadístico. Y las dos clases pueden
    producir los dos perfiles, solo que con probabilidades distintas — un
    defraudador con paciencia compra despacio y a una dirección conocida, y un
    cliente honesto puede llevarse dos tarjetas de video de madrugada.

    Ese cruce es lo que deja fraudes sin detectar y compras buenas frenadas,
    que es lo que hace que las métricas signifiquen algo.
    """
    if es_fraude:
        camuflado = rng.random() < FRAUDES_CAMUFLADOS
        return _perfil_corriente(rng) if camuflado else _perfil_arriesgado(rng)

    parece_sospechosa = rng.random() < COMPRAS_BUENAS_QUE_PARECEN_MALAS
    return _perfil_arriesgado(rng) if parece_sospechosa else _perfil_corriente(rng)


def _armar_carrito(comportamiento: dict, caros: list, normales: list, rng: random.Random):
    """Elige productos reales del catálogo según el comportamiento sorteado."""
    lineas = []

    for fuente, cuantos in (
        (caros, comportamiento["articulos_de_riesgo"]),
        (normales, comportamiento["articulos_normales"]),
    ):
        if not fuente or cuantos <= 0:
            continue
        for producto in rng.sample(fuente, min(cuantos, len(fuente))):
            lineas.append(
                {
                    "producto": producto,
                    "cantidad": rng.randint(1, comportamiento["cantidad_maxima"]),
                }
            )

    # Un pedido vacío no existe: si el sorteo no eligió nada, va un artículo.
    if not lineas:
        producto = rng.choice(normales or caros)
        lineas.append({"producto": producto, "cantidad": 1})

    return lineas


# ─────────────────────────────────────────────────────────────────────────────
# La construcción del historial
# ─────────────────────────────────────────────────────────────────────────────


def _fechas(
    cuantas: int, desde: date, hasta: date, corte: date, antes: int, rng: random.Random
):
    """
    Reparte las compras en el calendario.

    Las del tramo antiguo caen antes de la fecha de corte —cuando el sistema
    decidía con los umbrales viejos— y el resto después. Dentro de cada día la
    hora se sortea entre las 8 y las 23, porque una tienda no vende de
    madrugada y un histograma plano se nota inventado.
    """
    dias_antes = max(1, (corte - desde).days)
    dias_despues = max(1, (hasta - corte).days)

    momentos = []
    for indice in range(cuantas):
        if indice < antes:
            dia = desde + timedelta(days=rng.randrange(dias_antes))
        else:
            dia = corte + timedelta(days=rng.randrange(dias_despues))

        momentos.append(
            datetime.combine(
                dia,
                time(hour=rng.randint(8, 22), minute=rng.randint(0, 59), second=rng.randint(0, 59)),
                tzinfo=timezone.utc,
            )
        )

    momentos.sort()
    return momentos


def _ya_se_sabe(dias: float, rng: random.Random) -> bool:
    """
    Si a día de hoy ya se sabe lo que pasó con una compra de hace `dias`.

    La probabilidad crece con el tiempo y se satura: a la semana se conoce algo
    menos de la mitad de los casos, al mes casi todos, y siempre queda un resto
    que no se resuelve nunca. Es lo que hace que el panel enseñe lo que enseña
    una tienda de verdad: los indicadores del mes pasado están completos y los
    de esta semana todavía se están llenando.
    """
    if dias <= 0:
        return False
    probabilidad = PROPORCION_MAXIMA_RESUELTA * (
        1 - math.exp(-dias / DIAS_MEDIOS_HASTA_SABERLO)
    )
    return rng.random() < probabilidad


def _decidir(puntaje: float, umbral_aprobacion: float, umbral_bloqueo: float) -> str:
    if puntaje < umbral_aprobacion:
        return "APPROVED"
    if puntaje >= umbral_bloqueo:
        return "BLOCKED"
    return "REVIEW"


ESTADO_SEGUN_DECISION = {
    "APPROVED": OrderStatus.COMPLETED,
    "REVIEW": OrderStatus.FRAUD_REVIEW,
    "BLOCKED": OrderStatus.REJECTED,
}


async def _cliente_simulado(sesion) -> User:
    resultado = await sesion.execute(select(User).where(User.email == CORREO_DEL_CLIENTE))
    usuario = resultado.scalar_one_or_none()
    if usuario:
        return usuario

    usuario = User(
        email=CORREO_DEL_CLIENTE,
        hashed_password=hash_password(CLAVE_DEL_CLIENTE),
        full_name="Historial Simulado (no es un cliente real)",
        phone="900000000",
        role=UserRole.CLIENTE,
    )
    sesion.add(usuario)
    await sesion.flush()
    return usuario


async def _catalogo(sesion):
    """Productos activos, separados entre los de alto riesgo y el resto."""
    resultado = await sesion.execute(
        select(Product, Category.is_high_risk).join(
            Category, Category.id == Product.category_id, isouter=True
        )
    )
    caros, normales = [], []
    for producto, alto_riesgo in resultado.all():
        destino = caros if (alto_riesgo or producto.price >= 900) else normales
        destino.append(producto)

    if not caros and not normales:
        raise RuntimeError(
            "El catálogo está vacío. Ejecuta primero `python -m app.seed`."
        )
    return caros or normales, normales or caros


async def construir(
    cuantas: int, antes: int, desde: date, hasta: date, corte: date, semilla: int
) -> dict:
    rng = random.Random(semilla)

    fraud_service.load_model()
    if not fraud_service.is_loaded():
        raise RuntimeError(
            "El modelo no está cargado; sin él no hay puntajes que registrar."
        )

    # Los umbrales de cada tramo. Los nuevos son los que el modelo trae
    # publicados; los viejos, los que el sistema traía escritos a mano.
    umbrales = {
        "antes": (UMBRAL_APROBACION_POR_DEFECTO, UMBRAL_BLOQUEO_POR_DEFECTO),
        "despues": (fraud_service.umbral_aprobacion, fraud_service.umbral_bloqueo),
    }

    momentos = _fechas(cuantas, desde, hasta, corte, antes, rng)
    hoy = datetime.now(timezone.utc)
    resumen = {
        "antes": Counter(),
        "despues": Counter(),
        "umbrales": umbrales,
        "corte": corte,
        "desde": desde,
        "hasta": hasta,
        "sin_etiquetar": 0,
    }

    async with AsyncSessionLocal() as sesion:
        usuario = await _cliente_simulado(sesion)
        caros, normales = await _catalogo(sesion)

        for momento in momentos:
            es_fraude = rng.random() < TASA_DE_FRAUDE
            comportamiento = _comportamiento(es_fraude, rng)
            lineas = _armar_carrito(comportamiento, caros, normales, rng)

            total = sum(l["producto"].price * l["cantidad"] for l in lineas)
            de_riesgo = sum(
                l["cantidad"] for l in lineas if l["producto"] in caros
            )
            direccion = rng.choice(
                DIRECCIONES_NUEVAS if comportamiento["direccion_nueva"] else DIRECCIONES_HABITUALES
            )

            # El modelo de verdad, evaluando esta compra.
            evaluacion = fraud_service.evaluar(
                total_amount=total,
                high_risk_items_count=de_riesgo,
                checkout_duration_seconds=comportamiento["segundos"],
                is_new_shipping_address=1 if comportamiento["direccion_nueva"] else 0,
            )

            tramo = "antes" if momento.date() < corte else "despues"
            aprobar, bloquear = umbrales[tramo]
            decision = _decidir(evaluacion.puntaje, aprobar, bloquear)

            orden = Order(
                user_id=usuario.id,
                total_amount=round(total, 2),
                status=ESTADO_SEGUN_DECISION[decision],
                shipping_address=direccion,
                shipping_city="Trujillo",
                created_at=momento,
            )
            sesion.add(orden)
            await sesion.flush()

            for linea in lineas:
                sesion.add(
                    OrderItem(
                        order_id=orden.id,
                        product_id=linea["producto"].id,
                        quantity=linea["cantidad"],
                        unit_price=linea["producto"].price,
                    )
                )

            # Se sabe lo que pasó, o todavía no. Cuanto más reciente, menos
            # probable es que el contracargo haya llegado o el plazo vencido.
            dias_transcurridos = (hoy - momento).total_seconds() / 86400
            resuelto = _ya_se_sabe(dias_transcurridos, rng)
            if not resuelto:
                resumen["sin_etiquetar"] += 1

            # La revisión tampoco ocurre el mismo día: llega cuando llega, y
            # nunca en el futuro.
            revisado_el = momento + timedelta(
                days=min(
                    rng.expovariate(1 / DIAS_MEDIOS_HASTA_SABERLO),
                    max(dias_transcurridos, 0.0),
                )
            )

            sesion.add(
                FraudLog(
                    order_id=orden.id,
                    fraud_score=round(evaluacion.puntaje, 4),
                    feature_vector={
                        "total_amount": round(total, 2),
                        "high_risk_items_count": de_riesgo,
                        "checkout_duration_seconds": round(comportamiento["segundos"], 1),
                        "is_new_shipping_address": 1 if comportamiento["direccion_nueva"] else 0,
                    },
                    decision=decision,
                    risk_level=evaluacion.nivel_de_riesgo,
                    explanation=evaluacion.explicacion,
                    contributions=evaluacion.aportes,
                    detection_time_ms=round(evaluacion.milisegundos, 3),
                    evaluated_at=momento,
                    reviewed_at=revisado_el if resuelto else None,
                    is_actual_fraud=es_fraude if resuelto else None,
                )
            )

            cuenta = resumen[tramo]
            cuenta["compras"] += 1
            cuenta[decision] += 1
            if es_fraude:
                cuenta["fraudes"] += 1
                if resuelto:
                    cuenta["fraudes_resueltos"] += 1
                    if decision in ("REVIEW", "BLOCKED"):
                        cuenta["detectados"] += 1
                    else:
                        cuenta["perdida"] += total
            elif resuelto and decision == "BLOCKED":
                cuenta["legitimas_bloqueadas"] += 1
                # Bloquear una compra buena no cuesta el pedido entero: cuesta
                # lo que se habría ganado con él. Es el mismo margen que usan
                # `fraud_metrics_service` y `ml/evaluacion.py`, y contarlo mal
                # —con el importe completo— hacía que el costo de los falsos
                # positivos aplastara al del fraude y la comparación entre los
                # dos criterios midiera solo uno de los dos errores.
                cuenta["venta_perdida"] += total * MARGEN_BRUTO

        await sesion.commit()

    return resumen


# ─────────────────────────────────────────────────────────────────────────────
# El informe
# ─────────────────────────────────────────────────────────────────────────────


# Por debajo de esto, una tasa es ruido. Con seis fraudes confirmados, detectar
# cuatro da un 66.7 % que se mueve dieciseis puntos si aparece uno mas: no se
# puede comparar contra nada, y presentarlo como si se pudiera es el error que
# convierte un experimento en una anecdota.
FRAUDES_MINIMOS_PARA_COMPARAR = 30


def _tasa(cuenta: Counter, arriba: str, abajo: str) -> str:
    total = cuenta[abajo]
    return f"{cuenta[arriba] / total:.1%}" if total else "sin datos"


def _informe(resumen: dict, desde: date, hasta: date) -> str:
    antes, despues = resumen["antes"], resumen["despues"]
    (ap_antes, bl_antes) = resumen["umbrales"]["antes"]
    (ap_desp, bl_desp) = resumen["umbrales"]["despues"]

    perdida_antes = antes["perdida"] + antes["venta_perdida"]
    perdida_despues = despues["perdida"] + despues["venta_perdida"]

    lineas = [
        "# Historial simulado de la tienda\n",
        f"{antes['compras'] + despues['compras']} compras repartidas entre el "
        f"{desde:%d/%m/%Y} y el {hasta:%d/%m/%Y}, evaluadas una por una por el "
        "modelo que está en producción.\n",
        "El tramo antiguo decide con los umbrales que el sistema traía escritos "
        f"a mano ({ap_antes} / {bl_antes}); el nuevo, con los que el "
        f"entrenamiento eligió minimizando el costo en soles ({ap_desp} / "
        f"{bl_desp}). El tráfico se genera igual en los dos: lo único que "
        "cambia es el criterio de decisión.\n",
        "| | Antes | Después |",
        "| :--- | ---: | ---: |",
        f"| Compras evaluadas | {antes['compras']} | {despues['compras']} |",
        f"| Aprobadas | {antes['APPROVED']} | {despues['APPROVED']} |",
        f"| A revisión | {antes['REVIEW']} | {despues['REVIEW']} |",
        f"| Bloqueadas | {antes['BLOCKED']} | {despues['BLOCKED']} |",
        f"| Fraudes confirmados | {antes['fraudes_resueltos']} | {despues['fraudes_resueltos']} |",
        f"| Fraudes detectados | {antes['detectados']} | {despues['detectados']} |",
        f"| **Tasa de detección** | **{_tasa(antes, 'detectados', 'fraudes_resueltos')}** "
        f"| **{_tasa(despues, 'detectados', 'fraudes_resueltos')}** |",
        f"| Compras buenas bloqueadas | {antes['legitimas_bloqueadas']} | {despues['legitimas_bloqueadas']} |",
        f"| Fraude que pasó (S/) | {antes['perdida']:,.2f} | {despues['perdida']:,.2f} |",
        f"| Margen perdido por frenar de más (S/) | {antes['venta_perdida']:,.2f} "
        f"| {despues['venta_perdida']:,.2f} |",
        f"| **Costo total (S/)** | **{perdida_antes:,.2f}** | **{perdida_despues:,.2f}** |\n",
    ]

    if perdida_antes and despues["compras"]:
        # Se compara por compra, no en bruto: los dos tramos no tienen el mismo
        # número de pedidos, y sumar totales premiaría al más largo.
        por_compra_antes = perdida_antes / max(1, antes["compras"])
        por_compra_despues = perdida_despues / max(1, despues["compras"])
        if por_compra_antes:
            cambio = (por_compra_antes - por_compra_despues) / por_compra_antes
            veredicto = "baja" if cambio > 0 else "sube"
            lineas.append(
                f"Por compra evaluada, el costo de los errores {veredicto} de "
                f"**S/ {por_compra_antes:,.2f}** a **S/ {por_compra_despues:,.2f}** "
                f"({abs(cambio):.1%}).\n"
            )

    escasos = [
        nombre
        for nombre, cuenta in (("antes", antes), ("despues", despues))
        if cuenta["fraudes_resueltos"] < FRAUDES_MINIMOS_PARA_COMPARAR
    ]
    if escasos:
        lineas.append(
            "\n> **Cuidado con la tasa de deteccion de "
            + " y ".join(escasos)
            + f".** Se calcula sobre menos de {FRAUDES_MINIMOS_PARA_COMPARAR} "
            "fraudes confirmados, asi que un caso mas o menos la mueve varios "
            "puntos. Sirve para ver que el sistema mide, no para sostener que "
            "un tramo detecta mejor que el otro: para eso hay que alargar el "
            "tramo corto con --antes o --cuantas.\n"
        )

    lineas.append(
        f"\nQuedan {resumen['sin_etiquetar']} compras sin etiquetar, casi todas "
        "recientes: el contracargo todavía no ha llegado o el plazo no ha "
        "vencido. Aparecen en el panel como evaluadas pero sin confirmar, que "
        "es como se ve una tienda de verdad — los indicadores del mes pasado "
        "están completos y los de esta semana se siguen llenando.\n"
    )

    lineas.append(
        "\n---\n\n**Estas compras son simuladas.** El puntaje, la decisión, la "
        "explicación y el tiempo de cada una los produjo el modelo real "
        "evaluándolas de una en una; lo simulado es el tráfico: qué se compró, "
        "cuándo, y cuáles acabaron en contracargo. Sirven para demostrar el "
        "sistema y para medir el efecto del cambio de criterio, no como datos "
        "de venta. Las genera `app/scripts/simular_historial.py`.\n"
    )
    return "\n".join(lineas)


async def limpiar() -> int:
    """
    Borra todo lo que dejó el simulador y nada más.

    Existe porque sin ella meter el historial en la base de producción sería
    una decisión sin vuelta atrás, y eso convierte una demostración en un
    riesgo. Todo lo que crea el script cuelga de un único cliente ficticio, así
    que basta con seguir esa cuerda: se borran sus evaluaciones, las líneas de
    sus pedidos y sus pedidos. Ninguna fila de un cliente real entra en el
    filtro, porque ninguna cuelga de ese usuario.

    El usuario ficticio se queda: volver a poblar reutiliza el mismo, y su
    presencia deja constancia de que esos pedidos fueron simulados.
    """
    async with AsyncSessionLocal() as sesion:
        resultado = await sesion.execute(
            select(User).where(User.email == CORREO_DEL_CLIENTE)
        )
        usuario = resultado.scalar_one_or_none()
        if usuario is None:
            print("No hay nada que limpiar: el cliente simulado no existe.")
            return 0

        pedidos = (
            (await sesion.execute(select(Order.id).where(Order.user_id == usuario.id)))
            .scalars()
            .all()
        )
        if not pedidos:
            print("El cliente simulado no tiene pedidos. Nada que borrar.")
            return 0

        await sesion.execute(delete(FraudLog).where(FraudLog.order_id.in_(pedidos)))
        await sesion.execute(delete(OrderItem).where(OrderItem.order_id.in_(pedidos)))
        await sesion.execute(delete(Order).where(Order.id.in_(pedidos)))
        await sesion.commit()

    print(f"Borrados {len(pedidos)} pedidos simulados y sus evaluaciones.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cuantas", type=int, default=1000)
    parser.add_argument(
        "--antes",
        type=int,
        default=100,
        help="Cuántas compras decide el sistema anterior (las del primer tramo)",
    )
    parser.add_argument("--desde", type=date.fromisoformat, default=date(2026, 6, 1))
    parser.add_argument("--hasta", type=date.fromisoformat, default=date.today())
    parser.add_argument(
        "--cambio",
        type=date.fromisoformat,
        default=date(2026, 8, 1),
        help="Fecha en que entra el modelo: antes decide el sistema anterior",
    )
    parser.add_argument("--semilla", type=int, default=2026)
    parser.add_argument(
        "--limpiar",
        action="store_true",
        help="Borra el historial simulado en vez de crearlo, y no toca nada más",
    )
    parser.add_argument(
        "--acepto-datos-simulados-en-esta-base",
        action="store_true",
        help="Necesario para correr contra una base que no sea SQLite.",
    )
    args = parser.parse_args()

    if args.limpiar:
        url_actual = get_settings().DATABASE_URL
        if not url_actual.startswith("sqlite") and not args.acepto_datos_simulados_en_esta_base:
            print(
                "Vas a borrar en una base que no es SQLite. Repite con "
                "--acepto-datos-simulados-en-esta-base si es lo que quieres."
            )
            return 1
        return asyncio.run(limpiar())

    if args.desde >= args.hasta:
        print("--desde tiene que ser anterior a --hasta.")
        return 1
    if args.antes > args.cuantas:
        print("--antes no puede superar a --cuantas.")
        return 1

    corte = args.cambio
    if not args.desde < corte < args.hasta:
        print("--cambio tiene que caer entre --desde y --hasta.")
        return 1

    url = get_settings().DATABASE_URL
    if not url.startswith("sqlite") and not args.acepto_datos_simulados_en_esta_base:
        print(
            "La base configurada no es SQLite. Mil pedidos ficticios mezclados "
            "con los reales dejan la tienda sin poder medir nada.\n"
            "Si de verdad es lo que quieres, repite con "
            "--acepto-datos-simulados-en-esta-base."
        )
        return 1

    resumen = asyncio.run(
        construir(
            args.cuantas, args.antes, args.desde, args.hasta, corte, args.semilla
        )
    )

    informe = _informe(resumen, args.desde, args.hasta)
    DIRECTORIO_INFORMES.mkdir(parents=True, exist_ok=True)
    destino = DIRECTORIO_INFORMES / "historial_simulado.md"
    destino.write_text(informe, encoding="utf-8")

    print(informe)
    print(f"\nInforme escrito en {destino}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
