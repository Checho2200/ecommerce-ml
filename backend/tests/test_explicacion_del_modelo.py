"""
Pruebas de que la decisión del modelo se puede rehacer a mano.

El panel enseña la aritmética completa de un pedido: punto de partida, el
aporte de cada variable, la suma y la función logística. Eso solo vale si los
números cuadran, y cuadran por una propiedad concreta —los valores SHAP suman
exactamente el logit de la predicción— que es fácil de romper sin darse cuenta:
basta con guardar los aportes de otra forma, normalizarlos o dejar fuera el
valor base.

Si estas pruebas fallan, el panel está enseñando una cuenta que no cierra, que
es peor que no enseñar ninguna.
"""

from math import exp

import pandas as pd
import pytest

from app.models.user import UserRole
from app.services.fraud_service import fraud_service
from ml.dataset import FEATURES

from tests.conftest import cabeceras_de, crear_usuario


@pytest.fixture(scope="module", autouse=True)
def modelo_cargado():
    if not fraud_service.is_loaded():
        fraud_service.load_model()
    if not fraud_service.is_loaded():
        pytest.skip("no hay modelo publicado con el que comprobar la cuenta")


PEDIDOS = [
    {"total_amount": 8395.0, "high_risk_items_count": 5, "checkout_duration_seconds": 37.0, "is_new_shipping_address": 1},
    {"total_amount": 149.0, "high_risk_items_count": 0, "checkout_duration_seconds": 544.0, "is_new_shipping_address": 0},
    {"total_amount": 3498.0, "high_risk_items_count": 2, "checkout_duration_seconds": 570.9, "is_new_shipping_address": 0},
]


@pytest.mark.parametrize("pedido", PEDIDOS)
def test_el_puntaje_es_la_sigmoide_de_la_base_mas_los_aportes(pedido):
    """
    La igualdad que sostiene toda la explicación del panel:

        puntaje = 1 / (1 + e^-(base + suma de los aportes))
    """
    evaluacion = fraud_service.evaluar(
        total_amount=pedido["total_amount"],
        high_risk_items_count=pedido["high_risk_items_count"],
        checkout_duration_seconds=pedido["checkout_duration_seconds"],
        is_new_shipping_address=pedido["is_new_shipping_address"],
    )

    assert evaluacion.aportes is not None, "sin aportes no hay explicación que enseñar"

    base = fraud_service.valor_base()
    assert base is not None

    suma = base + sum(evaluacion.aportes.values())
    recalculado = 1 / (1 + exp(-suma))

    # La tolerancia es la del redondeo a cuatro decimales con el que se guardan
    # los aportes, no un margen de error del método.
    assert recalculado == pytest.approx(evaluacion.puntaje, abs=1e-3)


def test_hay_un_aporte_por_cada_variable_y_ninguno_de_mas():
    evaluacion = fraud_service.evaluar(
        total_amount=1000.0,
        high_risk_items_count=1,
        checkout_duration_seconds=200.0,
        is_new_shipping_address=0,
    )
    assert set(evaluacion.aportes or {}) == set(FEATURES)


def test_el_valor_base_no_depende_del_pedido():
    """
    Es una constante del modelo. Si cambiara con la entrada, el panel estaría
    llamando "punto de partida" a algo que no lo es.
    """
    primero = fraud_service.valor_base()

    fila = pd.DataFrame([{v: 9999.0 for v in FEATURES}])[FEATURES]
    contribuciones = fraud_service.model.booster_.predict(fila, pred_contrib=True)

    assert round(float(contribuciones[0][-1]), 4) == primero


@pytest.mark.asyncio
async def test_el_endpoint_del_modelo_publica_lo_que_hace_falta_para_la_cuenta(cliente, sesion):
    """El panel no puede rehacer la aritmética sin la base y las variables."""
    await crear_usuario(sesion, email="admin@ejemplo.com", rol=UserRole.ADMIN)
    cabeceras = await cabeceras_de(cliente, "admin@ejemplo.com")
    datos = (await cliente.get("/api/v1/fraud/model", headers=cabeceras)).json()

    assert datos["loaded"] is True
    assert datos["base_value"] is not None
    assert datos["n_trees"] and datos["n_trees"] > 1
    assert 0 < datos["approve_below"] < datos["block_above"] <= 1


@pytest.mark.asyncio
async def test_el_detalle_del_modelo_es_solo_para_administradores(cliente, sesion):
    await crear_usuario(sesion, email="cliente@ejemplo.com")
    cabeceras = await cabeceras_de(cliente, "cliente@ejemplo.com")

    respuesta = await cliente.get("/api/v1/fraud/model", headers=cabeceras)
    assert respuesta.status_code == 403
