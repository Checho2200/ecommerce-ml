import mercadopago
from fastapi import HTTPException
from typing import List, Dict, Any

from app.core.config import get_settings

# El token SIEMPRE viene de la configuración. Antes había uno de prueba escrito
# en el código como valor por defecto: quedó inservible (MercadoPago lo
# rechaza) y además viajaba en el repositorio, que es público.
#
# Y se lee por `get_settings()` y no por `os.getenv` como antes. La diferencia
# importa: pydantic carga también el archivo `.env`, y `os.getenv` no. Con la
# versión anterior, poner el token en `backend/.env` —que es lo que dicen el
# README y el .env.example— no surtía ningún efecto en local, y el checkout
# respondía 503 sin pista de por qué. En Render funcionaba igual porque allí
# las variables son de verdad del entorno, así que el fallo solo aparecía en la
# máquina de quien estuviera desarrollando.


def leer_notificacion(query: dict, body: dict) -> tuple:
    """
    Saca (payment_id, es_de_pago) de una notificacion de MercadoPago.

    Hay dos formatos vivos: los webhooks actuales mandan "type" en la query y
    {"action", "data": {"id"}} en el cuerpo JSON, y el IPN antiguo manda solo
    "topic" e "id" en la query. Se aceptan los dos.

    Vive aqui, junto al resto de la integracion con la pasarela, y no en el
    router: es conocimiento sobre MercadoPago, no sobre HTTP.
    """
    topic = query.get("type") or query.get("topic") or body.get("type") or ""
    action = query.get("action") or body.get("action") or ""
    payment_id = (
        query.get("data.id")
        or query.get("id")
        or (body.get("data") or {}).get("id")
    )

    es_de_pago = topic == "payment" or str(action).startswith("payment.")
    return payment_id, es_de_pago


def datos_del_pago(pago: dict) -> dict:
    """
    Saca de la respuesta de MercadoPago lo que la tienda puede guardar.

    Con qué tarjeta se pagó es información de seguimiento: ante un contracargo
    hay que poder decir qué pago fue y a nombre de quién sin ir a buscarlo al
    panel de la pasarela. Y el titular delata el caso más común de tarjeta
    robada, que es que la cuenta sea de una persona y la tarjeta de otra.

    Lo que se extrae son **los cuatro últimos dígitos y nada más**. Ni el
    número completo, ni el código de seguridad, ni la caducidad: PCI-DSS
    permite conservar los cuatro últimos porque no sirven para cobrar, y
    guardar el resto convertiría esta base en un objetivo que una tienda
    pequeña no tiene por qué ser. Tampoco se guardan los seis primeros —el BIN
    del emisor—, que no hacen falta para el seguimiento.

    Un pago por otro medio (Yape, efectivo) no trae tarjeta: los campos salen
    nulos y el panel lo enseña como lo que es.
    """
    tarjeta = pago.get("card") or {}
    titular = (tarjeta.get("cardholder") or {}).get("name")

    return {
        "payment_id": str(pago["id"]) if pago.get("id") is not None else None,
        "payment_method": pago.get("payment_method_id"),
        "card_last_four": tarjeta.get("last_four_digits"),
        "card_holder": titular,
    }


class PaymentService:
    def __init__(self):
        ajustes = get_settings()
        self.access_token = ajustes.MERCADOPAGO_ACCESS_TOKEN
        self.entorno = ajustes.MERCADOPAGO_ENTORNO
        self.sdk = mercadopago.SDK(self.access_token) if self.access_token else None

    @property
    def is_configured(self) -> bool:
        return self.sdk is not None

    @property
    def es_de_prueba(self) -> bool:
        """
        Si se está cobrando contra el entorno de pruebas de MercadoPago.

        Manda lo que diga `MERCADOPAGO_ENTORNO`, y si está vacío se cae al
        prefijo del token.

        Deducirlo del prefijo era lo único que había, y funcionaba mientras
        MercadoPago entregaba las credenciales de prueba con `TEST-` delante.
        Ya no lo hace: hoy las de prueba salen del panel con `APP_USR-`, el
        mismo prefijo que las de producción. Un sistema que adivina el entorno
        por ahí se equivoca en silencio, y equivocarse aquí es la peor
        confusión posible con una pasarela — creer que se cobra de verdad
        cuando no, o al revés.

        Se conserva la deducción por prefijo para no romper una instalación que
        ya venía funcionando con un token antiguo, pero declararlo gana.
        """
        declarado = (self.entorno or "").strip().lower()
        if declarado:
            return declarado in ("test", "prueba", "pruebas", "sandbox")
        return self.access_token.startswith("TEST-")

    def create_preference(self, order_id: str, items: List[Dict[str, Any]], payer_email: str) -> str:
        """
        Creates a MercadoPago preference and returns the init_point (URL to redirect the user).
        """
        # Convert our items format to MP format
        mp_items = []
        for item in items:
            mp_items.append({
                "title": item.get("title", "Producto"),
                "quantity": int(item.get("quantity", 1)),
                "unit_price": float(item.get("unit_price", 0.0)),
                "currency_id": "PEN"  # Assuming Peruvian Soles
            })

        # URLs de retorno del checkout y de la notificación de pago. Salen de
        # la configuración, que lee tanto el entorno como el archivo `.env`.
        ajustes = get_settings()
        FRONTEND_URL = ajustes.FRONTEND_URL
        BACKEND_URL = ajustes.BACKEND_URL
        notification_url = f"{BACKEND_URL}/api/v1/orders/webhook/mercadopago"

        preference_data = {
            "items": mp_items,
            "payer": {
                "email": payer_email
            },
            "back_urls": {
                "success": f"{FRONTEND_URL}/checkout/success?order_id={order_id}",
                "failure": f"{FRONTEND_URL}/checkout/failure?order_id={order_id}",
                # Un pago pendiente no es un pago fallido: con tarjeta ocurre
                # cuando MercadoPago lo deja en revision y puede acabar
                # aprobandose. Mandarlo a /failure le decia al cliente que su
                # compra habia fallado cuando todavia no se sabia.
                "pending": f"{FRONTEND_URL}/checkout/pending?order_id={order_id}"
            },
            # Volver solo al terminar: MercadoPago exige que `back_urls.success`
            # sea una dirección que él pueda alcanzar, y rechaza la preferencia
            # entera —400 `invalid_auto_return`— si no lo es.
            #
            # En una máquina de desarrollo esa dirección es `localhost`, así que
            # pedir `auto_return` allí hacía imposible crear ninguna
            # preferencia: el checkout no daba enlace de pago y nadie podía
            # comprar en local. Se pide cuando sirve y se omite cuando no; lo
            # único que se pierde es que el comprador vuelva solo, en lugar de
            # pulsar «volver al sitio».
            **(
                {"auto_return": "approved"}
                if FRONTEND_URL.startswith("https://")
                else {}
            ),
            "external_reference": str(order_id),
            # Solo tarjeta. El resto de medios que ofrece Checkout Pro en Peru
            # (PagoEfectivo, banca y agentes, transferencia) llenaban de ruido
            # el checkout, y ademas no encajan con el sistema: la deteccion de
            # fraude cubre el pago con tarjeta no presente, donde existe el
            # riesgo de tarjeta robada y contracargo. En un pago que el propio
            # comprador empuja desde su banco o en efectivo no hay nada que
            # detectar.
            "payment_methods": {
                "excluded_payment_types": [
                    {"id": "ticket"},         # efectivo / PagoEfectivo
                    {"id": "atm"},            # banca y agentes
                    {"id": "bank_transfer"},  # transferencia bancaria
                ],
                # Yape aparte, y por un motivo que no se ve venir: MercadoPago
                # lo tiene registrado como `debit_card`, no como billetera ni
                # como transferencia. Consultando los medios de pago de la
                # cuenta sale literalmente `debit_card / yape`. Por eso excluir
                # tipos no lo quitaba del checkout y hay que nombrarlo.
                #
                # Se excluye por la misma razón que el efectivo y la
                # transferencia: la detección de fraude de esta tienda cubre el
                # pago con tarjeta no presente, donde existen la tarjeta robada
                # y el contracargo. En un pago que el comprador empuja desde su
                # propia aplicación no hay nada que detectar, y además no deja
                # datos de tarjeta —ni los cuatro últimos dígitos ni el
                # titular—, que es justo lo que mira el revisor cuando el modelo
                # retiene un pedido.
                "excluded_payment_methods": [
                    {"id": "yape"},
                ],
            },
            # Important: Set the webhook URL
            "notification_url": notification_url,
            # Force HTTPS for notification url? MP requires it, but in test mode it might accept http if using some tunneling, 
            # though actually MP strictly requires HTTPS. If testing locally, we'll need ngrok.
        }

        if not self.is_configured:
            raise HTTPException(
                status_code=503,
                detail="Los pagos no están configurados: falta MERCADOPAGO_ACCESS_TOKEN.",
            )

        try:
            preference_response = self.sdk.preference().create(preference_data)
            preference = preference_response["response"]

            # Que el rechazo no pase en silencio.
            #
            # El SDK no lanza excepción cuando MercadoPago contesta 400: devuelve
            # la respuesta con el motivo dentro y sin `init_point`. El código
            # anterior leía `init_point`, se encontraba un `None` y lo devolvía
            # tal cual, así que el pedido acababa sin enlace de pago y la tienda
            # decía «no pudimos iniciar el pago» sin más. El motivo —que
            # MercadoPago sí había dado— se perdía entero, y con él la única
            # pista para arreglar nada.
            #
            # Ahora se mira el código de estado y se repite lo que dijo la
            # pasarela, en el log y en la respuesta.
            estado = preference_response.get("status")
            if estado is not None and int(estado) >= 400:
                motivo = (
                    preference.get("message")
                    or preference.get("error")
                    or "MercadoPago rechazó la preferencia sin decir por qué."
                )
                print(
                    f"MercadoPago rechazó la preferencia ({estado}): "
                    f"{preference.get('error')} - {motivo}"
                )
                raise HTTPException(
                    status_code=502, detail=f"MercadoPago: {motivo}"
                )

            # The init_point is the URL where the user should be redirected to pay
            init_point = preference.get("init_point")
            
            # A dónde se manda al comprador.
            #
            # `init_point` es el enlace que corresponde a las credenciales con
            # las que se creó la preferencia: con credenciales de prueba abre el
            # checkout de pruebas, y con las de producción el real. Es el que
            # hay que usar.
            #
            # `sandbox_init_point` es del esquema antiguo, cuando el token de
            # pruebas empezaba por `TEST-` y había que pedir el enlace de
            # sandbox aparte. Se sigue usando si el token es de ese formato y
            # MercadoPago lo devuelve, para no romper una integración vieja;
            # con las credenciales de hoy no viene, y forzarlo devolvería None
            # y dejaría al comprador sin enlace de pago.
            sandbox_init_point = preference.get("sandbox_init_point")
            if self.access_token.startswith("TEST-") and sandbox_init_point:
                return sandbox_init_point

            if not init_point:
                # Respuesta buena y sin enlace: no debería ocurrir, pero
                # devolver `None` aquí es lo que dejaba al comprador con un
                # pedido que no se puede pagar y sin explicación.
                print(f"MercadoPago respondió sin init_point: {preference}")
                raise HTTPException(
                    status_code=502,
                    detail="MercadoPago no devolvió un enlace de pago.",
                )

            return init_point

        except HTTPException:
            # Ya lleva dentro lo que dijo MercadoPago; envolverla en un 500
            # genérico sería volver al problema que esto arregla.
            raise
        except Exception as e:
            print(f"Error creating MP preference: {str(e)}")
            raise HTTPException(
                status_code=502, detail=f"Error creando la preferencia de pago: {e}"
            )

    def verify_payment(self, payment_id: str) -> dict:
        """
        Verify a payment status in MercadoPago API.
        Used by the webhook.
        """
        if not self.is_configured:
            raise HTTPException(
                status_code=503,
                detail="Los pagos no están configurados: falta MERCADOPAGO_ACCESS_TOKEN.",
            )

        try:
            payment_info = self.sdk.payment().get(payment_id)
            return payment_info["response"]
        except Exception as e:
            print(f"Error verifying payment {payment_id}: {str(e)}")
            raise

payment_service = PaymentService()
