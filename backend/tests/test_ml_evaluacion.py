"""
Pruebas de cómo se mide el modelo y de cómo se eligen sus umbrales.

Es la parte del proyecto que sostiene las conclusiones de la tesis, así que
conviene que sus reglas estén fijadas por pruebas y no solo por la última
ejecución que se miró en consola.
"""

import numpy as np

from ml import evaluacion
from ml.dataset import ETIQUETA, FEATURES, generar_datos_sinteticos


# ─────────────────────────────────────────────────────────────────────────────
# Métricas
# ─────────────────────────────────────────────────────────────────────────────
def test_un_clasificador_perfecto_da_uno_en_todo():
    y = [0, 0, 1, 1]
    prob = [0.01, 0.02, 0.98, 0.99]

    m = evaluacion.metricas(y, prob, umbral=0.5)

    assert m["precision"] == 1.0
    assert m["recall"] == 1.0
    assert m["average_precision"] == 1.0
    assert m["matriz_de_confusion"]["falsos_positivos"] == 0
    assert m["matriz_de_confusion"]["falsos_negativos"] == 0


def test_el_acierto_global_engana_y_el_auc_pr_no():
    """
    El caso que justifica toda la elección de métricas: con 5 % de fraude, el
    modelo que aprueba todo acierta el 95 % de las veces y no detecta un solo
    caso. El accuracy lo premia; el AUC-PR lo delata.
    """
    y = [0] * 95 + [1] * 5
    prob = [0.01] * 100  # "todo es legítimo"

    m = evaluacion.metricas(y, prob, umbral=0.5)

    assert m["accuracy"] == 0.95
    assert m["recall"] == 0.0
    assert m["average_precision"] < 0.10


def test_la_matriz_de_confusion_suma_el_total():
    y = np.random.default_rng(0).integers(0, 2, 200)
    prob = np.random.default_rng(1).random(200)

    m = evaluacion.metricas(y, prob)
    celdas = m["matriz_de_confusion"]

    assert sum(celdas.values()) == m["total"] == 200


# ─────────────────────────────────────────────────────────────────────────────
# Costos y umbrales
# ─────────────────────────────────────────────────────────────────────────────
def test_aprobar_un_fraude_cuesta_el_monto_mas_el_cargo():
    costos = evaluacion.Costos()
    # Un solo pedido fraudulento de S/ 1000 que el modelo aprueba.
    resultado = evaluacion.costo_de_los_umbrales(
        [1], [0.01], [1000.0], t_bajo=0.5, t_alto=0.9, costos=costos
    )

    assert resultado["fraudes_aprobados"] == 1
    assert resultado["costo_total"] == 1000.0 + costos.cargo_por_contracargo


def test_bloquear_una_compra_legitima_cuesta_solo_el_margen():
    costos = evaluacion.Costos()
    resultado = evaluacion.costo_de_los_umbrales(
        [0], [0.99], [1000.0], t_bajo=0.3, t_alto=0.7, costos=costos
    )

    assert resultado["legitimos_bloqueados"] == 1
    assert resultado["costo_total"] == 1000.0 * costos.margen_bruto


def test_la_revision_manual_cobra_el_tiempo_y_los_errores_del_revisor():
    """
    Si la revisión se contara como infalible, mandar todo a revisar saldría
    casi gratis y el optimizador elegiría justo eso.
    """
    costos = evaluacion.Costos(acierto_de_la_revision=0.9)
    resultado = evaluacion.costo_de_los_umbrales(
        [1], [0.5], [1000.0], t_bajo=0.3, t_alto=0.7, costos=costos
    )

    esperado = costos.revision_manual + 0.1 * (1000.0 + costos.cargo_por_contracargo)
    assert resultado["pedidos_revisados"] == 1
    assert round(resultado["costo_total"], 2) == round(esperado, 2)


def test_los_umbrales_elegidos_respetan_la_capacidad_de_revision():
    """
    La restricción operativa: por barato que salga en la ecuación, la tienda no
    puede revisar a mano más de lo que puede revisar a mano.
    """
    rng = np.random.default_rng(7)
    n = 500
    y = rng.binomial(1, 0.08, n)
    # Puntajes correlacionados con la etiqueta, pero con mucho solapamiento.
    prob = np.clip(rng.normal(np.where(y == 1, 0.7, 0.3), 0.2), 0, 1)
    montos = rng.lognormal(np.log(500), 1.0, n)

    costos = evaluacion.Costos(capacidad_de_revision=0.10)
    mejor, rejilla = evaluacion.buscar_umbrales(y, prob, montos, costos)

    assert mejor["proporcion_revisada"] <= 0.10
    assert mejor["dentro_de_capacidad"]
    # Y la rejilla completa se conserva para poder dibujar la superficie.
    assert len(rejilla) > 50


def test_el_mejor_par_es_el_mas_barato_entre_los_admisibles():
    rng = np.random.default_rng(11)
    n = 400
    y = rng.binomial(1, 0.1, n)
    prob = np.clip(rng.normal(np.where(y == 1, 0.75, 0.25), 0.18), 0, 1)
    montos = np.full(n, 800.0)

    costos = evaluacion.Costos()
    mejor, rejilla = evaluacion.buscar_umbrales(y, prob, montos, costos)

    admisibles = [f for f in rejilla if f["dentro_de_capacidad"]]
    assert mejor["costo_total"] == min(f["costo_total"] for f in admisibles)


def test_la_comparacion_avisa_cuando_la_referencia_no_era_operable():
    """
    El matiz que hay que declarar en la tesis: los umbrales de referencia
    (0.30 y 0.70) pueden salir mas baratos en la ecuacion, pero solo porque
    mandan a revision manual mas pedidos de los que la tienda puede revisar.
    Comparar costos sin mirar esa restriccion daria una conclusion falsa.
    """
    datos = generar_datos_sinteticos(n_muestras=3000, semilla=3)
    rng = np.random.default_rng(3)
    # Un "modelo" simulado: puntajes ruidosos pero informativos.
    prob = np.clip(
        rng.normal(np.where(datos[ETIQUETA] == 1, 0.72, 0.28), 0.20), 0, 1
    )
    montos = datos["total_amount"]

    costos = evaluacion.Costos()
    mejor, _ = evaluacion.buscar_umbrales(datos[ETIQUETA], prob, montos, costos)
    referencia = evaluacion.costo_de_los_umbrales(
        datos[ETIQUETA], prob, montos, 0.30, 0.70, costos
    )
    comparacion = evaluacion.comparar_con_referencia(
        mejor, referencia, len(datos), costos
    )

    # Los elegidos siempre caben; la referencia no tiene por que.
    assert mejor["proporcion_revisada"] <= costos.capacidad_de_revision
    if comparacion["la_referencia_cabe_en_la_capacidad"]:
        assert mejor["costo_total"] <= referencia["costo_total"]
    else:
        assert (
            comparacion["proporcion_revisada_con_la_referencia"]
            > costos.capacidad_de_revision
        )


# ─────────────────────────────────────────────────────────────────────────────
# Conjunto sintético
# ─────────────────────────────────────────────────────────────────────────────
def test_el_conjunto_sintetico_tiene_la_forma_declarada():
    df = generar_datos_sinteticos(n_muestras=2000, tasa_fraude=0.07, semilla=5)

    assert len(df) == 2000
    assert set(FEATURES).issubset(df.columns)
    # El ruido de etiqueta mueve la proporción, pero no la cambia de orden.
    assert 0.04 < df[ETIQUETA].mean() < 0.11


def test_el_conjunto_sintetico_es_reproducible():
    """Misma semilla, mismos datos: sin esto la tesis no sería replicable."""
    uno = generar_datos_sinteticos(n_muestras=500, semilla=42)
    otro = generar_datos_sinteticos(n_muestras=500, semilla=42)

    assert uno.equals(otro)


def test_las_clases_se_solapan_a_proposito():
    """
    Si las clases fueran separables por un umbral en una variable, el problema
    no necesitaría aprendizaje automático y la tesis se caería sola.
    """
    df = generar_datos_sinteticos(n_muestras=4000, semilla=9)

    legitimos = df[df[ETIQUETA] == 0]["total_amount"]
    fraudulentos = df[df[ETIQUETA] == 1]["total_amount"]

    # Hay pedidos legítimos más caros que el fraude típico, y al revés.
    assert legitimos.max() > fraudulentos.median()
    assert fraudulentos.min() < legitimos.median()
