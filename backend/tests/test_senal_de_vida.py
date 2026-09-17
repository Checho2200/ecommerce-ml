"""
Pruebas de las dos señales de vida del servicio: `/` y `/health`.

La de la raíz parece trivial y no lo es. Al desplegar, Render comprueba que el
servicio escucha mandando un `HEAD /`, y FastAPI no acepta HEAD solo porque se
haya declarado un GET —Starlette sí lo hace, FastAPI no—. Esa comprobación
recibía un 405, Render anotaba «no open ports detected» y al menos un despliegue
murió con «Port scan timeout reached».
"""


async def test_la_raiz_responde_a_head(cliente):
    """
    Es lo que Render pregunta al desplegar.

    Un 405 aquí no rompe la aplicación —nadie la usa con HEAD— pero sí rompe el
    despliegue, que es peor: el servicio funciona y aun así no llega a estar en
    línea.
    """
    respuesta = await cliente.head("/")

    assert respuesta.status_code == 200


async def test_la_raiz_sigue_respondiendo_a_get(cliente):
    respuesta = await cliente.get("/")

    assert respuesta.status_code == 200
    assert respuesta.json()["status"] == "running"


async def test_health_declara_que_el_cobro_es_simulado(cliente):
    """
    Se puede comprobar desde fuera, sin abrir la tienda.

    Es la tercera pata de la misma promesa: la pantalla avisa, la orden lo
    guarda, y esto permite verificarlo sin ser el comprador ni el administrador.
    """
    datos = (await cliente.get("/health")).json()

    assert datos["payments"] == "simulado"
