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


async def test_health_dice_de_que_entorno_es_cada_pasarela(cliente):
    """
    Las dos pasarelas se informan por separado y a propósito.

    Cada una depende de sus propias credenciales, así que se puede estar
    cobrando de prueba por una y de verdad por la otra. Un solo renglón tendría
    que mentir sobre alguna, y creer que se cobra de verdad cuando no —o al
    revés— es el peor malentendido posible con una pasarela.
    """
    datos = (await cliente.get("/health")).json()

    assert datos["payments"] in ("not_configured", "test", "production")
    assert datos["niubiz"] in ("not_configured", "test", "production")
