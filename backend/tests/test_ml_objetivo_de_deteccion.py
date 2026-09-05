"""
Pruebas de que el modelo persigue los indicadores y no solo el dinero.

El optimizador de umbrales razona en soles, y en soles hay respuestas que salen
baratas y son inaceptables: dejar escapar los fraudes pequeños cuesta menos que
las revisiones que haría falta pagar para atraparlos. La cuenta sale bien y la
tasa de fraudes detectados —el indicador que reporta la tesis— se hunde sin que
nada avise.

Lo que se comprueba aquí es que las dos defensas contra eso funcionan: el piso
de detección al elegir los umbrales, y la regla que impide publicar un modelo
reentrenado que detecte menos que el que ya está sirviendo.
"""

import numpy as np
import pytest

from ml import evaluacion
from ml.train import CAIDA_TOLERADA_DE_DETECCION, decidir_reemplazo


@pytest.fixture
def escenario():
    """
    Cien compras: noventa legítimas y diez fraudes.

    Los fraudes puntúan alto pero no todos: tres se quedan en la zona media,
    que es justo donde la elección de umbrales decide si se detectan o no.
    """
    generador = np.random.default_rng(7)
    y = np.array([0] * 90 + [1] * 10)
    prob = np.concatenate(
        [
            generador.uniform(0.0, 0.30, 90),   # legítimas, puntaje bajo
            generador.uniform(0.85, 0.99, 7),   # fraudes evidentes
            np.array([0.42, 0.46, 0.51]),       # fraudes en la zona dudosa
        ]
    )
    montos = np.concatenate([generador.uniform(80, 400, 90), generador.uniform(80, 300, 10)])
    return y, prob, montos


def test_el_costo_informa_la_tasa_de_deteccion(escenario):
    y, prob, montos = escenario
    # Un umbral de aprobación en 0.35 deja pasar todo lo que puntúe menos: los
    # tres fraudes de la zona dudosa quedan por encima, así que se detectan.
    fila = evaluacion.costo_de_los_umbrales(y, prob, montos, 0.35, 0.80, evaluacion.Costos())

    assert fila["fraudes_detectados"] + fila["fraudes_aprobados"] == 10
    assert fila["tasa_de_deteccion"] + fila["tasa_de_no_deteccion"] == pytest.approx(1.0)
    assert fila["tasa_de_deteccion"] == 1.0


def test_el_piso_de_deteccion_cambia_los_umbrales_elegidos(escenario):
    """
    Con el piso alto, la búsqueda tiene que renunciar al par más barato.

    Es el efecto que la tesis necesita poder mostrar: subir el indicador cuesta
    dinero, y el sistema elige a sabiendas en vez de tropezarse con ello.
    """
    y, prob, montos = escenario

    sin_piso, _ = evaluacion.buscar_umbrales(
        y, prob, montos, evaluacion.Costos(deteccion_minima=0.0)
    )
    con_piso, _ = evaluacion.buscar_umbrales(
        y, prob, montos, evaluacion.Costos(deteccion_minima=1.0)
    )

    assert con_piso["tasa_de_deteccion"] >= sin_piso["tasa_de_deteccion"]
    # Detectar más nunca sale más barato: si saliera, el piso sobraría.
    assert con_piso["costo_total"] >= sin_piso["costo_total"]
    assert "detectan al menos" in con_piso["regla_aplicada"]


def test_cuando_el_piso_es_inalcanzable_se_dice_en_vez_de_rebajarlo(escenario):
    """
    Un piso imposible no debe rebajarse en silencio: la búsqueda elige lo mejor
    que puede y deja constancia de que no llegó.
    """
    y, prob, montos = escenario
    # Nadie puede detectar más del 100 %, así que con la capacidad de revisión
    # a cero no queda ningún par que cumpla las dos condiciones.
    costos = evaluacion.Costos(deteccion_minima=1.01, capacidad_de_revision=0.05)
    mejor, _ = evaluacion.buscar_umbrales(y, prob, montos, costos)

    assert "ningún par alcanzó el piso" in mejor["regla_aplicada"]
    assert mejor["tasa_de_deteccion"] > 0


def test_no_se_publica_un_modelo_que_detecta_menos():
    """
    Aunque su AUC-PR sea mejor.

    El AUC-PR resume todos los umbrales posibles; el indicador mide el único
    que se va a usar de verdad. Un candidato puede ganar en el resumen y perder
    donde importa.
    """
    reemplaza, motivo, _ = decidir_reemplazo(
        ap_candidato=0.95,
        ap_anterior=0.70,
        casos_de_prueba=500,
        deteccion_candidato=0.60,
        deteccion_anterior=0.85,
    )

    assert reemplaza is False
    assert "detecta menos fraude" in motivo


def test_una_caida_minima_de_deteccion_no_bloquea_la_publicacion():
    """
    La partición de prueba es pequeña y un solo caso mueve el indicador varios
    puntos. Rechazar por ese ruido dejaría el modelo congelado para siempre.
    """
    reemplaza, _, _ = decidir_reemplazo(
        ap_candidato=0.75,
        ap_anterior=0.70,
        casos_de_prueba=500,
        deteccion_candidato=0.85 - CAIDA_TOLERADA_DE_DETECCION / 2,
        deteccion_anterior=0.85,
    )
    assert reemplaza is True


def test_forzar_publica_igual_pero_lo_deja_dicho():
    reemplaza, motivo, _ = decidir_reemplazo(
        ap_candidato=0.95,
        ap_anterior=0.70,
        casos_de_prueba=500,
        forzar=True,
        deteccion_candidato=0.40,
        deteccion_anterior=0.85,
    )
    assert reemplaza is True
    assert "--forzar" in motivo
