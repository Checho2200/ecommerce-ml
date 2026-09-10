"""
Pruebas del tercer indicador de la tesis: el tiempo de detección.

Lo que se comprueba aquí es que el número signifique lo que la pantalla dice.
El historial simulado guardaba, en el tramo anterior al modelo, los
milisegundos que el modelo tardaba en puntuar una compra que nadie le había
preguntado: el sistema que decidía era una regla fija más una persona mirando
la cola de revisión. Con eso el indicador comparaba al modelo consigo mismo y
no podía mejorar nunca, por construcción.

Ahora cada tramo guarda el tiempo del sistema que de verdad decidió, y como las
dos magnitudes no se parecen —horas frente a un milisegundo y pico—, se
comprueba también que se escriban de forma legible en el panel y en el Excel.
"""

import numpy as np
import pytest

from app.scripts.simular_historial import (
    REVISION_MANUAL_MAXIMA_S,
    REVISION_MANUAL_MINIMA_S,
    _tiempo_de_deteccion_manual,
)
from app.services.reporte_de_indicadores import duracion_legible


# ── El tiempo del sistema anterior ───────────────────────────────────────────


def test_la_revision_manual_tarda_lo_que_tarda_una_persona():
    """
    Ni segundos ni semanas: el rango de una cola de revisión de verdad.

    Sin el suelo, la lognormal produce de vez en cuando revisiones de dos
    minutos, que es tanto como decir que el sistema anterior también era
    automático y deja el indicador sin nada que mejorar.
    """
    rng = np.random.default_rng(2026)
    muestras = [_tiempo_de_deteccion_manual(rng) for _ in range(2000)]

    assert all(REVISION_MANUAL_MINIMA_S * 1000 <= m <= REVISION_MANUAL_MAXIMA_S * 1000
               for m in muestras)

    media_horas = sum(muestras) / len(muestras) / 3_600_000
    assert 1 < media_horas < 12


def test_la_revision_manual_es_mucho_mas_lenta_que_el_modelo():
    """
    El indicador solo puede mejorar si las dos magnitudes son distintas de
    verdad. El modelo puntúa en un milisegundo y pico; una persona, en horas.
    """
    rng = np.random.default_rng(7)
    manual = [_tiempo_de_deteccion_manual(rng) for _ in range(500)]

    # Tres órdenes de magnitud de holgura sobre un presupuesto de 50 ms.
    assert min(manual) > 50 * 1000


def test_dos_corridas_con_la_misma_semilla_dan_el_mismo_tiempo():
    """El historial tiene que ser reproducible, tiempos incluidos."""
    a = [_tiempo_de_deteccion_manual(np.random.default_rng(11)) for _ in range(3)]
    b = [_tiempo_de_deteccion_manual(np.random.default_rng(11)) for _ in range(3)]

    assert a == b


# ── Cómo se escribe ──────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "milisegundos, esperado",
    [
        (1.317, "1.3 ms"),
        (850.0, "850.0 ms"),
        (4_200.0, "4.2 s"),
        (95_000.0, "2 min"),
        (3_600_000.0, "1.0 h"),
        (15_480_000.0, "4.3 h"),
    ],
)
def test_cada_magnitud_se_escribe_en_su_unidad(milisegundos, esperado):
    """
    «12,600,000.0 ms» es un número que nadie puede leer, y es justo el del
    período con el que hay que comparar.
    """
    assert duracion_legible(milisegundos) == esperado


def test_el_tiempo_del_modelo_sigue_saliendo_en_milisegundos():
    """
    El presupuesto declarado en la tesis son 50 ms, así que el valor del modelo
    tiene que seguir leyéndose en esa unidad y no convertirse a segundos.
    """
    assert duracion_legible(1.317).endswith("ms")
    assert duracion_legible(49.9).endswith("ms")
