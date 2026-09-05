"""
Pruebas del historial de indicadores y del resumen del panel.

Lo que se comprueba aquí no es que las cifras "salgan"; es que signifiquen lo
que el panel dice que significan: que un pedido caiga en el día correcto según
el reloj de Trujillo y no el de Greenwich, que un período sin ventas aparezca
en cero en lugar de desaparecer del historial, y que "pasaron" cuente solo lo
que el modelo dejó seguir hasta el cobro.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.models.fraud_log import FraudLog
from app.models.order import Order, OrderStatus
from app.models.user import UserRole
from app.services import fraud_metrics_service
from app.services.fraud_metrics_service import ZONA_DE_LA_TIENDA

from tests.conftest import cabeceras_de, crear_usuario


async def _evaluacion(sesion, usuario, decision: str, monto: float, cuando: datetime):
    """Un pedido con su evaluación, fechado a mano."""
    estado = {
        "BLOCKED": OrderStatus.REJECTED,
        "REVIEW": OrderStatus.FRAUD_REVIEW,
    }.get(decision, OrderStatus.PENDING)

    orden = Order(
        user_id=usuario.id,
        total_amount=monto,
        status=estado,
        shipping_address="Jr. Alfonso Ugarte 493",
        shipping_city="Trujillo",
        created_at=cuando,
    )
    sesion.add(orden)
    await sesion.flush()

    sesion.add(
        FraudLog(
            order_id=orden.id,
            fraud_score=0.5,
            decision=decision,
            evaluated_at=cuando,
            detection_time_ms=3.0,
        )
    )
    await sesion.commit()
    return orden


@pytest.mark.asyncio
async def test_el_historial_separa_lo_que_paso_de_lo_que_se_retuvo(sesion):
    usuario = await crear_usuario(sesion)
    hoy = datetime.now(ZONA_DE_LA_TIENDA)

    await _evaluacion(sesion, usuario, "APPROVED", 100.0, hoy)
    await _evaluacion(sesion, usuario, "APPROVED", 200.0, hoy)
    await _evaluacion(sesion, usuario, "REVIEW", 300.0, hoy)
    await _evaluacion(sesion, usuario, "BLOCKED", 400.0, hoy)

    serie = await fraud_metrics_service.historial(sesion, "day", periodos=1)

    assert len(serie) == 1
    periodo = serie[0]
    assert periodo.evaluaciones == 4
    # "Pasaron" es solo lo aprobado: es lo único que llegó a la pasarela.
    assert periodo.aprobadas == 2
    assert periodo.en_revision == 1
    assert periodo.bloqueadas == 1
    assert periodo.monto_aprobado == 300.0
    # Lo retenido suma revisión y bloqueo: ninguno de los dos se cobró.
    assert periodo.monto_retenido == 700.0


@pytest.mark.asyncio
async def test_los_periodos_sin_ventas_salen_en_cero_y_no_se_saltan(sesion):
    usuario = await crear_usuario(sesion)
    hoy = datetime.now(ZONA_DE_LA_TIENDA)

    await _evaluacion(sesion, usuario, "APPROVED", 100.0, hoy)
    await _evaluacion(sesion, usuario, "APPROVED", 100.0, hoy - timedelta(days=4))

    serie = await fraud_metrics_service.historial(sesion, "day", periodos=5)

    # Cinco días seguidos, sin huecos, aunque tres estén vacíos.
    assert len(serie) == 5
    assert [p.evaluaciones for p in serie] == [1, 0, 0, 0, 1]
    dias = [p.inicio for p in serie]
    assert dias == sorted(dias), "el historial va del más antiguo al más reciente"


@pytest.mark.asyncio
async def test_una_compra_de_la_noche_cuenta_en_el_dia_de_trujillo(sesion):
    """
    Las 20:00 de Trujillo son las 01:00 UTC del día siguiente.

    Agrupando por UTC, la venta de una noche aparecería en el informe del día
    siguiente y el corte diario del panel empezaría a las siete de la tarde.
    """
    usuario = await crear_usuario(sesion)

    anoche = datetime.now(ZONA_DE_LA_TIENDA).replace(
        hour=20, minute=30, second=0, microsecond=0
    ) - timedelta(days=1)
    assert anoche.astimezone(timezone.utc).date() != anoche.date(), (
        "la prueba solo tiene sentido con una hora que cruza la medianoche UTC"
    )

    await _evaluacion(sesion, usuario, "APPROVED", 100.0, anoche)

    serie = await fraud_metrics_service.historial(sesion, "day", periodos=2)
    por_dia = {p.inicio: p.evaluaciones for p in serie}

    assert por_dia[anoche.date()] == 1
    assert por_dia[anoche.date() + timedelta(days=1)] == 0


@pytest.mark.asyncio
async def test_la_semana_empieza_en_lunes_y_el_mes_en_el_dia_uno(sesion):
    usuario = await crear_usuario(sesion)
    hoy = datetime.now(ZONA_DE_LA_TIENDA)
    await _evaluacion(sesion, usuario, "APPROVED", 100.0, hoy)

    semanas = await fraud_metrics_service.historial(sesion, "week", periodos=3)
    assert all(p.inicio.weekday() == 0 for p in semanas)

    meses = await fraud_metrics_service.historial(sesion, "month", periodos=3)
    assert all(p.inicio.day == 1 for p in meses)
    # Tres meses seguidos, sin saltarse los de 28 o 31 días.
    assert len({(p.inicio.year, p.inicio.month) for p in meses}) == 3


@pytest.mark.asyncio
async def test_el_historial_es_solo_para_administradores(cliente, sesion):
    await crear_usuario(sesion, email="cliente@ejemplo.com")
    cabeceras = await cabeceras_de(cliente, "cliente@ejemplo.com")

    respuesta = await cliente.get("/api/v1/fraud/history", headers=cabeceras)
    assert respuesta.status_code == 403


@pytest.mark.asyncio
async def test_el_resumen_de_ordenes_solo_factura_lo_cobrado(cliente, sesion):
    admin = await crear_usuario(sesion, email="admin@ejemplo.com", rol=UserRole.ADMIN)
    hoy = datetime.now(ZONA_DE_LA_TIENDA)

    await _evaluacion(sesion, admin, "APPROVED", 500.0, hoy)   # queda PENDING
    await _evaluacion(sesion, admin, "REVIEW", 300.0, hoy)
    await _evaluacion(sesion, admin, "BLOCKED", 900.0, hoy)

    cabeceras = await cabeceras_de(cliente, "admin@ejemplo.com")
    datos = (await cliente.get("/api/v1/orders/summary", headers=cabeceras)).json()

    assert datos["total"] == 3
    assert datos["by_status"]["PENDING"] == 1
    assert datos["awaiting_review"] == 1
    # Ni pendiente ni rechazada son venta: lo cobrado todavía es cero.
    assert datos["revenue"] == 0.0
