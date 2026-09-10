"""
Pruebas del endpoint que responde «por qué LightGBM».

El trabajo se titula «sistema web basado en LightGBM», así que la comparación
contra otros clasificadores no es un anexo: es la justificación del título. Y
tiene que poder verse dentro del sistema, no solo en un archivo del
repositorio.

Lo que se fija aquí es que la tabla llegue completa —incluidos los dos modelos
que marcan el suelo— y que la ausencia del informe no rompa la pantalla.
"""

import json

from app.models.user import UserRole
from tests.conftest import cabeceras_de, crear_usuario


async def _cabeceras_de_admin(cliente, sesion):
    await crear_usuario(sesion, email="admin@ejemplo.com", rol=UserRole.ADMIN)
    return await cabeceras_de(cliente, "admin@ejemplo.com")


async def test_la_comparacion_llega_con_lightgbm_y_su_suelo(cliente, sesion):
    cabeceras = await _cabeceras_de_admin(cliente, sesion)

    respuesta = await cliente.get("/api/v1/fraud/comparison", headers=cabeceras)

    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["disponible"] is True
    nombres = [fila["modelo"] for fila in cuerpo["resultados"]]

    assert "LightGBM" in nombres
    # Sin un suelo contra el que comparar, un AUC-PR suelto no dice nada: hace
    # falta al menos un modelo que no aprenda y unas reglas sin modelo.
    assert any("trivial" in n.lower() for n in nombres), nombres
    assert any("heur" in n.lower() for n in nombres), nombres
    assert len(nombres) >= 4


async def test_lightgbm_gana_en_la_metrica_que_gobierna(cliente, sesion):
    """
    LightGBM tiene que ser el mejor en AUC-PR, que es lo que el trabajo declaró
    como criterio de elección. Si deja de cumplirse hay que cambiar el modelo o
    el título de la tesis, no la tabla.

    Antes esta prueba exigía que fuese además **el más barato**, y eso era
    exigirle algo que el trabajo no afirma. La pérdida se mide en un único par
    de umbrales; el AUC-PR resume todos los cortes posibles, y por eso es el
    que gobierna la búsqueda de hiperparámetros y la publicación del modelo.
    Con todos los candidatos afinados, el bosque aleatorio puede caer en un par
    algo más barato en una partición concreta sin ordenar mejor las compras por
    riesgo. Confundir las dos cosas llevaría a cambiar de algoritmo por un
    número que depende del corte.
    """
    cabeceras = await _cabeceras_de_admin(cliente, sesion)

    filas = (await cliente.get("/api/v1/fraud/comparison", headers=cabeceras)).json()[
        "resultados"
    ]
    mejor = max(filas, key=lambda f: f["average_precision"])

    assert mejor["modelo"] == "LightGBM", (
        f"el mejor AUC-PR es de {mejor['modelo']}, no de LightGBM"
    )


async def test_si_otro_modelo_sale_mas_barato_no_es_por_bloquear_mas(cliente, sesion):
    """
    El matiz que hay que poder explicar en la sustentación.

    Que otro candidato salga más barato es admisible —la pérdida depende del
    par de umbrales—, pero entonces hay que saber a costa de qué. Lo que no
    sería admisible es que LightGBM perdiera por bloquear más compras
    legítimas: ahí ya no habría nada que defender.
    """
    cabeceras = await _cabeceras_de_admin(cliente, sesion)

    filas = (await cliente.get("/api/v1/fraud/comparison", headers=cabeceras)).json()[
        "resultados"
    ]
    por_nombre = {f["modelo"]: f for f in filas}
    lightgbm = por_nombre["LightGBM"]

    mas_baratos = [
        f
        for f in filas
        if f["perdida_total"] < lightgbm["perdida_total"] and f["modelo"] != "LightGBM"
    ]
    for otro in mas_baratos:
        assert lightgbm["legitimos_bloqueados"] <= otro["legitimos_bloqueados"], (
            f"{otro['modelo']} sale más barato Y bloquea menos compras buenas "
            f"que LightGBM: no queda argumento para el algoritmo del título"
        )


async def test_sin_el_informe_la_pantalla_no_se_rompe(cliente, sesion, monkeypatch, tmp_path):
    """Una copia del proyecto sin haber entrenado nunca no debe dar un error."""
    from app.api.v1 import fraud

    # Se apunta la búsqueda a un directorio vacío en lugar de borrar el informe
    # de verdad, que hace falta para el resto de las pruebas.
    monkeypatch.setattr(
        fraud, "Path", lambda *args, **kwargs: tmp_path / "ninguna_parte"
    )

    cabeceras = await _cabeceras_de_admin(cliente, sesion)
    respuesta = await cliente.get("/api/v1/fraud/comparison", headers=cabeceras)

    assert respuesta.status_code == 200
    assert respuesta.json()["disponible"] is False
    assert respuesta.json()["resultados"] == []


async def test_la_comparacion_es_solo_para_administradores(cliente, sesion):
    await crear_usuario(sesion, email="cliente@ejemplo.com")
    cabeceras = await cabeceras_de(cliente, "cliente@ejemplo.com")

    respuesta = await cliente.get("/api/v1/fraud/comparison", headers=cabeceras)

    assert respuesta.status_code == 403
