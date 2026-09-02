"""
Pruebas de dos decisiones que protegen al modelo que está en producción y de
la exportación del conjunto de datos.

La primera existe por un susto real: un entrenamiento de prueba con 260 pedidos
sembrados dio AUC-PR de 1.0000 y reemplazó al modelo bueno. Un resultado
perfecto en detección de fraude no es una buena noticia, es un síntoma.
"""

from pathlib import Path

from ml.dataset import Datos, generar_datos_sinteticos
from ml.train import MINIMO_EN_PRUEBA, UMBRAL_DE_SOSPECHA, decidir_reemplazo


# ─────────────────────────────────────────────────────────────────────────────
# Publicación del modelo
# ─────────────────────────────────────────────────────────────────────────────
def test_un_candidato_mejor_reemplaza_al_anterior():
    reemplaza, motivo, sospechoso = decidir_reemplazo(0.75, 0.70, casos_de_prueba=2000)

    assert reemplaza
    assert not sospechoso
    assert "0.7500" in motivo


def test_un_candidato_peor_no_reemplaza():
    reemplaza, motivo, _ = decidir_reemplazo(0.60, 0.72, casos_de_prueba=2000)

    assert not reemplaza
    assert "peor" in motivo


def test_un_candidato_peor_se_publica_si_se_fuerza():
    reemplaza, motivo, _ = decidir_reemplazo(0.60, 0.72, casos_de_prueba=2000, forzar=True)

    assert reemplaza
    assert "forzar" in motivo


def test_sin_modelo_previo_se_publica():
    reemplaza, motivo, _ = decidir_reemplazo(0.55, None, casos_de_prueba=2000)

    assert reemplaza
    assert "previo" in motivo


def test_un_resultado_perfecto_se_rechaza():
    """
    El caso que motivó la guarda: AUC-PR de 1.0 significa fuga de datos o
    clases separables, no un modelo mejor.
    """
    reemplaza, motivo, sospechoso = decidir_reemplazo(1.0, 0.72, casos_de_prueba=2000)

    assert not reemplaza
    assert sospechoso
    assert "sospechoso" in motivo


def test_una_particion_de_prueba_diminuta_se_rechaza():
    """Cincuenta pedidos no alcanzan para afirmar que un modelo es mejor."""
    reemplaza, _, sospechoso = decidir_reemplazo(
        0.80, 0.72, casos_de_prueba=MINIMO_EN_PRUEBA - 1
    )

    assert not reemplaza
    assert sospechoso


def test_el_umbral_de_sospecha_deja_pasar_un_resultado_normal():
    reemplaza, _, sospechoso = decidir_reemplazo(
        UMBRAL_DE_SOSPECHA - 0.01, 0.70, casos_de_prueba=2000
    )

    assert reemplaza
    assert not sospechoso


def test_lo_sospechoso_se_puede_publicar_a_mano():
    """Queda la puerta, pero hay que abrirla a propósito."""
    reemplaza, motivo, sospechoso = decidir_reemplazo(
        1.0, 0.72, casos_de_prueba=2000, forzar=True
    )

    assert reemplaza
    assert sospechoso
    assert "forzar" in motivo


# ─────────────────────────────────────────────────────────────────────────────
# Exportación del conjunto de datos
# ─────────────────────────────────────────────────────────────────────────────
def test_la_exportacion_deja_el_csv_y_su_documentacion(tmp_path: Path):
    """
    Lo que se adjunta como anexo de la tesis: el conjunto, qué significa cada
    columna y cómo se distribuye cada variable en cada clase.
    """
    from ml.exploracion import exportar

    datos = Datos(
        df=generar_datos_sinteticos(n_muestras=800, semilla=1),
        origen="sintetico",
        detalle="conjunto de prueba",
    )

    informe = exportar(datos, destino=tmp_path)

    assert (tmp_path / "dataset_sintetico.csv").exists()
    assert (tmp_path / "diccionario_de_datos.md").exists()
    assert (tmp_path / "estadisticas_del_dataset.json").exists()
    assert (tmp_path / "estadisticas_del_dataset.md").exists()
    assert informe["filas"] == 800


def test_las_estadisticas_muestran_el_solapamiento_entre_clases(tmp_path: Path):
    """
    El número que sostiene la elección del método: si las clases no se
    solaparan, bastaría un umbral por variable y no haría falta un modelo.
    """
    from ml.exploracion import describir

    df = generar_datos_sinteticos(n_muestras=3000, semilla=2)
    resumen = describir(df)["por_variable"]

    solapamiento = resumen["total_amount"]["solapamiento_con_el_fraude"]
    assert solapamiento is not None
    assert solapamiento > 0.05, "sin solapamiento el problema sería trivial"

    # Y las medias de las dos clases se reportan por separado.
    assert (
        resumen["total_amount"]["fraudulentas"]["media"]
        > resumen["total_amount"]["legitimas"]["media"]
    )


def test_una_variable_binaria_no_reporta_solapamiento(tmp_path: Path):
    """
    En una binaria el rango intercuartílico cubre todo y el número saldría 1
    siempre, sin significar nada: mejor no darlo que darlo mal.
    """
    from ml.exploracion import describir

    resumen = describir(generar_datos_sinteticos(n_muestras=1500, semilla=4))["por_variable"]

    assert resumen["is_new_shipping_address"]["solapamiento_con_el_fraude"] is None


def test_el_diccionario_describe_todas_las_columnas():
    from ml.dataset import ETIQUETA, FEATURES
    from ml.exploracion import diccionario_de_datos

    texto = diccionario_de_datos()

    for columna in FEATURES + [ETIQUETA]:
        assert f"`{columna}`" in texto
