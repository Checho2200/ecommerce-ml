"""
Pruebas de la ficha del modelo que ve el administrador.

El punto de estas pruebas es la honestidad de la pantalla, no su aspecto. El
modelo que sirve hoy aprendió de un conjunto sintético del dominio, porque una
tienda recién abierta no tiene contracargos con los que aprender. Un panel que
solo dijera "modelo cargado" dejaría entender que aprendió de las ventas de la
tienda, y en una sustentación esa es exactamente la pregunta que se hace.

Por eso la ficha lleva el recuento de pedidos etiquetados y el umbral que pide
el entrenamiento para cambiar de fuente, y ese umbral se lee de `ml/dataset.py`
en vez de repetirse: si se copiara, la pantalla podría prometer una condición y
el entrenamiento aplicar otra.
"""

from datetime import datetime, timezone

from ml.dataset import MINIMO_POR_CLASE, MINIMO_TOTAL

from app.models.fraud_log import FraudLog
from app.models.order import Order, OrderStatus
from app.models.user import UserRole
from app.services import fraud_metrics_service
from tests.conftest import cabeceras_de, crear_usuario


async def _pedido_etiquetado(sesion, usuario, es_fraude: bool, revisado: bool = True):
    orden = Order(
        user_id=usuario.id,
        total_amount=250.0,
        status=OrderStatus.PENDING,
        shipping_address="Jr. Alfonso Ugarte 493",
        shipping_city="Trujillo",
    )
    sesion.add(orden)
    await sesion.flush()

    ahora = datetime.now(timezone.utc)
    sesion.add(
        FraudLog(
            order_id=orden.id,
            fraud_score=0.5,
            decision="REVIEW",
            evaluated_at=ahora,
            detection_time_ms=2.0,
            reviewed_at=ahora if revisado else None,
            is_actual_fraud=es_fraude if revisado else None,
        )
    )
    await sesion.commit()


async def test_la_ficha_dice_cuantas_etiquetas_faltan(cliente, sesion):
    usuario = await crear_usuario(sesion, email="admin@ejemplo.com", rol=UserRole.ADMIN)
    await _pedido_etiquetado(sesion, usuario, es_fraude=True)
    await _pedido_etiquetado(sesion, usuario, es_fraude=False)
    await _pedido_etiquetado(sesion, usuario, es_fraude=False)

    cabeceras = await cabeceras_de(cliente, "admin@ejemplo.com")
    respuesta = await cliente.get("/api/v1/fraud/model", headers=cabeceras)

    assert respuesta.status_code == 200, respuesta.text
    ficha = respuesta.json()

    assert ficha["labeled_orders"] == 3
    assert ficha["labeled_frauds"] == 1
    assert ficha["labeled_legit"] == 2
    # El umbral que enseña la pantalla es el mismo que aplica el entrenamiento.
    assert ficha["required_total"] == MINIMO_TOTAL
    assert ficha["required_per_class"] == MINIMO_POR_CLASE
    # Con tres pedidos no se reentrena con datos de la tienda, y se dice.
    assert ficha["can_train_with_real_data"] is False


async def test_un_pedido_sin_revisar_no_cuenta_como_etiquetado(cliente, sesion):
    usuario = await crear_usuario(sesion, email="admin@ejemplo.com", rol=UserRole.ADMIN)
    await _pedido_etiquetado(sesion, usuario, es_fraude=True, revisado=False)

    cabeceras = await cabeceras_de(cliente, "admin@ejemplo.com")
    ficha = (await cliente.get("/api/v1/fraud/model", headers=cabeceras)).json()

    assert ficha["labeled_orders"] == 0


async def test_el_progreso_se_considera_suficiente_solo_con_las_dos_clases(sesion):
    usuario = await crear_usuario(sesion)

    # Muchos legítimos y ni un fraude: no alcanza, por mucho que sume el total.
    for _ in range(MINIMO_TOTAL):
        await _pedido_etiquetado(sesion, usuario, es_fraude=False)

    progreso = await fraud_metrics_service.progreso_hacia_datos_reales(sesion)

    assert progreso.etiquetados == MINIMO_TOTAL
    assert progreso.legitimos == MINIMO_TOTAL
    assert progreso.fraudes == 0
    assert progreso.suficientes is False, (
        "sin ejemplos de fraude el modelo no puede aprender a distinguirlo"
    )


async def test_la_ficha_es_solo_para_administradores(cliente, sesion):
    await crear_usuario(sesion, email="cliente@ejemplo.com")
    cabeceras = await cabeceras_de(cliente, "cliente@ejemplo.com")

    respuesta = await cliente.get("/api/v1/fraud/model", headers=cabeceras)

    assert respuesta.status_code == 403
