"""
Pasarela de pago simulada.

La tienda tiene integradas dos pasarelas reales —MercadoPago y Niubiz— y
ninguna de las dos quedó utilizable: MercadoPago rechazaba los cobros sin llegar
a registrar el pago, y Niubiz exige una afiliación comercial y una sesión de
certificación antes de entregar credenciales de producción. Como lo que este
trabajo demuestra es la **detección de fraude**, y no el cobro, el cobro se
simula.

La regla que gobierna este archivo entero: **simular sí, fingir no.**

Una simulación honesta dice que lo es. Esta lo dice en los tres sitios donde
alguien podría mirar: la pantalla del checkout avisa de que no se hará ningún
cargo, la orden guarda `payment_gateway = "simulado"` —así que el panel de
administración distingue para siempre un pedido simulado de uno cobrado de
verdad— y `/health` informa de que la tienda está en modo simulado. Si algún día
se vuelve a una pasarela real, los pedidos viejos siguen sabiendo lo que fueron.

Lo que **no** se simula es nada de lo que sustenta la tesis. El modelo evalúa el
pedido de verdad antes de llegar aquí, y el resultado de este cobro entra por el
mismo sitio que entraría el de una pasarela real —
`order_service.registrar_resultado_del_pago`—, así que la máquina de estados que
completa un pedido, lo retiene por orden del modelo o lo cancela y devuelve el
stock es exactamente la misma. Se sustituye la pasarela, no el sistema.

Y se comporta como una pasarela de verdad en lo que se puede comprobar: valida
el número con el algoritmo de Luhn —el mismo que usa la industria—, comprueba
que la tarjeta no esté vencida, y aprueba o rechaza según tarjetas de prueba
documentadas, como hacen los entornos de prueba de Visa, Stripe o MercadoPago.
No aprueba cualquier cosa que se le escriba.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

# Tarjetas con comportamiento fijo, para poder enseñar los dos desenlaces en una
# demostración sin depender de la suerte. Son los números que la industria usa
# como ejemplo: válidos según Luhn, pero sin emisor detrás.
#
# Cada una lleva su código de respuesta, porque una pasarela real no contesta
# «no» a secas: devuelve un código que dice por qué, y de ese código depende lo
# que la tienda hace después. Los que se usan aquí son los de la norma ISO 8583,
# que es la que hablan las redes de tarjetas.
TARJETAS_DE_PRUEBA = {
    "4111111111111111": ("aprobada", "visa", "00"),
    "5500000000000004": ("aprobada", "master", "00"),
    # Estas dos existen para poder demostrar el camino del rechazo: qué le pasa
    # al pedido y al inventario cuando un cobro no prospera.
    "4000000000000002": ("rechazada: fondos insuficientes", "visa", "51"),
    "5105105105105100": ("rechazada: tarjeta reportada", "master", "43"),
}

# Y los códigos de lo que ni siquiera llega al emisor, porque lo descarta antes
# el propio formulario.
CODIGO_NUMERO_INVALIDO = "14"
CODIGO_VENCIDA = "54"
CODIGO_CVV = "82"
CODIGO_APROBADO = "00"


@dataclass
class ResultadoSimulado:
    """Lo que la pasarela simulada decidió sobre un intento de cobro."""

    aprobado: bool
    # El motivo cuando no se aprueba, para enseñárselo a quien está comprando.
    # Una pasarela real tampoco dice más que esto.
    motivo: Optional[str] = None
    # Solo se conservan los cuatro últimos dígitos, igual que con una pasarela
    # real. El número completo no se guarda ni se registra en ningún log aunque
    # aquí no haya dinero de por medio: la costumbre es lo que evita el
    # accidente el día que sí lo haya.
    ultimos_cuatro: Optional[str] = None
    marca: Optional[str] = None
    titular: Optional[str] = None
    # El código de respuesta, como el que devuelve una pasarela real. "00" es
    # aprobado; cualquier otro dice por qué no. Se enseña en pantalla porque es
    # lo que un comercio de verdad apunta cuando un cliente llama a preguntar.
    codigo: Optional[str] = None
    # Si el «no» vino del emisor de la tarjeta o del formulario, que no es lo
    # mismo y el pedido no corre la misma suerte. Una tarjeta rechazada es una
    # compra que no va a completarse: el pedido se cancela y el inventario
    # vuelve. Un número mal escrito es alguien que todavía está intentándolo, y
    # cancelarle el pedido por una errata sería absurdo.
    es_rechazo_del_emisor: bool = False


def _solo_digitos(texto: str) -> str:
    return "".join(c for c in (texto or "") if c.isdigit())


def luhn_valido(numero: str) -> bool:
    """
    El algoritmo de Luhn, que es el que usan las tarjetas de verdad.

    Se duplica cada segundo dígito empezando por la derecha, se restan nueve a
    los resultados que pasen de nueve, y la suma total tiene que ser múltiplo de
    diez. No comprueba que la tarjeta exista —eso solo lo sabe el emisor— pero sí
    descarta un número tecleado al azar, que es justo lo que hace falta para que
    la simulación no apruebe cualquier cosa.
    """
    digitos = _solo_digitos(numero)
    if len(digitos) < 13 or len(digitos) > 19:
        return False

    suma = 0
    for posicion, caracter in enumerate(reversed(digitos)):
        valor = int(caracter)
        if posicion % 2 == 1:
            valor *= 2
            if valor > 9:
                valor -= 9
        suma += valor
    return suma % 10 == 0


def marca_de(numero: str) -> str:
    """
    De qué red es la tarjeta, por el primer dígito.

    Es la misma regla que usa cualquier formulario de pago para pintar el
    logotipo mientras se escribe: 4 es Visa, 5 es Mastercard, 3 es American
    Express.
    """
    digitos = _solo_digitos(numero)
    if digitos.startswith("4"):
        return "visa"
    if digitos.startswith("5"):
        return "master"
    if digitos.startswith("3"):
        return "amex"
    return "desconocida"


def _vencida(mes: int, anio: int) -> bool:
    """
    Si la tarjeta ya caducó.

    Una tarjeta vale hasta el último día de su mes, así que se compara contra el
    mes en curso y no contra el día de hoy.
    """
    ahora = datetime.now(timezone.utc)
    return (anio, mes) < (ahora.year, ahora.month)


def cobrar(
    *,
    numero: str,
    mes: int,
    anio: int,
    cvv: str,
    titular: str,
) -> ResultadoSimulado:
    """
    Decide si este cobro simulado prospera.

    Las comprobaciones van de la más barata a la más cara, igual que en una
    pasarela real: primero la forma del número, después la vigencia, y solo al
    final la decisión de la tarjeta concreta.

    Los dos «no» que puede devolver son distintos y el pedido no corre la misma
    suerte con cada uno, así que van marcados: mirar `es_rechazo_del_emisor`.
    """
    digitos = _solo_digitos(numero)

    if not luhn_valido(digitos):
        return ResultadoSimulado(
            False, "El número de tarjeta no es válido.", codigo=CODIGO_NUMERO_INVALIDO
        )

    if not (1 <= mes <= 12):
        return ResultadoSimulado(
            False, "El mes de vencimiento no existe.", codigo=CODIGO_VENCIDA
        )

    if _vencida(mes, anio):
        return ResultadoSimulado(
            False, "La tarjeta está vencida.", codigo=CODIGO_VENCIDA
        )

    if len(_solo_digitos(cvv)) not in (3, 4):
        return ResultadoSimulado(
            False, "El código de seguridad no es válido.", codigo=CODIGO_CVV
        )

    if not (titular or "").strip():
        return ResultadoSimulado(
            False, "Falta el nombre del titular.", codigo=CODIGO_CVV
        )

    marca = marca_de(digitos)
    ultimos = digitos[-4:]

    decision, marca_fija, codigo = TARJETAS_DE_PRUEBA.get(
        digitos, ("aprobada", marca, CODIGO_APROBADO)
    )

    if decision.startswith("rechazada"):
        # El motivo va sin el prefijo, que es de uso interno.
        return ResultadoSimulado(
            False,
            decision.split(":", 1)[1].strip().capitalize() + ".",
            ultimos_cuatro=ultimos,
            marca=marca_fija,
            titular=titular.strip(),
            codigo=codigo,
            es_rechazo_del_emisor=True,
        )

    return ResultadoSimulado(
        True,
        None,
        ultimos_cuatro=ultimos,
        marca=marca_fija,
        titular=titular.strip(),
        codigo=codigo,
    )


def datos_del_pago_simulado(resultado: ResultadoSimulado) -> dict:
    """
    Traduce el resultado a las columnas que guarda la orden.

    Devuelve las mismas claves que sus gemelas de MercadoPago y Niubiz, porque
    las tres pasarelas escriben en los mismos campos a través de
    `registrar_resultado_del_pago`. Que la simulada encaje sin una sola rama
    especial es la prueba de que sustituye a la pasarela y no al sistema.

    `payment_gateway` vale "simulado" y ese es el dato que impide que esto se
    confunda nunca con un cobro real, ni hoy en el panel ni dentro de un año
    mirando la base de datos.
    """
    return {
        # Un identificador con prefijo: si alguien lo busca en el panel de una
        # pasarela real no lo va a encontrar, y el prefijo le dice por qué.
        "payment_id": f"SIM-{datetime.now(timezone.utc):%Y%m%d%H%M%S}",
        "payment_method": resultado.marca,
        "payment_gateway": "simulado",
        "card_last_four": resultado.ultimos_cuatro,
        "card_holder": resultado.titular,
    }
