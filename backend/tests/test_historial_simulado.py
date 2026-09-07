"""
Pruebas del generador de historial simulado.

Lo que hay que proteger aquí no es que el script corra, es que **no mienta**.
Un simulador de tráfico que separa las clases demasiado bien produce un panel
con el 100 % de detección y cero falsas alarmas, que es el resultado que
delata un experimento amañado y lo primero que un jurado pondría en duda.

Así que se comprueban las tres cosas de las que depende esa credibilidad: que
las dos clases se solapen de verdad, que el criterio de decisión sea lo único
que distingue a los dos tramos, y que las etiquetas lleguen con el tiempo en
vez de aparecer todas de golpe.
"""

import random

from app.scripts.simular_historial import (
    COMPRAS_BUENAS_QUE_PARECEN_MALAS,
    FRAUDES_CAMUFLADOS,
    _comportamiento,
    _decidir,
    _ya_se_sabe,
)


def _con_direccion_nueva(es_fraude: bool, cuantas: int = 4000) -> float:
    rng = random.Random(7)
    nuevas = sum(
        1 for _ in range(cuantas) if _comportamiento(es_fraude, rng)["direccion_nueva"]
    )
    return nuevas / cuantas


def test_las_dos_clases_se_solapan_y_ninguna_variable_las_separa():
    fraudes = _con_direccion_nueva(True)
    legitimas = _con_direccion_nueva(False)

    # El fraude usa direcciones nuevas mucho más a menudo, pero ni siempre él
    # ni nunca las compras buenas: si fuera 100 % contra 0 %, la dirección
    # bastaría para clasificar y no haría falta ningún modelo.
    assert 0.55 < fraudes < 0.95, fraudes
    assert 0.05 < legitimas < 0.40, legitimas
    assert fraudes > legitimas


def test_una_parte_del_fraude_se_comporta_como_una_compra_corriente():
    # Es el parámetro que impide que la detección salga en el 100 %.
    assert 0.2 < FRAUDES_CAMUFLADOS < 0.5
    assert 0.05 < COMPRAS_BUENAS_QUE_PARECEN_MALAS < 0.3


def test_el_mismo_puntaje_se_decide_distinto_segun_el_criterio():
    # Un puntaje intermedio: el sistema antiguo lo bloqueaba y el nuevo, con
    # los umbrales elegidos por costo, solo lo manda a revisar. Toda la
    # diferencia entre los dos tramos del historial está aquí.
    puntaje = 0.75

    assert _decidir(puntaje, 0.30, 0.70) == "BLOCKED"
    assert _decidir(puntaje, 0.35, 0.80) == "REVIEW"

    # Y en los extremos los dos coinciden, que es lo esperable.
    assert _decidir(0.05, 0.30, 0.70) == _decidir(0.05, 0.35, 0.80) == "APPROVED"
    assert _decidir(0.99, 0.30, 0.70) == _decidir(0.99, 0.35, 0.80) == "BLOCKED"


def test_saber_lo_que_paso_es_mas_probable_cuanto_mas_vieja_es_la_compra():
    rng = random.Random(11)

    def proporcion(dias: float) -> float:
        return sum(_ya_se_sabe(dias, rng) for _ in range(3000)) / 3000

    hoy, una_semana, un_mes = proporcion(0.2), proporcion(7), proporcion(30)

    assert hoy < una_semana < un_mes
    # Ni siquiera al mes se resuelven todas: de algunas compras la tienda no
    # llega a enterarse nunca, y un historial sin ese resto se nota falso.
    assert un_mes < 1.0


def test_una_compra_de_hoy_todavia_no_esta_resuelta():
    rng = random.Random(3)

    assert _ya_se_sabe(0, rng) is False
    assert _ya_se_sabe(-1, rng) is False
