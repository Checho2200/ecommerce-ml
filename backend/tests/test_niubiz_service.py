"""
Pruebas del servicio de Niubiz, la segunda pasarela.

Lo que se sujeta aquí son las decisiones que no se pueden comprobar mirando la
pantalla: contra qué entorno se está cobrando, qué se guarda de la tarjeta y —la
más importante— la diferencia entre que Niubiz rechace una tarjeta y que Niubiz
no conteste. Confundir esas dos cosas es lo que convertiría la dirección de
retorno, que es pública, en una forma de cancelar pedidos ajenos.
"""

import pytest

from app.services.niubiz_service import (
    ENTORNOS,
    ErrorDeNiubiz,
    NiubizService,
    datos_del_pago_de_niubiz,
    leer_retorno,
)


def _servicio(entorno: str = "test", con_credenciales: bool = True) -> NiubizService:
    servicio = NiubizService()
    servicio.entorno = entorno
    servicio.usuario = "usuario@ejemplo.com" if con_credenciales else ""
    servicio.clave = "clave" if con_credenciales else ""
    servicio.merchant_id = "456879852" if con_credenciales else ""
    return servicio


# ── Configuración ────────────────────────────────────────────────────────────
def test_sin_las_tres_credenciales_no_se_declara_configurado():
    """
    Con una sola que falte, la tienda no ofrece Niubiz.

    Ofrecerlo y fallar después es peor que no ofrecerlo: el comprador ya tiene
    la tarjeta en la mano cuando se entera.
    """
    servicio = _servicio()
    servicio.merchant_id = ""

    assert not servicio.esta_configurado


def test_con_las_tres_credenciales_se_declara_configurado():
    assert _servicio().esta_configurado


async def test_sin_configurar_no_se_intenta_cobrar():
    """Sin credenciales no se llama a la pasarela: se dice que no hay con qué."""
    servicio = _servicio(con_credenciales=False)

    with pytest.raises(ErrorDeNiubiz):
        await servicio.autorizar(
            token_de_transaccion="lo-que-sea", numero_de_compra="1", monto=10.0
        )


# ── Entorno ──────────────────────────────────────────────────────────────────
#
# Las credenciales de Niubiz no llevan marca de entorno, así que lo declarado es
# lo único que hay. Equivocarse aquí manda el formulario a un sitio y la
# autorización a otro, y el pago muere a mitad de camino.
def test_el_entorno_declarado_manda():
    assert _servicio("test").es_de_prueba
    assert not _servicio("produccion").es_de_prueba


def test_cualquier_valor_raro_se_toma_como_pruebas():
    """Ante la duda, no cobrar de verdad: es el error barato."""
    assert _servicio("cualquier-cosa").es_de_prueba


def test_la_api_y_el_formulario_van_siempre_al_mismo_entorno():
    """
    Las tres direcciones cambian juntas.

    Apuntar la API a producción y el formulario a pruebas da un error opaco en
    mitad del pago, que es justo lo que no se quiere depurar en vivo.
    """
    pruebas = _servicio("test")
    assert pruebas._base == ENTORNOS["test"]["api"]
    assert pruebas._checkout_js == ENTORNOS["test"]["checkout_js"]

    produccion = _servicio("produccion")
    assert produccion._base == ENTORNOS["produccion"]["api"]
    assert produccion._checkout_js == ENTORNOS["produccion"]["checkout_js"]


# ── Qué se guarda del cobro ──────────────────────────────────────────────────
def test_de_la_tarjeta_solo_quedan_los_cuatro_ultimos_digitos():
    """
    Niubiz entrega la tarjeta ya enmascarada y aun así se recorta.

    PCI-DSS permite conservar los cuatro últimos precisamente porque no sirven
    para cobrar. Guardar más convertiría esta base en un objetivo que una
    tienda pequeña no tiene por qué ser.
    """
    datos = datos_del_pago_de_niubiz(
        {
            "dataMap": {
                "ACTION_CODE": "000",
                "CARD": "455687******8232",
                "BRAND": "visa",
                "TRANSACTION_ID": "998877",
            }
        }
    )

    assert datos["card_last_four"] == "8232"
    assert "455687" not in str(datos)
    assert datos["payment_id"] == "998877"
    assert datos["payment_method"] == "visa"


def test_el_cobro_queda_marcado_como_de_niubiz():
    """
    Sin esto, un `payment_id` suelto no dice en qué panel buscarlo.

    Es lo primero que hace falta ante un contracargo, y ahora hay dos paneles
    donde mirar.
    """
    datos = datos_del_pago_de_niubiz({"dataMap": {"CARD": "4111********1111"}})

    assert datos["payment_gateway"] == "niubiz"


def test_si_niubiz_no_manda_el_titular_el_campo_queda_vacio():
    """
    Se prefiere «no lo sé» a un nombre que nadie verificó.

    El titular es la señal que usa el revisor para el fraude con tarjeta
    robada: inventarlo sería peor que no tenerlo, porque el panel enseñaría
    como comprobado algo que no lo está.
    """
    datos = datos_del_pago_de_niubiz({"dataMap": {"CARD": "4111********1111"}})

    assert datos["card_holder"] is None


def test_las_dos_pasarelas_escriben_las_mismas_columnas():
    """
    Niubiz y MercadoPago terminan en el mismo sitio de la orden.

    Si una devolviera claves distintas, la confirmación del pago tendría que
    saber de qué pasarela viene, y esa es justo la rama que no queremos.
    """
    from app.services.payment_service import datos_del_pago

    de_mercadopago = set(
        datos_del_pago({"id": 1, "payment_method_id": "visa", "card": {}})
    )
    de_niubiz = set(datos_del_pago_de_niubiz({"dataMap": {}}))

    assert de_mercadopago <= de_niubiz


# ── El formulario de vuelta ──────────────────────────────────────────────────
def test_se_lee_el_token_que_manda_el_formulario():
    token, error = leer_retorno({"transactionToken": "abc123", "channel": "web"})

    assert token == "abc123"
    assert error is None


def test_un_retorno_sin_token_trae_el_motivo():
    """El comprador cerró el modal o la sesión caducó: no se cobró nada."""
    token, error = leer_retorno({"errorMessage": "Sesión expirada"})

    assert token is None
    assert error == "Sesión expirada"
