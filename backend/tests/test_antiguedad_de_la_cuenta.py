"""
Pruebas de la quinta variable del modelo: la antigüedad de la cuenta.

Se añadió después de medir el techo de las otras cuatro. Los fraudes que se
escapaban puntuaban todos alrededor de 0.146 —monto normal, prisa normal,
dirección conocida— y ningún umbral separa lo que el modelo no mira. La
antigüedad es la señal más fuerte que la tienda ya tenía sin pedirle nada al
cliente: está en `users.created_at`.

Lo que se comprueba aquí es que llegue de verdad hasta el modelo y que su
ausencia no se lea como fraude, que es el modo de fallar más silencioso: si una
evaluación sin ese dato asumiera cero días, cada compra hecha sin él parecería
venir de una cuenta estrenada esa misma mañana.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.models.user import User
from app.services.fraud_service import (
    ANTIGUEDAD_POR_DEFECTO,
    FEATURES,
    fraud_service,
)
from app.services.order_service import _antiguedad_de_la_cuenta


def _usuario(alta) -> User:
    return User(
        email="quien.sea@gmail.com",
        hashed_password="x",
        full_name="Quien Sea",
        created_at=alta,
    )


# ── El cálculo ───────────────────────────────────────────────────────────────


def test_una_cuenta_de_hoy_no_tiene_antiguedad():
    dias = _antiguedad_de_la_cuenta(_usuario(datetime.now(timezone.utc)))

    assert 0 <= dias < 0.01


def test_una_cuenta_vieja_cuenta_sus_dias():
    alta = datetime.now(timezone.utc) - timedelta(days=200)

    assert 199.9 < _antiguedad_de_la_cuenta(_usuario(alta)) < 200.1


def test_una_fecha_ingenua_se_lee_como_utc():
    """
    SQLite devuelve fechas sin zona. Sin esta conversión, restarlas contra un
    instante con zona revienta y la compra entera se cae.
    """
    alta = (datetime.now(timezone.utc) - timedelta(days=30)).replace(tzinfo=None)

    assert 29.9 < _antiguedad_de_la_cuenta(_usuario(alta)) < 30.1


def test_una_fecha_en_el_futuro_no_da_dias_negativos():
    """
    Solo puede venir de un reloj mal puesto o de datos importados a mano, pero
    un negativo aquí empujaría el puntaje hacia un lado que nadie eligió.
    """
    alta = datetime.now(timezone.utc) + timedelta(days=5)

    assert _antiguedad_de_la_cuenta(_usuario(alta)) == 0.0


def test_sin_fecha_de_alta_se_supone_un_cliente_normal():
    """
    Y no cero. Cero significa «cuenta abierta hoy», que es justo la señal de
    fraude: un dato que falta no puede convertirse en una acusación.
    """
    assert _antiguedad_de_la_cuenta(_usuario(None)) == ANTIGUEDAD_POR_DEFECTO
    assert ANTIGUEDAD_POR_DEFECTO > 30


# ── Que el modelo la mire ────────────────────────────────────────────────────


def test_el_modelo_declara_las_cinco_variables():
    assert "account_age_days" in FEATURES
    assert len(FEATURES) == 5


def test_la_cuenta_recien_abierta_puntua_mas_alto_que_la_antigua():
    """
    La misma compra, palabra por palabra, cambiando solo la antigüedad. Si el
    puntaje no se moviera, la variable estaría llegando pero sin usarse.
    """
    fraud_service.load_model()
    if not fraud_service.is_loaded():
        pytest.skip("no hay modelo publicado con el que evaluar")

    compra = dict(
        total_amount=2800.0,
        high_risk_items_count=2,
        checkout_duration_seconds=40.0,
        is_new_shipping_address=1,
    )
    nueva = fraud_service.evaluar(**compra, account_age_days=1.0)
    antigua = fraud_service.evaluar(**compra, account_age_days=300.0)

    assert nueva.puntaje > antigua.puntaje


def test_la_antiguedad_aparece_entre_los_aportes():
    """
    Los aportes son los que sostienen la explicación que ve el administrador.
    Una variable que no aparece ahí no se puede auditar.
    """
    fraud_service.load_model()
    if not fraud_service.is_loaded():
        pytest.skip("no hay modelo publicado con el que evaluar")

    evaluacion = fraud_service.evaluar(
        total_amount=3500.0,
        high_risk_items_count=3,
        checkout_duration_seconds=25.0,
        is_new_shipping_address=1,
        account_age_days=2.0,
    )

    assert "account_age_days" in evaluacion.aportes
    assert set(evaluacion.aportes) == set(FEATURES)


def test_la_explicacion_sabe_nombrar_la_antiguedad():
    """
    La frase la lee una persona: «account_age_days: 2» no es una explicación.
    """
    from app.services.fraud_service import _frase

    assert _frase("account_age_days", 0.0) == "cuenta abierta hoy"
    assert _frase("account_age_days", 1.0) == "cuenta de ayer"
    assert _frase("account_age_days", 12.0) == "cuenta de 12 días"
    assert _frase("account_age_days", 200.0) == "cuenta de 6 meses"
