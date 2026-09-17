"""
Pruebas del cobro simulado.

La pasarela se simula; el sistema no. Lo que estas pruebas sujetan es
exactamente eso: que sustituir el cobro por una simulación no cambie **ninguna**
de las reglas que sustentan la tesis. El pedido que el modelo marcó para revisar
tiene que quedar retenido igual, el pedido con el cobro rechazado tiene que
devolver su inventario igual, y de la tarjeta tienen que sobrevivir los cuatro
últimos dígitos y nada más, igual.

La otra mitad es que la simulación no apruebe cualquier cosa. Una que dijera
«aprobado» a un número tecleado al azar no demostraría nada y no se podría
defender delante de nadie.
"""

from datetime import datetime, timezone

from app.models.fraud_log import FraudLog
from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.services import order_service
from app.services.pago_simulado import cobrar, luhn_valido, marca_de

from tests.conftest import crear_producto, crear_usuario, token_de


APROBADA = "4557889244830258"
RECHAZADA = "4915515029140707"

# Un año por delante, para que las pruebas no caduquen con el tiempo.
ANIO_VIGENTE = datetime.now(timezone.utc).year + 1


async def _pedido(sesion, usuario, producto, unidades=1, decision=None):
    """Un pedido pendiente, con su stock ya apartado y su evaluación."""
    orden = Order(
        user_id=usuario.id,
        total_amount=producto.price * unidades,
        status=OrderStatus.PENDING,
        shipping_address="Jr. Alfonso Ugarte 493",
        shipping_city="Trujillo",
    )
    sesion.add(orden)
    await sesion.flush()
    sesion.add(
        OrderItem(
            order_id=orden.id,
            product_id=producto.id,
            quantity=unidades,
            unit_price=producto.price,
        )
    )
    if decision:
        sesion.add(
            FraudLog(
                order_id=orden.id,
                fraud_score=0.55,
                decision=decision,
                detection_time_ms=2.0,
            )
        )
    producto.stock -= unidades
    await sesion.commit()
    await sesion.refresh(orden)
    return orden


async def _stock(sesion, producto_id):
    return (await sesion.get(Product, producto_id)).stock


async def _pagar(sesion, orden_id, numero=APROBADA, titular="Ana Quispe Ramos", **extra):
    datos = {
        "numero": numero,
        "mes": 12,
        "anio": ANIO_VIGENTE,
        "cvv": "123",
        "titular": titular,
    }
    datos.update(extra)
    return await order_service.confirmar_pago_simulado(sesion, orden_id, **datos)


# ── La simulación no aprueba cualquier cosa ──────────────────────────────────
def test_un_numero_inventado_no_pasa_luhn():
    """
    Si aprobara cualquier número, la simulación no demostraría nada.

    Luhn es el algoritmo que usan las tarjetas de verdad, así que esto es la
    misma comprobación que hace un formulario de pago real antes de molestar al
    banco.
    """
    assert not luhn_valido("1234567890123456")
    assert not luhn_valido("4557889244830259")
    assert luhn_valido(APROBADA)
    assert luhn_valido(RECHAZADA)


def test_la_marca_sale_del_primer_digito():
    assert marca_de(APROBADA) == "visa"
    assert marca_de("5500000000000004") == "master"


def test_una_tarjeta_vencida_no_cobra():
    resultado = cobrar(
        numero=APROBADA, mes=1, anio=2020, cvv="123", titular="Ana Quispe"
    )

    assert not resultado.aprobado
    assert "vencida" in resultado.motivo.lower()


def test_un_numero_mal_escrito_no_es_un_rechazo_del_emisor():
    """
    Son dos «no» distintos y el pedido no corre la misma suerte.

    Una errata es alguien que sigue intentándolo; cancelarle el pedido por eso
    sería absurdo, y además le devolvería el inventario a la tienda mientras la
    persona todavía está escribiendo.
    """
    resultado = cobrar(
        numero="4557889244830259", mes=12, anio=ANIO_VIGENTE, cvv="123", titular="Ana"
    )

    assert not resultado.aprobado
    assert not resultado.es_rechazo_del_emisor


# ── El cobro sale bien ───────────────────────────────────────────────────────
async def test_un_cobro_aprobado_completa_el_pedido(sesion):
    usuario = await crear_usuario(sesion)
    producto = await crear_producto(sesion)
    orden = await _pedido(sesion, usuario, producto)

    aplicado, cobro = await _pagar(sesion, orden.id)

    assert cobro.aprobado
    assert aplicado.estado == "completada"
    await sesion.refresh(orden)
    assert orden.status == OrderStatus.COMPLETED
    assert orden.paid_at is not None


async def test_el_pedido_queda_marcado_como_simulado(sesion):
    """
    Es lo que impide que esto se confunda nunca con un cobro real.

    Ni hoy en el panel, ni dentro de un año mirando la base de datos, ni si
    algún día la tienda vuelve a cobrar de verdad y conviven los dos tipos de
    pedido.
    """
    usuario = await crear_usuario(sesion)
    producto = await crear_producto(sesion)
    orden = await _pedido(sesion, usuario, producto)

    await _pagar(sesion, orden.id)

    await sesion.refresh(orden)
    assert orden.payment_gateway == "simulado"
    assert orden.payment_id.startswith("SIM-")


async def test_de_la_tarjeta_solo_quedan_los_cuatro_ultimos_digitos(sesion):
    """
    Aunque aquí no haya dinero de por medio.

    La costumbre de no guardar el número completo es lo que evita el accidente
    el día que sí lo haya.
    """
    usuario = await crear_usuario(sesion)
    producto = await crear_producto(sesion)
    orden = await _pedido(sesion, usuario, producto)

    await _pagar(sesion, orden.id, titular="Ana Quispe Ramos")

    await sesion.refresh(orden)
    assert orden.card_last_four == "0258"
    assert orden.card_holder == "Ana Quispe Ramos"
    # El número entero no aparece por ninguna parte de la orden.
    assert APROBADA not in str(
        [orden.payment_id, orden.payment_method, orden.card_last_four, orden.card_holder]
    )


# ── Y el modelo sigue mandando ───────────────────────────────────────────────
async def test_un_pedido_marcado_por_el_modelo_queda_retenido_tras_cobrarse(sesion):
    """
    Esta es la prueba que importa para la tesis.

    El sistema retiene la compra sospechosa **después** de cobrar y antes de
    prepararla, para que el revisor tenga delante el titular de la tarjeta. Que
    el cobro sea simulado no cambia esa regla ni una coma: el pedido que el
    modelo mandó a revisar no se completa, se retiene.
    """
    usuario = await crear_usuario(sesion)
    producto = await crear_producto(sesion)
    orden = await _pedido(sesion, usuario, producto, decision="REVIEW")

    aplicado, cobro = await _pagar(sesion, orden.id)

    assert cobro.aprobado
    assert aplicado.estado == "retenida"
    await sesion.refresh(orden)
    assert orden.status == OrderStatus.FRAUD_REVIEW
    # Y el revisor tiene la señal que necesita: quién es el titular.
    assert orden.card_holder == "Ana Quispe Ramos"


async def test_un_pedido_sin_observaciones_se_completa(sesion):
    usuario = await crear_usuario(sesion)
    producto = await crear_producto(sesion)
    orden = await _pedido(sesion, usuario, producto, decision="APPROVED")

    aplicado, _ = await _pagar(sesion, orden.id)

    assert aplicado.estado == "completada"


# ── El cobro sale mal ────────────────────────────────────────────────────────
async def test_una_tarjeta_rechazada_cancela_el_pedido_y_devuelve_el_stock(sesion):
    usuario = await crear_usuario(sesion)
    producto = await crear_producto(sesion, stock=10)
    orden = await _pedido(sesion, usuario, producto, unidades=3)
    assert await _stock(sesion, producto.id) == 7

    aplicado, cobro = await _pagar(sesion, orden.id, numero=RECHAZADA)

    assert not cobro.aprobado
    assert cobro.es_rechazo_del_emisor
    assert aplicado.estado == "cancelada"
    await sesion.refresh(orden)
    assert orden.status == OrderStatus.CANCELLED
    assert await _stock(sesion, producto.id) == 10


async def test_una_errata_deja_el_pedido_intacto_para_reintentar(sesion):
    """
    Quien se equivoca escribiendo tiene que poder volver a intentarlo.

    Si una errata cancelara el pedido, además de la molestia se le devolvería el
    inventario a la tienda mientras la persona sigue delante de la pantalla.
    """
    usuario = await crear_usuario(sesion)
    producto = await crear_producto(sesion, stock=10)
    orden = await _pedido(sesion, usuario, producto, unidades=3)

    aplicado, cobro = await _pagar(sesion, orden.id, numero="4557889244830259")

    assert not cobro.aprobado
    assert aplicado.estado == "sin cambios"
    await sesion.refresh(orden)
    assert orden.status == OrderStatus.PENDING
    assert await _stock(sesion, producto.id) == 7


async def test_un_pedido_ya_pagado_no_se_cobra_dos_veces(sesion):
    usuario = await crear_usuario(sesion)
    producto = await crear_producto(sesion)
    orden = await _pedido(sesion, usuario, producto)
    await _pagar(sesion, orden.id)

    aplicado, _ = await _pagar(sesion, orden.id)

    assert aplicado.estado == "sin cambios"




# ── Por HTTP, que es como lo usa la tienda ───────────────────────────────────
async def test_nadie_paga_el_pedido_de_otro(cliente, sesion):
    dueno = await crear_usuario(sesion, email="dueno@ejemplo.com")
    await crear_usuario(sesion, email="intruso@ejemplo.com")
    producto = await crear_producto(sesion)
    orden = await _pedido(sesion, dueno, producto)
    orden_id = orden.id

    token = await token_de(cliente, "intruso@ejemplo.com")
    respuesta = await cliente.post(
        f"/api/v1/orders/{orden_id}/pago-simulado",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "numero": APROBADA,
            "mes": 12,
            "anio": ANIO_VIGENTE,
            "cvv": "123",
            "titular": "Ana Quispe",
        },
    )

    assert respuesta.status_code == 403


async def test_el_recorrido_completo_por_http(cliente, sesion):
    """
    De la orden pendiente al pedido completado, por donde pasa la tienda.

    Y la orden avisa de que está en modo simulado, que es lo que el checkout
    mira para enseñar su propio formulario en lugar de mandar a nadie fuera.
    """
    usuario = await crear_usuario(sesion)
    producto = await crear_producto(sesion)
    orden = await _pedido(sesion, usuario, producto)
    orden_id = orden.id

    token = await token_de(cliente, usuario.email)
    cabeceras = {"Authorization": f"Bearer {token}"}

    respuesta = await cliente.post(
        f"/api/v1/orders/{orden_id}/pago-simulado",
        headers=cabeceras,
        json={
            "numero": APROBADA,
            "mes": 12,
            "anio": ANIO_VIGENTE,
            "cvv": "123",
            "titular": "Ana Quispe Ramos",
        },
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["aprobado"] is True
    assert cuerpo["estado_del_pedido"] == "completada"

    final = (await cliente.get(f"/api/v1/orders/{orden_id}", headers=cabeceras)).json()
    assert final["status"] == "COMPLETED"
    assert final["payment_gateway"] == "simulado"
    assert final["card_last_four"] == "0258"


# ── Los códigos de respuesta ─────────────────────────────────────────────────
#
# Una pasarela real no contesta «no» a secas: devuelve un código que dice por
# qué, y es el dato que un comercio apunta cuando un cliente llama a preguntar.
# Los que se usan aquí son los de la norma ISO 8583, que es la que hablan las
# redes de tarjetas.


def test_cada_desenlace_trae_su_codigo():
    def codigo(numero, **extra):
        datos = dict(numero=numero, mes=12, anio=ANIO_VIGENTE, cvv="123", titular="Ana Quispe")
        datos.update(extra)
        return cobrar(**datos).codigo

    assert codigo(APROBADA) == "00"
    assert codigo(RECHAZADA) == "51"
    assert codigo("5579898419701047") == "43"
    assert codigo("4557889244830259") == "14"
    assert codigo(APROBADA, mes=1, anio=2020) == "54"


async def test_el_cobro_aprobado_devuelve_su_referencia(cliente, sesion):
    """
    El comprobante tiene que cuadrar con el sistema.

    La referencia que ve el comprador es la misma que queda guardada en el
    pedido y que el administrador ve en el panel. Un comprobante que no coincide
    con lo que hay dentro no sirve para reclamar nada.
    """
    usuario = await crear_usuario(sesion)
    producto = await crear_producto(sesion)
    orden = await _pedido(sesion, usuario, producto)
    orden_id = orden.id

    token = await token_de(cliente, usuario.email)
    cabeceras = {"Authorization": f"Bearer {token}"}

    respuesta = await cliente.post(
        f"/api/v1/orders/{orden_id}/pago-simulado",
        headers=cabeceras,
        json={
            "numero": APROBADA,
            "mes": 12,
            "anio": ANIO_VIGENTE,
            "cvv": "123",
            "titular": "Ana Quispe Ramos",
        },
    )

    cuerpo = respuesta.json()
    assert cuerpo["codigo"] == "00"
    assert cuerpo["referencia"].startswith("SIM-")

    guardada = (await cliente.get(f"/api/v1/orders/{orden_id}", headers=cabeceras)).json()
    assert guardada["payment_id"] == cuerpo["referencia"]

