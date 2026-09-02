"""
Pruebas del etiquetado de pedidos y de las métricas del modelo.

Lo que se vigila aquí es que los números que el panel muestra —y que
terminarán en el documento de la tesis— midan lo que dicen medir. El error que
tenían antes era silencioso: como `is_actual_fraud` valía False tanto para
"revisado y legítimo" como para "nadie lo miró", la precisión del modelo se
calculaba sobre pedidos que nadie había comprobado.
"""

from datetime import datetime, timezone

from app.models.fraud_log import FraudLog
from app.models.order import Order, OrderStatus
from app.models.user import UserRole
from tests.conftest import cabeceras_de, crear_usuario

RUTA_METRICAS = "/api/v1/fraud/metrics"


async def _crear_evaluacion(
    sesion,
    usuario_id: str,
    decision: str,
    monto: float = 1000.0,
    puntaje: float = 0.5,
) -> FraudLog:
    """Deja en la base un pedido con su evaluación, sin revisar todavía."""
    orden = Order(
        user_id=usuario_id,
        total_amount=monto,
        status=OrderStatus.PENDING,
        shipping_address="Av. España 1234",
        shipping_city="Trujillo",
    )
    sesion.add(orden)
    await sesion.flush()

    log = FraudLog(
        order_id=orden.id,
        fraud_score=puntaje,
        decision=decision,
        risk_level="MEDIUM",
        explanation="Evaluación de prueba",
        detection_time_ms=1.5,
        feature_vector={
            "total_amount": monto,
            "high_risk_items_count": 1,
            "checkout_duration_seconds": 60.0,
            "is_new_shipping_address": 1,
        },
    )
    sesion.add(log)
    await sesion.commit()
    await sesion.refresh(log)
    return log


async def test_etiquetar_exige_ser_administrador(cliente, sesion):
    usuario = await crear_usuario(sesion, email="cliente@ejemplo.com")
    log = await _crear_evaluacion(sesion, usuario.id, "BLOCKED")
    cabeceras = await cabeceras_de(cliente, "cliente@ejemplo.com")

    respuesta = await cliente.put(
        f"/api/v1/fraud/logs/{log.id}/label", json={"is_fraud": True}, headers=cabeceras
    )

    assert respuesta.status_code == 403


async def test_marcar_un_fraude_real_deja_constancia_de_la_revision(cliente, sesion):
    cliente_usuario = await crear_usuario(sesion, email="cliente@ejemplo.com")
    await crear_usuario(sesion, email="jefe@ejemplo.com", rol=UserRole.ADMIN)
    log = await _crear_evaluacion(sesion, cliente_usuario.id, "BLOCKED")
    cabeceras = await cabeceras_de(cliente, "jefe@ejemplo.com")

    respuesta = await cliente.put(
        f"/api/v1/fraud/logs/{log.id}/label", json={"is_fraud": True}, headers=cabeceras
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["is_actual_fraud"] is True
    assert cuerpo["reviewed_at"] is not None


async def test_tambien_se_puede_marcar_que_era_legitima(cliente, sesion):
    """
    La mitad que faltaba. Sin poder decir "revisé esto y estaba bien" no hay
    verdaderos negativos, y sin verdaderos negativos no hay precisión.
    """
    cliente_usuario = await crear_usuario(sesion, email="cliente@ejemplo.com")
    await crear_usuario(sesion, email="jefe@ejemplo.com", rol=UserRole.ADMIN)
    log = await _crear_evaluacion(sesion, cliente_usuario.id, "BLOCKED")
    cabeceras = await cabeceras_de(cliente, "jefe@ejemplo.com")

    respuesta = await cliente.put(
        f"/api/v1/fraud/logs/{log.id}/label", json={"is_fraud": False}, headers=cabeceras
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["is_actual_fraud"] is False
    assert cuerpo["reviewed_at"] is not None


async def test_etiquetar_un_registro_inexistente_da_404(cliente, sesion):
    await crear_usuario(sesion, email="jefe@ejemplo.com", rol=UserRole.ADMIN)
    cabeceras = await cabeceras_de(cliente, "jefe@ejemplo.com")

    respuesta = await cliente.put(
        "/api/v1/fraud/logs/no-existe/label", json={"is_fraud": True}, headers=cabeceras
    )

    assert respuesta.status_code == 404


async def test_las_metricas_solo_cuentan_lo_revisado(cliente, sesion):
    """
    Un pedido sin revisar no dice nada del modelo. Antes se colaba entre los
    legítimos e inventaba aciertos que nadie había comprobado.
    """
    usuario = await crear_usuario(sesion, email="cliente@ejemplo.com")
    await crear_usuario(sesion, email="jefe@ejemplo.com", rol=UserRole.ADMIN)

    # Tres evaluaciones, ninguna revisada.
    for decision in ("APPROVED", "REVIEW", "BLOCKED"):
        await _crear_evaluacion(sesion, usuario.id, decision)

    cabeceras = await cabeceras_de(cliente, "jefe@ejemplo.com")
    respuesta = await cliente.get(RUTA_METRICAS, headers=cabeceras)

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["total_evaluations"] == 3
    assert cuerpo["reviewed_count"] == 0
    assert cuerpo["precision"] == 0.0
    assert cuerpo["true_negatives"] == 0


async def test_la_matriz_de_confusion_sale_de_las_etiquetas(cliente, sesion):
    usuario = await crear_usuario(sesion, email="cliente@ejemplo.com")
    await crear_usuario(sesion, email="jefe@ejemplo.com", rol=UserRole.ADMIN)

    # Un acierto: el modelo alertó y era fraude.
    verdadero_positivo = await _crear_evaluacion(sesion, usuario.id, "BLOCKED", monto=2000.0)
    # Una falsa alarma: alertó y la compra era buena.
    falso_positivo = await _crear_evaluacion(sesion, usuario.id, "BLOCKED", monto=1000.0)
    # Un fraude que se le escapó.
    falso_negativo = await _crear_evaluacion(sesion, usuario.id, "APPROVED", monto=3000.0)
    # Y una compra normal que dejó pasar, correctamente.
    verdadero_negativo = await _crear_evaluacion(sesion, usuario.id, "APPROVED", monto=500.0)

    ahora = datetime.now(timezone.utc)
    for log, es_fraude in (
        (verdadero_positivo, True),
        (falso_positivo, False),
        (falso_negativo, True),
        (verdadero_negativo, False),
    ):
        log.is_actual_fraud = es_fraude
        log.reviewed_at = ahora
    await sesion.commit()

    cabeceras = await cabeceras_de(cliente, "jefe@ejemplo.com")
    cuerpo = (await cliente.get(RUTA_METRICAS, headers=cabeceras)).json()

    assert cuerpo["reviewed_count"] == 4
    assert cuerpo["true_positives"] == 1
    assert cuerpo["false_positives"] == 1
    assert cuerpo["false_negatives"] == 1
    assert cuerpo["true_negatives"] == 1

    # Precisión = 1/(1+1) = 50 %; exhaustividad = 1/(1+1) = 50 %.
    assert cuerpo["precision"] == 50.0
    assert cuerpo["recall"] == 50.0
    assert cuerpo["f1_score"] == 50.0


async def test_las_metricas_ponen_los_errores_en_soles(cliente, sesion):
    """
    La cifra que convence en una tesis aplicada: cuánto dinero salvó el modelo
    y cuánto costó equivocarse.
    """
    usuario = await crear_usuario(sesion, email="cliente@ejemplo.com")
    await crear_usuario(sesion, email="jefe@ejemplo.com", rol=UserRole.ADMIN)

    detenido = await _crear_evaluacion(sesion, usuario.id, "BLOCKED", monto=2000.0)
    escapado = await _crear_evaluacion(sesion, usuario.id, "APPROVED", monto=3000.0)
    frenado_por_error = await _crear_evaluacion(sesion, usuario.id, "BLOCKED", monto=1000.0)

    ahora = datetime.now(timezone.utc)
    for log, es_fraude in ((detenido, True), (escapado, True), (frenado_por_error, False)):
        log.is_actual_fraud = es_fraude
        log.reviewed_at = ahora
    await sesion.commit()

    cabeceras = await cabeceras_de(cliente, "jefe@ejemplo.com")
    cuerpo = (await cliente.get(RUTA_METRICAS, headers=cabeceras)).json()

    assert cuerpo["loss_prevented"] == 2000.0
    assert cuerpo["loss_absorbed"] == 3000.0
    # Bloquear una compra buena no cuesta el pedido entero, cuesta el margen.
    assert cuerpo["revenue_lost"] == 150.0


async def test_una_revision_manual_no_cuenta_como_venta_perdida(cliente, sesion):
    """
    Mandar a revisión no es lo mismo que bloquear: si termina bien, el pedido
    sigue su curso y no se pierde ninguna venta.
    """
    usuario = await crear_usuario(sesion, email="cliente@ejemplo.com")
    await crear_usuario(sesion, email="jefe@ejemplo.com", rol=UserRole.ADMIN)

    revisado = await _crear_evaluacion(sesion, usuario.id, "REVIEW", monto=1000.0)
    revisado.is_actual_fraud = False
    revisado.reviewed_at = datetime.now(timezone.utc)
    await sesion.commit()

    cabeceras = await cabeceras_de(cliente, "jefe@ejemplo.com")
    cuerpo = (await cliente.get(RUTA_METRICAS, headers=cabeceras)).json()

    assert cuerpo["false_positives"] == 1
    assert cuerpo["revenue_lost"] == 0.0


async def test_las_metricas_son_solo_para_administradores(cliente, sesion):
    await crear_usuario(sesion, email="cliente@ejemplo.com")
    cabeceras = await cabeceras_de(cliente, "cliente@ejemplo.com")

    respuesta = await cliente.get(RUTA_METRICAS, headers=cabeceras)

    assert respuesta.status_code == 403


async def test_cada_orden_guarda_el_aporte_de_cada_variable(cliente, sesion):
    """
    La trazabilidad de la decisión: no basta con el puntaje, hay que poder
    reconstruir por qué salió ese puntaje.
    """
    from tests.conftest import crear_producto

    producto = await crear_producto(sesion, stock=5)
    await crear_usuario(sesion, email="compra@ejemplo.com")
    cabeceras = await cabeceras_de(cliente, "compra@ejemplo.com")

    respuesta = await cliente.post(
        "/api/v1/orders",
        json={
            "items": [{"product_id": producto.id, "quantity": 1}],
            "shipping_address": "Av. España 1234, Trujillo",
            "shipping_city": "Trujillo",
            "checkout_duration_seconds": 120.0,
        },
        headers=cabeceras,
    )
    assert respuesta.status_code == 201

    await crear_usuario(sesion, email="jefe@ejemplo.com", rol=UserRole.ADMIN)
    cabeceras_admin = await cabeceras_de(cliente, "jefe@ejemplo.com")
    logs = (await cliente.get("/api/v1/fraud/logs", headers=cabeceras_admin)).json()

    assert logs, "la orden tuvo que dejar su evaluación"
    aportes = logs[0]["contributions"]
    assert aportes and set(aportes) == {
        "total_amount",
        "high_risk_items_count",
        "checkout_duration_seconds",
        "is_new_shipping_address",
    }
    # Y la explicación menciona algo concreto del pedido, no una frase fija.
    assert "S/" in logs[0]["explanation"] or "checkout" in logs[0]["explanation"]
