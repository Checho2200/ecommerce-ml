"""
Pruebas del servicio de deteccion de fraude con LightGBM.

Comprueban el contrato que consume la creacion de ordenes: que el modelo
entrenado se carga y que cada evaluacion devuelve valores utilizables.
"""

import pytest

from app.services.fraud_service import fraud_service

DECISIONES_VALIDAS = {"APPROVED", "REVIEW", "BLOCKED"}
NIVELES_VALIDOS = {"LOW", "MEDIUM", "HIGH"}


@pytest.fixture(scope="module", autouse=True)
def cargar_modelo():
    fraud_service.load_model()


def test_el_modelo_entrenado_se_carga():
    assert fraud_service.is_loaded(), "No se encontro fraud_model.joblib"


def test_una_compra_corriente_devuelve_valores_coherentes():
    score, decision, nivel, explicacion, ms = fraud_service.evaluate_transaction(
        total_amount=150.0,
        high_risk_items_count=0,
        checkout_duration_seconds=180.0,
        is_new_shipping_address=0,
    )

    assert 0.0 <= score <= 1.0
    assert decision in DECISIONES_VALIDAS
    assert nivel in NIVELES_VALIDOS
    assert explicacion
    assert ms >= 0.0


def test_una_compra_sospechosa_no_puntua_menos_que_una_corriente():
    corriente, *_ = fraud_service.evaluate_transaction(
        total_amount=120.0,
        high_risk_items_count=0,
        checkout_duration_seconds=240.0,
        is_new_shipping_address=0,
    )
    sospechosa, *_ = fraud_service.evaluate_transaction(
        total_amount=8000.0,
        high_risk_items_count=4,
        checkout_duration_seconds=12.0,
        is_new_shipping_address=1,
    )

    assert sospechosa >= corriente
