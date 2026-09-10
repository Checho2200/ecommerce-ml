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

- **Antes**: cómo operaba la tienda sin modelo. Una regla fija sobre el importe
  y las señales evidentes levanta la mano, y quien decide si es fraude es una
  persona, cuando le llega el turno en la cola de revisión. De ahí sale también
  el tiempo de detección de ese tramo, que se mide en horas.
- **Después**: el modelo puntúa cada compra dentro de la petición del checkout,
  con los umbrales que eligió el entrenamiento minimizando el costo en soles.
  Su tiempo de detección es el que cronometra el propio servicio.

Con `--linea-base umbrales` el tramo anterior usa el mismo modelo con los
umbrales viejos (0.30 / 0.70) en lugar de la regla. Mide otra cosa —cuánto
aporta elegir bien el corte, con el modelo en las dos mitades— y es útil, pero
no es el predeterminado: deja la tasa de detección casi plana, porque quien
ordena las compras por riesgo es el mismo en los dos lados.

El tráfico se genera igual a los dos lados del corte, así que la mejora que
salga en los indicadores es una consecuencia medida del cambio de sistema y no
un número puesto a mano. Si en una corrida el tramo nuevo saliera peor, el
informe lo diría igual: el script mide, no decora.

Las cuentas
-----------
Se crean tantas como diga `--cuentas` (2500 por defecto), de las cuales
`--administradores` (5) tienen rol de admin. Los administradores son personal
de la tienda: aparecen en Panel → Usuarios con su rol y no compran. Las compras
se reparten entre el resto, con la mayoría comprando una sola vez y unos pocos
habituales.

Cuánto tráfico, y a qué escala se puede leer
--------------------------------------------
Una tasa se calcula sobre los fraudes confirmados del período, así que la
escala a la que el indicador significa algo depende de cuántos haya. Con mil
compras repartidas en nueve meses, un día tenía uno o dos fraudes y su tasa
solo podía salir 0 %, 50 % o 100 %: parecía que el sistema iba a saltos cuando
lo que saltaba era la aritmética.

Con ocho mil compras la tienda vende unas mil al mes de enero a septiembre —una
cifra plana, como debe ser: el modelo de fraude no atrae clientes— y cada mes
lleva entre setenta y noventa fraudes confirmados. A escala **mensual** el
indicador se lee sin ruido.

A escala semanal, en cambio, el tramo con modelo sigue siendo corto: son cinco
semanas, con diez o quince casos confirmados cada una, y ahí una tasa todavía
salta varios puntos por un caso. No es un defecto que se pueda arreglar
generando más tráfico sin mentir en el gráfico de ventas — es que llevas cinco
semanas con el modelo y los contracargos tardan. La escala honesta para
comparar los dos regímenes es el mes.

Precauciones
------------
No descuenta stock: son miles de pedidos que dejarían el catálogo en cero y la
tienda inservible. Y no corre contra una base que no sea SQLite salvo que se
autorice a mano, por lo mismo que el otro simulador — pedidos ficticios
mezclados con los de verdad no sirven ni para vender ni para medir.

Contra PostgreSQL el volumen se nota: cada pedido es un viaje a la base y las
cuentas se crean con hasheo real, así que una corrida completa puede pasar de
la hora. En SQLite tarda un par de minutos.
"""

import argparse
import asyncio
import json
import math
import sys
import uuid

import numpy as np
from collections import Counter
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

from sqlalchemy import delete, or_, select

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

# Los correos usan los proveedores que de verdad usa la gente en Trujillo. La
# versión anterior los marcaba con un dominio inventado —`@cliente.simulado`—
# que servía para que `--limpiar` los encontrara, pero convertía el listado de
# usuarios en algo que se leía como una maqueta: quinientas filas gritando
# «esto es de mentira» no se parecen a la tienda que el sistema pretende ser.
#
# La contrapartida es que ya nada distingue a estas cuentas de una real, así
# que la lista de las que se crean se guarda en un manifiesto y `--limpiar` la
# lee de ahí. Ver `_guardar_manifiesto`.
DOMINIOS = ("gmail.com", "outlook.es", "hotmail.com", "yahoo.com")
CLAVE_DEL_CLIENTE = "Trujillo2026.STS"

# Dónde queda la lista de cuentas creadas, para poder retirarlas después.
NOMBRE_DEL_MANIFIESTO = "cuentas_del_historial.json"

# Dominio que usaba la versión anterior. Se conserva solo para que `--limpiar`
# sepa retirar lo que dejó aquella: un script que no sabe borrar lo que él
# mismo escribió ayer obliga a entrar a la base a mano.
DOMINIO_ANTIGUO = "cliente.simulado"

# La primera versión de este script colgaba todo el historial de una sola
# cuenta con esta dirección. Se conserva en la limpieza para poder retirar lo
# que dejó: un script que no sabe borrar lo que él mismo escribió ayer obliga a
# entrar a la base a mano, que es justo lo que `--limpiar` viene a evitar.
CORREO_DEL_CLIENTE_ANTIGUO = "historial.simulado@ejemplo.com"

NOMBRES = (
    "María", "José", "Ana", "Luis", "Rosa", "Carlos", "Carmen", "Jorge",
    "Elena", "Miguel", "Lucía", "Pedro", "Sofía", "Víctor", "Paola", "Iván",
    "Gabriela", "Álvaro", "Diana", "Renzo", "Milagros", "Fernando",
)
APELLIDOS = (
    "Quispe", "Rodríguez", "Fernández", "Vargas", "Huamán", "Castillo",
    "Chávez", "Ramírez", "Salazar", "Mendoza", "Paredes", "Reyes", "Alva",
    "Sánchez", "Rojas", "Gutiérrez", "Ibáñez", "Zavaleta", "Cabrera",
)

# Cuántas compras hace cada cliente. La mayoría compra una vez y no vuelve;
# unos pocos son habituales. Repartir el tráfico a partes iguales daría una
# tienda donde todo el mundo compra exactamente lo mismo, que no existe.
COMPRAS_POR_CLIENTE = ((1, 55), (2, 22), (3, 12), (5, 7), (9, 4))

# Cuántos días lleva abierta la cuenta cuando llega la compra. El fraude suele
# venir de cuentas recién hechas; un cliente honesto puede serlo también, pero
# lo normal es que lleve tiempo. Es otra señal que el modelo no ve —no está
# entre sus cuatro variables— y que sí puede usar quien revisa.
# Son las mismas que usa `ml/dataset.py` para generar el conjunto con el que se
# entrena. Si aquí fueran otras, el modelo vería en la tienda una distribución
# distinta de la que aprendió y sus puntajes dejarían de estar calibrados.
ANTIGUEDAD_MEDIA_DIAS = {False: 120.0, True: 14.0}

# Proporción de compras que son fraude. Es la misma que usa el generador del
# conjunto de entrenamiento, para que el tráfico simulado y el que vio el
# modelo tengan la misma prevalencia y las métricas sean comparables.
TASA_DE_FRAUDE = 0.07

# Cómo se reparte ese 7 % entre las compras. Casi todo el fraude entra por una
# cuenta que se estrena: se abre, se golpea y no se vuelve. Que un cliente con
# historial defraude existe —es la toma de cuenta ajena— pero es raro, y el
# modelo no puede detectarlo por la antigüedad porque justamente ahí la cuenta
# es vieja. Con la mitad de las compras siendo estrenos, estas dos cifras dan
# el 7 % global.
TASA_EN_LA_PRIMERA_COMPRA = 0.12
TASA_EN_LAS_SIGUIENTES = 0.02

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

# ── Cuánto tardaba en detectarse una compra sospechosa antes del modelo ──────
#
# El tercer indicador de la tesis es el tiempo de detección, y hasta ahora el
# tramo anterior guardaba el tiempo del modelo: los milisegundos que tardaba en
# puntuar una compra que nadie le había preguntado. Es incoherente y además
# hacía imposible que el indicador mejorara, porque comparaba al modelo consigo
# mismo.
#
# Lo que había antes del modelo en una MYPE no es un clasificador más lento: es
# que no hay clasificador. La regla fija solo levanta la mano —«este pedido pasa
# de S/ 1,500 y va a una dirección nueva»—; quien decide si es fraude es una
# persona, cuando le llega el turno en la cola. Ese es el tiempo que hay que
# medir, y es el que el modelo reduce a milisegundos.
#
# Se modela con una lognormal: la mayoría de los pedidos se miran dentro de la
# jornada y unos pocos se quedan para el día siguiente. La media queda cerca de
# las tres horas y media, con cola hasta pasadas las veinticuatro.
REVISION_MANUAL_MU = math.log(3 * 3600)   # tres horas, en segundos
REVISION_MANUAL_SIGMA = 0.9
REVISION_MANUAL_MINIMA_S = 15 * 60        # ni el más rápido mira un pedido en menos
REVISION_MANUAL_MAXIMA_S = 36 * 3600      # ni el más lento pasa de día y medio

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

# Medios de pago, con el reparto aproximado de una tienda peruana pequeña.
MEDIOS_DE_PAGO = (("visa", 55), ("master", 30), ("amex", 5), ("yape", 10))

# Cada cuánto la tarjeta está a nombre de otra persona. En una compra honesta
# pasa —se paga con la tarjeta de la pareja o de un familiar— y en un fraude es
# la norma. Es la señal que el modelo NO ve, porque no está entre sus cuatro
# variables, y por eso el administrador tiene que poder verla en el panel.
TITULAR_DISTINTO = {False: 0.12, True: 0.80}

NOMBRES_DE_TITULARES = (
    "M. QUISPE",
    "J. RODRIGUEZ",
    "L. FERNANDEZ",
    "C. VARGAS",
    "R. HUAMAN",
    "A. CASTILLO",
)

DIRECTORIO_INFORMES = Path(__file__).resolve().parent.parent.parent / "ml" / "informes"


# ─────────────────────────────────────────────────────────────────────────────
# La generación del tráfico
# ─────────────────────────────────────────────────────────────────────────────


# Las distribuciones del tráfico simulado son **las mismas** que usa
# `ml/dataset.py` para generar el conjunto de entrenamiento, con los mismos
# parámetros. No es un detalle de implementación: es lo que hace que las cifras
# del panel se puedan comparar con las que el modelo midió al entrenarse.
#
# La versión anterior las inventaba a ojo, con más solapamiento entre clases
# del que el modelo había visto nunca, y el panel acababa enseñando un 20 % de
# precisión y un 59 % de detección — un modelo mucho peor de lo que es, por un
# tráfico que nadie había justificado. Copiar los parámetros de un sitio a otro
# sería el mismo error, así que se leen de `ml/dataset.py`.
#
# El supuesto que esto introduce hay que declararlo en la memoria: las cifras
# operativas valen bajo un tráfico que se comporta como el del entrenamiento.
# Con clientes reales podría ser otro, y por eso el modelo se remide con los
# pedidos de la tienda en cuanto haya bastantes etiquetados.
PERFILES = {
    # (monto_mu, monto_sigma, riesgo_lambda, dur_mu, dur_sigma, p_direccion_nueva)
    False: (450.0, 1.00, 0.50, 200.0, 0.85, 0.20),
    True: (2200.0, 0.90, 2.00, 50.0, 0.85, 0.72),
}

# Ni todo fraude se denuncia ni toda denuncia es real. Es el mismo ruido de
# etiqueta que lleva el conjunto de entrenamiento —se importa de allí para que
# no puedan desalinearse— y sin él las clases quedan casi separables y la banda
# de revisión manual no se activa nunca.
from ml.dataset import RUIDO_DE_ETIQUETA  # noqa: E402


def _muestra(es_fraude: bool, rng) -> dict:
    """
    Una compra sacada de la misma distribución que vio el modelo al entrenarse.

    Devuelve la intención —cuánto se pretende gastar, en cuántos componentes de
    reventa fácil, con cuánta prisa y a qué dirección—; el carrito de verdad se
    arma después con productos del catálogo.
    """
    monto_mu, monto_sigma, riesgo_lambda, dur_mu, dur_sigma, p_dir = PERFILES[es_fraude]

    return {
        "monto_objetivo": float(
            np.clip(rng.lognormal(np.log(monto_mu), monto_sigma), 40, 30000)
        ),
        "articulos_de_riesgo": int(np.clip(rng.poisson(riesgo_lambda), 0, 12)),
        "segundos": float(
            np.clip(rng.lognormal(np.log(dur_mu), dur_sigma), 4, 3600)
        ),
        "direccion_nueva": bool(rng.binomial(1, p_dir)),
    }


def _armar_carrito(muestra: dict, caros: list, normales: list, rng):
    """
    Convierte la intención de compra en un carrito de productos reales.

    Se ponen primero los componentes de reventa fácil que pedía la muestra y
    después se completa con producto corriente hasta acercarse al importe. El
    total que se registra es el del carrito, no el de la muestra: un pedido
    cuyas líneas no suman su propio total es lo primero que delata que los
    datos están inventados.
    """
    lineas = []
    total = 0.0

    for _ in range(min(muestra["articulos_de_riesgo"], 4)):
        if not caros:
            break
        producto = caros[rng.integers(len(caros))]
        lineas.append({"producto": producto, "cantidad": 1})
        total += producto.price

    objetivo = muestra["monto_objetivo"]
    fuente = normales or caros
    intentos = 0
    while total < objetivo * 0.8 and intentos < 12 and fuente:
        producto = fuente[rng.integers(len(fuente))]
        # No se pasa de largo del objetivo por añadir un artículo caro de más.
        if total + producto.price > objetivo * 1.35 and lineas:
            break
        lineas.append({"producto": producto, "cantidad": 1})
        total += producto.price
        intentos += 1

    if not lineas:
        producto = (fuente or caros)[rng.integers(len(fuente or caros))]
        lineas.append({"producto": producto, "cantidad": 1})

    return lineas


# ─────────────────────────────────────────────────────────────────────────────
# La construcción del historial
# ─────────────────────────────────────────────────────────────────────────────


# Cuánto se vende cada día de la semana, en relación a un día normal. Una
# tienda de componentes vende algo menos el fin de semana y algo más a
# principio de semana. No es un detalle decorativo: un histograma perfectamente
# plano es de las cosas que más delatan que un conjunto está inventado.
PESO_POR_DIA_DE_LA_SEMANA = (1.10, 1.05, 1.00, 1.00, 1.05, 0.85, 0.70)


def _fechas(cuantas: int, desde: date, hasta: date, corte: date, antes: int | None, rng):
    """
    Reparte las compras en el calendario.

    Por defecto el reparto es **uniforme en el tiempo**, y el tramo al que
    pertenece cada compra lo decide su fecha frente al corte. Es lo único
    defendible: el modelo de fraude no atrae clientes ni vende nada, así que la
    tienda no puede pasar de doscientas compras al mes a dos mil el día que se
    enciende. Una gráfica con ese salto no enseña que el sistema funciona,
    enseña que los datos están puestos a mano.

    La versión anterior repartía por cuenta —tantas antes del corte, tantas
    después— y con ello se podía concentrar tráfico donde interesaba medir. Se
    medía mejor y se mentía en el gráfico. `--antes` sigue existiendo para esa
    corrida forzada, pero ya no es lo que ocurre si no se pide.

    Dentro de cada día la hora se sortea entre las 8 y las 23, porque una
    tienda no vende de madrugada.
    """
    dias = [desde + timedelta(days=i) for i in range((hasta - desde).days + 1)]

    if antes is None:
        # Uniforme sobre todo el rango, con el peso de cada día de la semana.
        pesos = np.array(
            [PESO_POR_DIA_DE_LA_SEMANA[d.weekday()] for d in dias], dtype=float
        )
        elegidos = rng.choice(len(dias), size=cuantas, p=pesos / pesos.sum())
        sorteados = [dias[i] for i in elegidos]
    else:
        # Reparto forzado: tantas compras a cada lado del corte.
        previos = [d for d in dias if d < corte] or [desde]
        posteriores = [d for d in dias if d >= corte] or [hasta]
        sorteados = [
            previos[int(rng.integers(len(previos)))] if i < antes
            else posteriores[int(rng.integers(len(posteriores)))]
            for i in range(cuantas)
        ]

    momentos = [
        datetime.combine(
            dia,
            time(
                hour=int(rng.integers(8, 23)),
                minute=int(rng.integers(0, 60)),
                second=int(rng.integers(0, 60)),
            ),
            tzinfo=timezone.utc,
        )
        for dia in sorteados
    ]
    momentos.sort()
    return momentos


def _cobro(es_fraude: bool, nombre_del_titular: str, momento: datetime, rng) -> dict:
    """
    Con qué se pagó una compra que el sistema dejó pasar.

    Son datos simulados, como el resto del tráfico, pero con la misma forma que
    los que deja un cobro real: medio, cuatro últimos dígitos, titular y hora.
    Sin ellos, mil pedidos completados aparecerían en el panel como «sin
    cobrar», que es una incoherencia que salta a la vista.

    Solo cuatro dígitos, igual que en producción: aquí tampoco existe un número
    de tarjeta completo que pudiera acabar guardado por descuido.
    """
    medios = [m for m, _ in MEDIOS_DE_PAGO]
    pesos = np.array([p for _, p in MEDIOS_DE_PAGO], dtype=float)
    medio = medios[int(rng.choice(len(medios), p=pesos / pesos.sum()))]

    if medio == "yape":
        # Un monedero no tiene tarjeta ni titular que enseñar.
        return {
            "payment_id": f"SIM-{int(rng.integers(10**9, 10**10))}",
            "payment_method": medio,
            "card_last_four": None,
            "card_holder": None,
            "paid_at": momento + timedelta(minutes=float(rng.exponential(6))),
        }

    otra_persona = rng.random() < TITULAR_DISTINTO[es_fraude]
    titular = (
        NOMBRES_DE_TITULARES[int(rng.integers(len(NOMBRES_DE_TITULARES)))]
        if otra_persona
        else nombre_del_titular
    )

    return {
        "payment_id": f"SIM-{int(rng.integers(10**9, 10**10))}",
        "payment_method": medio,
        "card_last_four": f"{int(rng.integers(0, 10000)):04d}",
        "card_holder": titular,
        "paid_at": momento + timedelta(minutes=float(rng.exponential(6))),
    }


def _tiempo_de_deteccion_manual(rng) -> float:
    """
    Cuánto tarda una persona en mirar un pedido que la regla marcó, en ms.

    Es el «tiempo de detección» del sistema anterior. Va en milisegundos como
    el del modelo —es la misma columna y el mismo indicador— aunque la magnitud
    sea otra por completo: horas frente a un milisegundo y pico. Esa distancia
    es justamente lo que el indicador tiene que enseñar.
    """
    segundos = float(rng.lognormal(REVISION_MANUAL_MU, REVISION_MANUAL_SIGMA))
    segundos = min(max(segundos, REVISION_MANUAL_MINIMA_S), REVISION_MANUAL_MAXIMA_S)
    return round(segundos * 1000.0, 3)


def _ya_se_sabe(dias: float, rng) -> bool:
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


# ── El sistema anterior: una regla fija, sin modelo ──────────────────────────
#
# Es lo que hace una tienda antes de tener un modelo: unos cuantos `if` sobre
# el importe y las señales más evidentes. Existe aquí para que el tramo
# anterior del historial **no use el modelo en absoluto** y la mejora que
# aparezca sea atribuible al aprendizaje automático, no a haber movido dos
# umbrales.
#
# Comparar 0.30/0.70 contra 0.35/0.80 —que es lo que hacía este script antes—
# tiene al modelo en las dos mitades: mide el efecto de elegir mejor el corte,
# que es real pero es otra cosa, y por eso la detección salía plana.
MONTO_SOSPECHOSO = 1500.0
ARTICULOS_SOSPECHOSOS = 2


def _decidir_con_la_regla(
    monto: float, articulos_de_riesgo: int, direccion_nueva: bool
) -> str:
    """La decisión del sistema anterior, sin puntaje ni modelo de por medio."""
    if monto > MONTO_SOSPECHOSO and direccion_nueva:
        return "BLOCKED"
    if monto > MONTO_SOSPECHOSO or articulos_de_riesgo >= ARTICULOS_SOSPECHOSOS:
        return "REVIEW"
    return "APPROVED"


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


def _titular_de(usuario) -> str:
    """
    Cómo figura el nombre en la tarjeta de esa persona.

    En una tarjeta va la inicial y el apellido en mayúsculas, no el nombre
    completo de la cuenta. Importa para que la comparación con el titular
    tenga sentido visual: si el panel enseñara «María Quispe» en la cuenta y
    «MARIA QUISPE» en la tarjeta, parecerían distintos sin serlo.
    """
    partes = usuario.full_name.split()
    if len(partes) < 2:
        return usuario.full_name.upper()
    return f"{partes[0][0]}. {partes[-1]}".upper()


def _cuantas_compras(rng) -> int:
    """Cuántas veces compra un cliente, según el reparto declarado arriba."""
    valores = [v for v, _ in COMPRAS_POR_CLIENTE]
    pesos = np.array([p for _, p in COMPRAS_POR_CLIENTE], dtype=float)
    return int(valores[int(rng.choice(len(valores), p=pesos / pesos.sum()))])


class SesionDeEnsayo:
    """
    Se traga las escrituras y deja pasar las lecturas.

    Sirve para el ensayo: la generación necesita leer el catálogo de la base,
    pero no debe escribir nada. Envolver la sesión de verdad —en lugar de
    sembrar de `if ensayo:` todo el bucle— mantiene una sola versión del código
    que genera, que es lo que garantiza que el ensayo y la corrida real
    produzcan exactamente los mismos números.
    """

    def __init__(self, sesion):
        self._sesion = sesion
        self.escrituras = 0

    def add(self, _fila):
        self.escrituras += 1

    async def flush(self):
        return None

    async def commit(self):
        return None

    def __getattr__(self, nombre):
        # `execute`, `scalars` y demás lecturas van a la sesión de verdad.
        return getattr(self._sesion, nombre)


def _guardar_manifiesto(correos: list[str]) -> Path:
    """
    Deja por escrito qué cuentas creó esta corrida.

    Desde que los correos usan proveedores reales, nada distingue a estas
    cuentas de un cliente de verdad —que es justo lo que se buscaba—, así que
    la única forma honesta de poder retirarlas después es haber anotado cuáles
    son. `--limpiar` lee este archivo.
    """
    DIRECTORIO_INFORMES.mkdir(parents=True, exist_ok=True)
    destino = DIRECTORIO_INFORMES / NOMBRE_DEL_MANIFIESTO
    destino.write_text(
        json.dumps(
            {"generado_en": datetime.now(timezone.utc).isoformat(), "correos": correos},
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return destino


def _leer_manifiesto() -> list[str]:
    """Los correos que dejó la última generación, o una lista vacía."""
    archivo = DIRECTORIO_INFORMES / NOMBRE_DEL_MANIFIESTO
    if not archivo.exists():
        return []
    try:
        return list(json.loads(archivo.read_text(encoding="utf-8")).get("correos", []))
    except (OSError, json.JSONDecodeError):
        return []


def _cuenta_nueva(usados: set, rol, rng, ensayo: bool = False) -> User:
    """Una cuenta con nombre verosímil de Trujillo y correo sin repetir."""
    nombre = NOMBRES[int(rng.integers(len(NOMBRES)))]
    apellido = APELLIDOS[int(rng.integers(len(APELLIDOS)))]
    base = f"{nombre}.{apellido}".lower()
    base = (
        base.replace("á", "a").replace("é", "e").replace("í", "i")
        .replace("ó", "o").replace("ú", "u").replace("ñ", "n")
    )

    # El proveedor se sortea, y el desempate va antes de la arroba —como hace
    # la gente cuando su nombre ya está cogido— en vez de después.
    dominio = DOMINIOS[int(rng.integers(len(DOMINIOS)))]
    correo = f"{base}@{dominio}"
    sufijo = 1
    while correo in usados:
        sufijo += 1
        correo = f"{base}{sufijo}@{dominio}"
    usados.add(correo)

    return User(
        # El identificador se fija aquí, igual que en los pedidos. Sin él,
        # `usuario.id` es None hasta que la sesión hace `flush()`, y el conjunto
        # que evita refechar una cuenta ya fechada se llenaba de `None`: la
        # primera compra entraba y todas las demás creían que su cliente ya
        # tenía fecha. En la corrida real no se notaba porque el `flush()` de
        # las cuentas ocurre antes del bucle; en cuanto se quitó —para poder
        # ensayar sin escribir— quedó a la vista.
        id=str(uuid.uuid4()),
        email=correo,
        # En el ensayo no se guarda nada, así que hashear cuesta minutos para
        # tirarlos: cuatro mil cuentas con bcrypt son casi todo el tiempo de una
        # corrida. La contraseña solo importa cuando la cuenta va a existir.
        hashed_password=("(ensayo)" if ensayo else hash_password(CLAVE_DEL_CLIENTE)),
        full_name=f"{nombre} {apellido}",
        phone=f"9{int(rng.integers(10**8)):08d}",
        role=rol,
    )


async def _crear_clientes(
    sesion, compras_totales: int, rng, cuentas: int, administradores: int,
    ensayo: bool = False,
) -> tuple[list, list]:
    """
    Crea exactamente `cuentas` cuentas y reparte las compras entre ellas.

    Devuelve `(reparto, admins)`. `reparto` tiene una entrada por compra —el
    cliente al que le toca—, ya barajada, así el bucle principal solo va
    sacando de ahí y las compras de un mismo cliente quedan repartidas en el
    tiempo, que es como ocurre de verdad: nadie hace sus nueve pedidos el mismo
    martes.

    El número de cuentas se fija de antemano en lugar de salir de la cuenta de
    compras. Con el reparto declarado en COMPRAS_POR_CLIENTE la cifra emergente
    quedaba cerca pero nunca redonda, y «¿cuántos clientes tiene la tienda?» es
    una pregunta que se responde mejor con un número que se eligió que con uno
    que salió.

    Los administradores son personal de la tienda, no clientes: se crean, se
    ven en Panel → Usuarios con su rol, y no compran. Un administrador con un
    pedido que acabó en contracargo es un artefacto raro de explicar y no
    aporta nada a lo que el historial viene a enseñar.

    Antes todo el historial colgaba de un único usuario ficticio. Mil
    cuatrocientas compras de la misma persona no se sostienen ni un segundo en
    una pantalla, y además dejaban sin sentido cualquier señal que dependa del
    cliente: cuántas veces ha comprado antes o cuándo abrió la cuenta.
    """
    if administradores >= cuentas:
        raise ValueError(
            f"Se pidieron {administradores} administradores de {cuentas} cuentas: "
            "tiene que quedar alguien que compre."
        )

    usados: set = set()
    admins = [
        _cuenta_nueva(usados, UserRole.ADMIN, rng, ensayo)
        for _ in range(administradores)
    ]
    compradores = [
        _cuenta_nueva(usados, UserRole.CLIENTE, rng, ensayo)
        for _ in range(cuentas - administradores)
    ]
    for cuenta in admins + compradores:
        sesion.add(cuenta)

    # Cada comprador estrena con una compra —una cuenta sin un solo pedido no
    # se distingue de un registro abandonado— y a partir de ahí se le suman las
    # que le toquen según el reparto declarado.
    veces = {id(c): 1 for c in compradores}
    asignadas = len(compradores)
    if asignadas > compras_totales:
        raise ValueError(
            f"No caben {cuentas - administradores} compradores en "
            f"{compras_totales} compras: cada uno necesita al menos una."
        )

    for comprador in compradores:
        if asignadas >= compras_totales:
            break
        extra = min(_cuantas_compras(rng) - 1, compras_totales - asignadas)
        if extra > 0:
            veces[id(comprador)] += extra
            asignadas += extra

    # Si el reparto se quedó corto, las que faltan van a compradores al azar:
    # así el total cuadra exacto sin deformar la forma de la distribución.
    while asignadas < compras_totales:
        elegido = compradores[int(rng.integers(len(compradores)))]
        veces[id(elegido)] += 1
        asignadas += 1

    reparto = [c for c in compradores for _ in range(veces[id(c)])]

    await sesion.flush()
    rng.shuffle(reparto)
    return reparto, admins


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
    cuantas: int,
    antes: int | None,
    desde: date,
    hasta: date,
    corte: date,
    semilla: int,
    linea_base: str = "regla",
    cuentas: int = 500,
    administradores: int = 5,
    ensayo: bool = False,
) -> dict:
    # El mismo generador que `ml/dataset.py`: si el tráfico ha de venir de la
    # misma distribución, también el sorteo.
    rng = np.random.default_rng(semilla)

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
        "linea_base": linea_base,
        "desde": desde,
        "hasta": hasta,
        "sin_etiquetar": 0,
    }

    async with AsyncSessionLocal() as sesion_real:
        # En el ensayo, la envoltura se traga las escrituras y deja pasar las
        # lecturas. El código que genera es el mismo en los dos casos, que es
        # lo que hace que el ensayo prediga la corrida de verdad.
        sesion = SesionDeEnsayo(sesion_real) if ensayo else sesion_real

        reparto, admins = await _crear_clientes(
            sesion, len(momentos), rng, cuentas, administradores, ensayo
        )
        caros, normales = await _catalogo(sesion)
        resumen["clientes"] = len({c.email for c in reparto})
        resumen["administradores"] = len(admins)
        resumen["cuentas"] = resumen["clientes"] + len(admins)
        # Se anota antes de empezar a insertar pedidos: si la corrida se
        # interrumpe a mitad, la lista de cuentas creadas ya está en disco y
        # `--limpiar` puede retirarlas.
        if not ensayo:
            resumen["manifiesto"] = str(
                _guardar_manifiesto(
                    sorted({c.email for c in reparto} | {a.email for a in admins})
                )
            )
        cuentas_fechadas: set = set()
        # El día que abrió la tienda: el primero del rango pedido.
        apertura = datetime.combine(desde, time.min, tzinfo=timezone.utc)

        for indice, momento in enumerate(momentos):
            usuario = reparto[indice]
            # El fraude se concentra en la primera compra de una cuenta, que es
            # como ocurre: se abre una cuenta, se golpea una vez y no se vuelve.
            # Un cliente que ya compró y volvió es casi siempre honesto.
            #
            # Sortearlo con la misma probabilidad en todas las compras, como
            # hacía la versión anterior, producía algo que no existe: cuentas
            # con meses de historial que un día «defraudan» y al siguiente
            # vuelven a comprar bien. Además rompía la señal de la antigüedad
            # —el fraude aparecía repartido por igual entre cuentas nuevas y
            # viejas— y con ella el modelo perdía ocho puntos de detección.
            estrena = usuario.id not in cuentas_fechadas
            es_fraude = bool(
                rng.random()
                < (TASA_EN_LA_PRIMERA_COMPRA if estrena else TASA_EN_LAS_SIGUIENTES)
            )
            muestra = _muestra(es_fraude, rng)
            lineas = _armar_carrito(muestra, caros, normales, rng)

            # El ruido de etiqueta va después de generar el comportamiento: la
            # compra se comportó como su clase, pero lo que acabó constando es
            # lo contrario. Es lo que pasa cuando un fraude no se denuncia o
            # cuando alguien reclama un cargo que sí hizo.
            if rng.random() < RUIDO_DE_ETIQUETA:
                es_fraude = not es_fraude

            total = sum(l["producto"].price * l["cantidad"] for l in lineas)
            de_riesgo = sum(l["cantidad"] for l in lineas if l["producto"] in caros)
            direccion = DIRECCIONES_NUEVAS[rng.integers(len(DIRECCIONES_NUEVAS))] if muestra[
                "direccion_nueva"
            ] else DIRECCIONES_HABITUALES[rng.integers(len(DIRECCIONES_HABITUALES))]

            # Cuándo abrió la cuenta este cliente. Se decide una sola vez, la
            # primera vez que aparece, y como los momentos vienen ordenados esa
            # primera vez es su compra más antigua: la cuenta queda abierta
            # justo antes de estrenarla.
            #
            # La antigüedad depende de esa primera compra. Quien entra a
            # defraudar suele hacerlo con una cuenta recién creada; quien
            # compra de verdad lleva meses.
            #
            # Fijarla en cada compra, como hacía la primera versión, daba lo
            # contrario de lo que se pretendía: un cliente con nueve pedidos
            # acababa con la fecha más antigua de las nueve, y las cuentas de
            # los defraudadores salían más viejas que las de los clientes
            # honestos.
            if usuario.id not in cuentas_fechadas:
                dias = float(rng.exponential(ANTIGUEDAD_MEDIA_DIAS[es_fraude]))
                alta = momento - timedelta(days=dias + 0.2)
                # Ninguna cuenta puede ser anterior a la apertura de la tienda.
                # Sin este tope, una compra de enero con la antigüedad media de
                # un cliente honesto daba una cuenta abierta el año pasado, en
                # una tienda que no existía.
                usuario.created_at = max(alta, apertura)
                cuentas_fechadas.add(usuario.id)

            # Y la antigüedad que ve el modelo es la de ESTA compra, no la del
            # estreno: un cliente que vuelve en marzo lleva dos meses más que
            # cuando compró en enero, y ésa es justo la señal.
            antiguedad = max(
                0.0, (momento - usuario.created_at).total_seconds() / 86400
            )

            # El modelo de verdad, evaluando esta compra.
            evaluacion = fraud_service.evaluar(
                total_amount=total,
                high_risk_items_count=de_riesgo,
                checkout_duration_seconds=muestra["segundos"],
                is_new_shipping_address=1 if muestra["direccion_nueva"] else 0,
                account_age_days=antiguedad,
            )

            tramo = "antes" if momento.date() < corte else "despues"
            if tramo == "antes" and linea_base == "regla":
                decision = _decidir_con_la_regla(
                    total, de_riesgo, muestra["direccion_nueva"]
                )
                # El puntaje se registra igual, calculado a posteriori: no lo
                # usó nadie para decidir, pero permite enseñar en el panel qué
                # habría hecho el modelo con esa misma compra.
                explicacion = (
                    "Decidido por la regla fija anterior al modelo "
                    f"(monto > S/ {MONTO_SOSPECHOSO:,.0f} o "
                    f"{ARTICULOS_SOSPECHOSOS}+ artículos de alto riesgo)."
                )
                # Y el tiempo que se guarda es el del sistema que decidió, no
                # el del modelo al que nadie preguntó: lo que tardó una persona
                # en llegar a este pedido en la cola de revisión.
                milisegundos = _tiempo_de_deteccion_manual(rng)
            else:
                aprobar, bloquear = umbrales[tramo]
                decision = _decidir(evaluacion.puntaje, aprobar, bloquear)
                explicacion = evaluacion.explicacion
                milisegundos = round(evaluacion.milisegundos, 3)

            orden = Order(
                # El identificador se fija aquí en vez de dejar que lo ponga la
                # base al insertar. Parece un detalle y no lo es: sin él hay que
                # hacer `flush()` después de cada pedido para conocer su id y
                # poder colgarle sus líneas y su evaluación, y eso son tantos
                # viajes a la base como pedidos. Contra PostgreSQL en la nube,
                # cinco mil viajes son más de una hora; fijándolo, todo se
                # acumula en memoria y viaja junto al confirmar.
                id=str(uuid.uuid4()),
                user_id=usuario.id,
                total_amount=round(total, 2),
                status=ESTADO_SEGUN_DECISION[decision],
                shipping_address=direccion,
                shipping_city="Trujillo",
                created_at=momento,
            )
            # Solo se cobra lo que el sistema dejó pasar. Un pedido bloqueado o
            # retenido nunca llegó a la pasarela, así que no puede tener
            # tarjeta: enseñarle una sería la incoherencia más fácil de pillar.
            if decision == "APPROVED":
                for campo, valor in _cobro(
                    es_fraude, _titular_de(usuario), momento, rng
                ).items():
                    setattr(orden, campo, valor)
            sesion.add(orden)

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
                    float(rng.exponential(DIAS_MEDIOS_HASTA_SABERLO)),
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
                        "checkout_duration_seconds": round(muestra["segundos"], 1),
                        "is_new_shipping_address": 1 if muestra["direccion_nueva"] else 0,
                        "account_age_days": round(antiguedad, 2),
                    },
                    decision=decision,
                    risk_level=evaluacion.nivel_de_riesgo,
                    explanation=explicacion,
                    contributions=evaluacion.aportes,
                    detection_time_ms=milisegundos,
                    evaluated_at=momento,
                    reviewed_at=revisado_el if resuelto else None,
                    is_actual_fraud=es_fraude if resuelto else None,
                )
            )

            cuenta = resumen[tramo]
            cuenta["compras"] += 1
            cuenta[decision] += 1
            # Se acumula para poder dar el tiempo medio de cada tramo en el
            # informe: es el tercero de los indicadores de la tesis y hasta
            # ahora no aparecía por ninguna parte.
            cuenta["suma_ms"] += milisegundos
            if es_fraude:
                cuenta["fraudes"] += 1
                if resuelto:
                    cuenta["fraudes_resueltos"] += 1
                    if decision in ("REVIEW", "BLOCKED"):
                        cuenta["detectados"] += 1
                    else:
                        # El fraude que se aprobó: es el numerador del segundo
                        # indicador, y hasta ahora solo se sumaba su importe.
                        cuenta["no_detectados"] += 1
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


def _duracion(milisegundos: float) -> str:
    """
    Un tiempo de detección escrito para leer, sea cual sea su magnitud.

    Los dos tramos viven en escalas que no se parecen —horas de cola de
    revisión frente a poco más de un milisegundo del modelo—, y forzar los dos
    a «ms» daría «12,600,000.0 ms», que no dice nada a nadie.
    """
    if milisegundos < 1000:
        return f"{milisegundos:,.1f} ms"
    segundos = milisegundos / 1000
    if segundos < 60:
        return f"{segundos:,.1f} s"
    minutos = segundos / 60
    if minutos < 60:
        return f"{minutos:,.0f} min"
    return f"{minutos / 60:,.1f} h"


def _tiempo_medio(cuenta: Counter) -> str:
    return _duracion(cuenta["suma_ms"] / cuenta["compras"]) if cuenta["compras"] else "sin datos"


def _informe(resumen: dict, desde: date, hasta: date) -> str:
    antes, despues = resumen["antes"], resumen["despues"]
    (ap_antes, bl_antes) = resumen["umbrales"]["antes"]
    (ap_desp, bl_desp) = resumen["umbrales"]["despues"]

    perdida_antes = antes["perdida"] + antes["venta_perdida"]
    perdida_despues = despues["perdida"] + despues["venta_perdida"]

    if resumen["linea_base"] == "regla":
        criterio_antiguo = (
            "una regla fija sin modelo (bloquear si el monto pasa de "
            f"S/ {MONTO_SOSPECHOSO:,.0f} y la dirección es nueva; revisar si "
            f"pasa de ese monto o lleva {ARTICULOS_SOSPECHOSOS} o más "
            "artículos de alto riesgo)"
        )
    else:
        criterio_antiguo = (
            "el mismo modelo con los umbrales escritos a mano "
            f"({ap_antes} / {bl_antes})"
        )

    lineas = [
        "# Historial simulado de la tienda\n",
        f"{antes['compras'] + despues['compras']} compras repartidas entre el "
        f"{desde:%d/%m/%Y} y el {hasta:%d/%m/%Y}, evaluadas una por una por el "
        "modelo que está en producción.\n",
        f"El tramo antiguo decide con {criterio_antiguo}; el nuevo, con el "
        f"modelo y los umbrales que el entrenamiento eligió minimizando el "
        f"costo en soles ({ap_desp} / {bl_desp}). El tráfico se genera igual "
        "en los dos: lo único que cambia es el criterio de decisión.\n",
        "## Los tres indicadores\n",
        "Son los que mide la tesis. El corte es la entrada del modelo; a la "
        "izquierda, cómo operaba la tienda antes.\n",
        "El reparto de compras entre los dos tramos no sigue al calendario, y "
        "conviene decirlo en vez de dejar que se deduzca del gráfico. Las tasas "
        "se calculan solo sobre los fraudes ya confirmados, y en el tramo nuevo "
        "—que son semanas, no meses— muchos contracargos aún no han llegado: "
        "hace falta más tráfico para terminar con la misma cantidad de casos "
        "comprobados. Por eso el tramo nuevo lleva más compras y mayor densidad "
        "diaria. Lo que se iguala no son las compras, sino los casos sobre los "
        "que se puede medir.\n",
        "Las dos tasas de arriba se dividen entre los fraudes confirmados: son "
        "la exhaustividad del modelo. Los indicadores DTF y NFND que enseña el "
        "panel dividen entre el total de transacciones, así que sus valores son "
        "mucho menores —su techo es la propia tasa de fraude de la tienda— y no "
        "hay que confundir unos con otros.\n",
        "| Indicador | Antes | Después | Debe |",
        "| :--- | ---: | ---: | :---: |",
        f"| Tasa de fraudes detectados | {_tasa(antes, 'detectados', 'fraudes_resueltos')} "
        f"| **{_tasa(despues, 'detectados', 'fraudes_resueltos')}** | subir |",
        f"| Tasa de fraude no detectado | {_tasa(antes, 'no_detectados', 'fraudes_resueltos')} "
        f"| **{_tasa(despues, 'no_detectados', 'fraudes_resueltos')}** | bajar |",
        f"| Tiempo de detección | {_tiempo_medio(antes)} "
        f"| **{_tiempo_medio(despues)}** | bajar |\n",
        "El tiempo de detección no compara dos clasificadores: compara **no "
        "tener detector** con tenerlo. Antes del modelo la regla fija solo "
        "levantaba la mano y quien decidía era una persona, cuando le llegaba "
        "el turno en la cola de revisión; ese es el tiempo de la izquierda. El "
        "de la derecha lo cronometra el propio servicio al puntuar cada "
        "compra, una por una, dentro de la petición que crea el pedido.\n",
        "## Las cuentas\n",
        f"{resumen.get('cuentas', 0)} cuentas con nombres, teléfonos y correos "
        f"como los de cualquier cliente de Trujillo "
        f"({', '.join('@' + d for d in DOMINIOS)}). "
        f"{resumen.get('administradores', 0)} de ellas son "
        f"administradores —personal de la tienda, se ven en Panel → Usuarios "
        f"con su rol y no compran— y las otras "
        f"{resumen.get('clientes', 0)} son los clientes entre los que se "
        "reparten las compras: la mayoría compra una sola vez, unos pocos son "
        "habituales con nueve pedidos.\n",
        "## El detalle\n",
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
        "\nLas compras que el sistema dejó pasar llevan además datos de cobro "
        "simulados —medio de pago, cuatro últimos dígitos y titular—, con la "
        "misma forma que los que deja un pago real. En una parte de ellas el "
        "titular no coincide con el de la cuenta: es la señal más común de "
        "tarjeta robada, y ninguna de las cuatro variables del modelo la ve, "
        "así que solo puede verla la persona que revisa.\n"
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
    riesgo.

    Todo lo que crea el script cuelga de cuentas con el dominio de correo
    reservado para la simulación, así que basta con seguir esa cuerda: sus
    evaluaciones, las líneas de sus pedidos, sus pedidos y por último las
    propias cuentas. Ninguna fila de un cliente real entra en el filtro, porque
    ningún cliente real tiene ese dominio.
    """
    async with AsyncSessionLocal() as sesion:
        simulados = (
            (
                await sesion.execute(
                    select(User.id).where(
                        or_(
                            User.email.in_(_leer_manifiesto() or ["(sin manifiesto)"]),
                            # Las dos formas que usaron las versiones
                            # anteriores, para poder retirar lo que dejaron.
                            User.email.like(f"%@{DOMINIO_ANTIGUO}"),
                            User.email == CORREO_DEL_CLIENTE_ANTIGUO,
                        )
                    )
                )
            )
            .scalars()
            .all()
        )
        if not simulados:
            print("No hay nada que limpiar: no existe ninguna cuenta simulada.")
            return 0

        pedidos = (
            (
                await sesion.execute(
                    select(Order.id).where(Order.user_id.in_(simulados))
                )
            )
            .scalars()
            .all()
        )

        if pedidos:
            await sesion.execute(delete(FraudLog).where(FraudLog.order_id.in_(pedidos)))
            await sesion.execute(delete(OrderItem).where(OrderItem.order_id.in_(pedidos)))
            await sesion.execute(delete(Order).where(Order.id.in_(pedidos)))
        await sesion.execute(delete(User).where(User.id.in_(simulados)))
        await sesion.commit()

    print(
        f"Borrados {len(pedidos)} pedidos simulados, sus evaluaciones y "
        f"{len(simulados)} cuentas."
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cuantas",
        type=int,
        default=8000,
        help=(
            "Cuántas compras generar. Cinco mil no es capricho: una tasa se "
            "calcula sobre los fraudes confirmados del período, y con mil "
            "compras cada día tenía uno o dos, así que la tasa diaria solo "
            "podía salir 0 %, 50 % o 100 %. Con este volumen cada semana lleva "
            "entre treinta y cincuenta casos y el indicador se mueve en una "
            "banda creíble en vez de saltar entre extremos."
        ),
    )
    parser.add_argument(
        "--antes",
        type=int,
        default=None,
        help=(
            "Fuerza cuántas compras caen antes del corte. Sin esto —que es lo "
            "normal— el tráfico se reparte uniforme por el calendario y el "
            "tramo de cada compra lo decide su fecha, que es lo único "
            "defendible: encender el modelo no atrae clientes, así que la "
            "tienda no puede multiplicar sus ventas el día que se enciende. "
            "Usarlo concentra casos donde interesa medir, a cambio de un "
            "gráfico de ventas que nadie se cree."
        ),
    )
    parser.add_argument("--desde", type=date.fromisoformat, default=date(2026, 1, 1))
    parser.add_argument("--hasta", type=date.fromisoformat, default=date(2026, 9, 7))
    parser.add_argument(
        "--cambio",
        type=date.fromisoformat,
        default=date(2026, 8, 1),
        help="Fecha en que entra el modelo: antes decide el sistema anterior",
    )
    parser.add_argument(
        "--cuentas",
        type=int,
        default=4000,
        help=(
            "Cuántas cuentas de cliente crear. Las compras se reparten entre "
            "ellas, así que tiene que haber menos cuentas que compras: cada "
            "comprador estrena con al menos un pedido."
        ),
    )
    parser.add_argument(
        "--administradores",
        type=int,
        default=5,
        help=(
            "Cuántas de esas cuentas son administradores. Son personal de la "
            "tienda: se ven en Panel → Usuarios con su rol y no compran."
        ),
    )
    parser.add_argument(
        "--ensayo",
        action="store_true",
        help=(
            "Genera y mide sin escribir nada: mismo tráfico, mismo modelo, "
            "mismos números, pero sin crear cuentas ni pedidos. Tarda segundos "
            "en vez de minutos porque se salta el hasheo de contraseñas y los "
            "viajes a la base. Sirve para ver qué va a producir una "
            "configuración antes de comprometerla."
        ),
    )
    parser.add_argument("--semilla", type=int, default=2026)
    parser.add_argument(
        "--linea-base",
        choices=("regla", "umbrales"),
        default="regla",
        dest="linea_base",
        help=(
            "Con qué decide el tramo anterior: 'regla' es el sistema sin "
            "modelo (por defecto) y 'umbrales' es el mismo modelo con los "
            "umbrales viejos"
        ),
    )
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
    if args.antes is not None and args.antes > args.cuantas:
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
            args.cuantas,
            args.antes,
            args.desde,
            args.hasta,
            corte,
            args.semilla,
            args.linea_base,
            args.cuentas,
            args.administradores,
            args.ensayo,
        )
    )

    informe = _informe(resumen, args.desde, args.hasta)
    print(informe)

    if args.ensayo:
        # El informe de un ensayo no se guarda: sobrescribir el del historial
        # que sí está en la base dejaría el documento describiendo unos datos
        # que nadie puede consultar.
        print(
            "\nEnsayo: no se escribió nada. Estos son los números que dará la "
            "corrida de verdad con esta misma configuración y semilla."
        )
        return 0

    DIRECTORIO_INFORMES.mkdir(parents=True, exist_ok=True)
    destino = DIRECTORIO_INFORMES / "historial_simulado.md"
    destino.write_text(informe, encoding="utf-8")

    print(f"\nInforme escrito en {destino}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
