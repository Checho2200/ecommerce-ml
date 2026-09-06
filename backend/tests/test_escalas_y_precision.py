"""
Pruebas de las escalas del historial y de la precisión por período.

Dos cosas que el panel promete y que conviene tener sujetas:

- Que un bimestre, un trimestre y un semestre estén anclados al calendario y no
  a "hace dos meses desde hoy". Si no lo estuvieran, el mismo informe pedido en
  dos días distintos devolvería bloques distintos y dejaría de ser comparable,
  que es justo para lo que se exporta.
- Que la precisión cuente las alertas que resultaron ser compras buenas. Sin
  ellas el modelo parecería infalible: solo se estarían mirando sus aciertos.
"""

from datetime import date, datetime, timedelta, timezone

import pytest

from app.models.fraud_log import FraudLog
from app.models.order import Order, OrderStatus
from app.services import fraud_metrics_service
from app.services.fraud_metrics_service import (
    ZONA_DE_LA_TIENDA,
    _inicio_del_periodo,
    _periodo_anterior,
)

from tests.conftest import crear_usuario


async def _evaluacion(
    sesion,
    usuario,
    decision: str,
    cuando: datetime,
    *,
    revisado: bool = False,
    fue_fraude: bool | None = None,
    monto: float = 100.0,
):
    """Un pedido evaluado, opcionalmente ya revisado y etiquetado."""
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
            reviewed_at=cuando if revisado else None,
            is_actual_fraud=fue_fraude,
        )
    )
    await sesion.commit()
    return orden


# ── Las escalas nuevas ───────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "granularidad, dia, esperado",
    [
        # Los bimestres del año son ene-feb, mar-abr, may-jun...
        ("bimester", date(2026, 1, 15), date(2026, 1, 1)),
        ("bimester", date(2026, 2, 28), date(2026, 1, 1)),
        ("bimester", date(2026, 3, 1), date(2026, 3, 1)),
        ("bimester", date(2026, 12, 31), date(2026, 11, 1)),
        # Los trimestres, ene-mar, abr-jun, jul-sep, oct-dic.
        ("quarter", date(2026, 3, 31), date(2026, 1, 1)),
        ("quarter", date(2026, 4, 1), date(2026, 4, 1)),
        ("quarter", date(2026, 11, 20), date(2026, 10, 1)),
        # Los semestres, ene-jun y jul-dic.
        ("semester", date(2026, 6, 30), date(2026, 1, 1)),
        ("semester", date(2026, 7, 1), date(2026, 7, 1)),
        # Y las de siempre, que no deben haber cambiado.
        ("month", date(2026, 5, 17), date(2026, 5, 1)),
        ("year", date(2026, 5, 17), date(2026, 1, 1)),
    ],
)
def test_cada_escala_ancla_el_periodo_al_calendario(granularidad, dia, esperado):
    momento = datetime.combine(dia, datetime.min.time(), tzinfo=ZONA_DE_LA_TIENDA)
    assert _inicio_del_periodo(momento, granularidad) == esperado


@pytest.mark.parametrize(
    "granularidad, inicio, esperado",
    [
        ("bimester", date(2026, 3, 1), date(2026, 1, 1)),
        ("bimester", date(2026, 1, 1), date(2025, 11, 1)),
        ("quarter", date(2026, 1, 1), date(2025, 10, 1)),
        ("semester", date(2026, 1, 1), date(2025, 7, 1)),
        ("month", date(2026, 1, 1), date(2025, 12, 1)),
        ("year", date(2026, 1, 1), date(2025, 1, 1)),
    ],
)
def test_retroceder_un_periodo_cruza_bien_el_cambio_de_ano(granularidad, inicio, esperado):
    assert _periodo_anterior(inicio, granularidad) == esperado


async def test_el_historial_bimestral_devuelve_la_ventana_pedida(sesion):
    usuario = await crear_usuario(sesion)
    await _evaluacion(sesion, usuario, "APPROVED", datetime.now(ZONA_DE_LA_TIENDA))

    serie = await fraud_metrics_service.historial(sesion, "bimester", periodos=6)

    assert len(serie) == 6
    # Sin huecos y en orden: cada período empieza dos meses después del anterior.
    for anterior, siguiente in zip(serie, serie[1:]):
        assert _periodo_anterior(siguiente.inicio, "bimester") == anterior.inicio
    # Y todos arrancan en un mes impar, que es donde empieza un bimestre.
    assert all(p.inicio.month % 2 == 1 for p in serie)
    assert sum(p.evaluaciones for p in serie) == 1


async def test_una_escala_desconocida_cae_en_dias(sesion):
    await crear_usuario(sesion)

    serie = await fraud_metrics_service.historial(sesion, "quincena", periodos=3)

    assert len(serie) == 3
    assert _periodo_anterior(serie[-1].inicio, "day") == serie[-2].inicio


# ── La precisión ─────────────────────────────────────────────────────────────


async def test_la_precision_cuenta_las_alertas_que_eran_compras_buenas(sesion):
    usuario = await crear_usuario(sesion)
    hoy = datetime.now(ZONA_DE_LA_TIENDA)

    # Tres alertas revisadas: dos eran fraude, una era una compra legítima.
    await _evaluacion(sesion, usuario, "BLOCKED", hoy, revisado=True, fue_fraude=True)
    await _evaluacion(sesion, usuario, "REVIEW", hoy, revisado=True, fue_fraude=True)
    await _evaluacion(sesion, usuario, "BLOCKED", hoy, revisado=True, fue_fraude=False)
    # Y una compra aprobada y revisada, que no es alerta: no toca la precisión.
    await _evaluacion(sesion, usuario, "APPROVED", hoy, revisado=True, fue_fraude=False)

    serie = await fraud_metrics_service.historial(sesion, "day", periodos=1)
    periodo = serie[-1]

    assert periodo.fraudes_detectados == 2
    assert periodo.falsas_alertas == 1
    assert periodo.precision == pytest.approx(2 / 3, abs=1e-4)
    # La detección se mide contra los fraudes, no contra las alertas.
    assert periodo.tasa_de_deteccion == pytest.approx(1.0)


async def test_sin_alertas_revisadas_la_precision_es_desconocida_y_no_cero(sesion):
    usuario = await crear_usuario(sesion)
    hoy = datetime.now(ZONA_DE_LA_TIENDA)

    # Solo compras aprobadas: el modelo no frenó nada que se pueda comprobar.
    await _evaluacion(sesion, usuario, "APPROVED", hoy, revisado=True, fue_fraude=False)

    periodo = (await fraud_metrics_service.historial(sesion, "day", periodos=1))[-1]

    assert periodo.precision is None, "un cero diría que todo lo frenado estaba mal"
    assert periodo.falsas_alertas == 0


async def test_una_alerta_sin_revisar_no_cuenta_para_la_precision(sesion):
    usuario = await crear_usuario(sesion)
    hoy = datetime.now(ZONA_DE_LA_TIENDA)

    # Bloqueada pero nadie la miró: no se sabe si estuvo bien o mal.
    await _evaluacion(sesion, usuario, "BLOCKED", hoy)

    periodo = (await fraud_metrics_service.historial(sesion, "day", periodos=1))[-1]

    assert periodo.precision is None
    assert periodo.falsas_alertas == 0
    assert periodo.bloqueadas == 1
