"""
Pruebas del generador de historial simulado.

Lo que hay que proteger aquí no es que el script corra, es que **no mienta** ni
en un sentido ni en el otro.

Un simulador que separa las clases demasiado bien produce un panel con el
100 % de detección, que es el resultado que delata un experimento amañado. Uno
que las mezcla más de la cuenta produce lo contrario —un modelo que parece muy
peor de lo que es— y también es falso, solo que en su contra. La primera
versión de este script cayó en los dos errores, uno detrás del otro.

La salida de ese dilema no es elegir un solapamiento a ojo, sino no elegirlo:
el tráfico se genera con **las mismas distribuciones** con las que se entrenó y
se midió el modelo, que están en `ml/dataset.py`. Estas pruebas fijan
precisamente eso.
"""

import numpy as np
import pytest

from ml.dataset import generar_datos_sinteticos
from app.scripts.simular_historial import (
    PERFILES,
    RUIDO_DE_ETIQUETA,
    TASA_DE_FRAUDE,
    _decidir,
    _muestra,
    _ya_se_sabe,
)


def _muestras(es_fraude: bool, cuantas: int = 4000) -> list[dict]:
    rng = np.random.default_rng(7)
    return [_muestra(es_fraude, rng) for _ in range(cuantas)]


def _muestreo_completo(cuantas: int = 8000, semilla: int = 7) -> list[dict]:
    """
    Reproduce lo que hace el script: sortear la clase, generar la compra y
    aplicar después el ruido de etiqueta.

    El orden importa para comparar contra `ml/dataset.py`, que también voltea
    etiquetas al final. Sin ese paso, el grupo marcado como fraude de la
    referencia incluye compras baratas —las volteadas— y el nuestro no, y las
    medianas no cuadran aunque las distribuciones sean idénticas.
    """
    rng = np.random.default_rng(semilla)
    filas = []
    for _ in range(cuantas):
        es_fraude = bool(rng.random() < TASA_DE_FRAUDE)
        muestra = _muestra(es_fraude, rng)
        if rng.random() < RUIDO_DE_ETIQUETA:
            es_fraude = not es_fraude
        filas.append({**muestra, "is_fraud": int(es_fraude)})
    return filas


def test_el_trafico_sale_de_la_misma_distribucion_con_la_que_se_entreno():
    """
    Los parámetros de aquí y los de `ml/dataset.py` describen la misma tienda.

    Se comparan las medianas de las dos fuentes en lugar de los parámetros
    sueltos: es lo que de verdad importa —que las compras se parezcan— y no se
    rompe si alguien reescribe el generador de otra manera equivalente.
    """
    referencia = generar_datos_sinteticos(n_muestras=8000, tasa_fraude=TASA_DE_FRAUDE)
    propias = _muestreo_completo()

    for etiqueta in (0, 1):
        suyas = referencia[referencia["is_fraud"] == etiqueta]
        nuestras = [f for f in propias if f["is_fraud"] == etiqueta]

        mediana_suya = float(suyas["total_amount"].median())
        mediana_nuestra = float(np.median([m["monto_objetivo"] for m in nuestras]))
        assert mediana_nuestra == pytest.approx(mediana_suya, rel=0.25), (
            f"los montos de la clase {etiqueta} no se parecen: "
            f"{mediana_nuestra:.0f} frente a {mediana_suya:.0f}"
        )

        duracion_suya = float(suyas["checkout_duration_seconds"].median())
        duracion_nuestra = float(np.median([m["segundos"] for m in nuestras]))
        assert duracion_nuestra == pytest.approx(duracion_suya, rel=0.25)

        direccion_suya = float(suyas["is_new_shipping_address"].mean())
        direccion_nuestra = float(np.mean([m["direccion_nueva"] for m in nuestras]))
        assert direccion_nuestra == pytest.approx(direccion_suya, abs=0.08)


def test_las_dos_clases_se_solapan_y_ninguna_variable_las_separa():
    fraudes = _muestras(True)
    legitimas = _muestras(False)

    # El fraude estrena dirección mucho más a menudo, pero ni siempre él ni
    # nunca las compras buenas: si fuera 100 % contra 0 %, la dirección
    # bastaría para clasificar y no haría falta ningún modelo.
    direccion_fraude = np.mean([m["direccion_nueva"] for m in fraudes])
    direccion_legitima = np.mean([m["direccion_nueva"] for m in legitimas])
    assert 0.4 < direccion_fraude < 0.95
    assert 0.05 < direccion_legitima < 0.45
    assert direccion_fraude > direccion_legitima

    # Y los montos se cruzan: hay compras honestas más caras que el fraude
    # típico, que es lo que obliga al modelo a ponderar señales.
    caras_legitimas = np.mean(
        [m["monto_objetivo"] > np.median([f["monto_objetivo"] for f in fraudes])
         for m in legitimas]
    )
    assert caras_legitimas > 0.03, "ninguna compra buena llega al monto del fraude típico"


def test_hay_ruido_de_etiqueta_como_en_el_conjunto_de_entrenamiento():
    # Ni todo fraude se denuncia ni toda denuncia es real. Sin ese ruido las
    # clases quedan casi separables y la banda de revisión no se activa nunca.
    assert 0 < RUIDO_DE_ETIQUETA < 0.05


def test_los_perfiles_declaran_fraude_mas_caro_y_mas_rapido():
    monto_legitimo, _, riesgo_legitimo, dur_legitima, _, dir_legitima = PERFILES[False]
    monto_fraude, _, riesgo_fraude, dur_fraude, _, dir_fraude = PERFILES[True]

    assert monto_fraude > monto_legitimo
    assert riesgo_fraude > riesgo_legitimo
    assert dur_fraude < dur_legitima
    assert dir_fraude > dir_legitima


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
    rng = np.random.default_rng(11)

    def proporcion(dias: float) -> float:
        return sum(_ya_se_sabe(dias, rng) for _ in range(3000)) / 3000

    hoy, una_semana, un_mes = proporcion(0.2), proporcion(7), proporcion(30)

    assert hoy < una_semana < un_mes
    # Ni siquiera al mes se resuelven todas: de algunas compras la tienda no
    # llega a enterarse nunca, y un historial sin ese resto se nota falso.
    assert un_mes < 1.0


def test_una_compra_de_hoy_todavia_no_esta_resuelta():
    rng = np.random.default_rng(3)

    assert _ya_se_sabe(0, rng) is False
    assert _ya_se_sabe(-1, rng) is False
