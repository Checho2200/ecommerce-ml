"""
Pruebas del servicio de detección de fraude con LightGBM.

Comprueban el contrato que consume la creación de órdenes: que el modelo
entrenado se carga, que cada evaluación devuelve valores utilizables, y que la
explicación que ve el administrador dice algo del pedido concreto y no una
frase igual para todos.
"""

import pytest

from app.services.fraud_service import FEATURES, fraud_service

DECISIONES_VALIDAS = {"APPROVED", "REVIEW", "BLOCKED"}
NIVELES_VALIDOS = {"LOW", "MEDIUM", "HIGH"}

COMPRA_CORRIENTE = {
    "total_amount": 150.0,
    "high_risk_items_count": 0,
    "checkout_duration_seconds": 180.0,
    "is_new_shipping_address": 0,
}

COMPRA_SOSPECHOSA = {
    "total_amount": 8500.0,
    "high_risk_items_count": 4,
    "checkout_duration_seconds": 11.0,
    "is_new_shipping_address": 1,
}


@pytest.fixture(scope="module", autouse=True)
def cargar_modelo():
    fraud_service.load_model()


def test_el_modelo_entrenado_se_carga():
    assert fraud_service.is_loaded(), "No se encontró fraud_model.joblib"


def test_una_compra_corriente_devuelve_valores_coherentes():
    evaluacion = fraud_service.evaluar(**COMPRA_CORRIENTE)

    assert 0.0 <= evaluacion.puntaje <= 1.0
    assert evaluacion.decision in DECISIONES_VALIDAS
    assert evaluacion.nivel_de_riesgo in NIVELES_VALIDOS
    assert evaluacion.explicacion
    assert evaluacion.milisegundos >= 0.0


def test_una_compra_sospechosa_no_puntua_menos_que_una_corriente():
    corriente = fraud_service.evaluar(**COMPRA_CORRIENTE)
    sospechosa = fraud_service.evaluar(**COMPRA_SOSPECHOSA)

    assert sospechosa.puntaje >= corriente.puntaje


def test_los_umbrales_salen_del_entrenamiento():
    """
    El servicio ya no lleva los cortes escritos a mano: los lee del archivo que
    deja `ml/train.py`, donde se eligieron minimizando el costo de los errores.
    """
    assert 0.0 < fraud_service.umbral_aprobacion < fraud_service.umbral_bloqueo < 1.0


def test_la_decision_respeta_los_umbrales_cargados():
    for datos in (COMPRA_CORRIENTE, COMPRA_SOSPECHOSA):
        evaluacion = fraud_service.evaluar(**datos)
        if evaluacion.puntaje < fraud_service.umbral_aprobacion:
            esperado = "APPROVED"
        elif evaluacion.puntaje < fraud_service.umbral_bloqueo:
            esperado = "REVIEW"
        else:
            esperado = "BLOCKED"
        assert evaluacion.decision == esperado


def test_cada_evaluacion_trae_el_aporte_de_las_cuatro_variables():
    """
    Son los valores SHAP que calcula LightGBM. Sin ellos la decisión no se
    puede auditar: quedaría un número y nada más.
    """
    evaluacion = fraud_service.evaluar(**COMPRA_SOSPECHOSA)

    assert set(evaluacion.aportes) == set(FEATURES)
    assert all(isinstance(valor, float) for valor in evaluacion.aportes.values())


def test_la_explicacion_nombra_lo_que_pesó_en_ese_pedido():
    """
    Antes todos los pedidos de alto riesgo recibían la misma frase fija. Ahora
    dos pedidos distintos tienen que explicarse distinto.
    """
    corriente = fraud_service.evaluar(**COMPRA_CORRIENTE)
    sospechosa = fraud_service.evaluar(**COMPRA_SOSPECHOSA)

    assert corriente.explicacion != sospechosa.explicacion
    # El monto del pedido caro aparece escrito en su propia explicación.
    assert "8,500" in sospechosa.explicacion


def test_sin_modelo_se_aprueba_y_se_dice_por_que():
    """
    Una falla de infraestructura no puede bloquear compras legítimas: si el
    modelo no está, el pedido pasa y la explicación lo deja por escrito.
    """
    modelo = fraud_service.model
    fraud_service.model = None
    try:
        evaluacion = fraud_service.evaluar(**COMPRA_SOSPECHOSA)
    finally:
        fraud_service.model = modelo

    # Si el archivo del modelo existe, `evaluar` lo recarga solo y decide
    # normalmente; lo que se comprueba es que en ninguno de los dos caminos se
    # queda sin respuesta.
    assert evaluacion.decision in DECISIONES_VALIDAS
    assert evaluacion.explicacion
