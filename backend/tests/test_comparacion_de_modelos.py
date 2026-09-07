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


async def test_lightgbm_es_el_que_menos_cuesta(cliente, sesion):
    # Es el criterio con el que se eligió, y el que el panel resalta. Si algún
    # día deja de cumplirse, hay que cambiar el título de la tesis o el modelo,
    # no la tabla.
    cabeceras = await _cabeceras_de_admin(cliente, sesion)

    filas = (await cliente.get("/api/v1/fraud/comparison", headers=cabeceras)).json()[
        "resultados"
    ]
    mas_barato = min(filas, key=lambda f: f["perdida_total"])

    assert mas_barato["modelo"] == "LightGBM", (
        f"el modelo más barato es {mas_barato['modelo']}, no LightGBM"
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
