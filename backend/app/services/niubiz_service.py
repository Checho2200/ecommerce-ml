"""
Cobro con Niubiz, la pasarela de Visa en Perú.

Es la segunda forma de pago de la tienda y **no reemplaza a MercadoPago**: los
dos servicios conviven y el comprador elige en el checkout. Por eso este
archivo no toca nada de `payment_service.py`; se apoya en lo que ya era común a
cualquier pasarela, que es `order_service.registrar_resultado_del_pago`.

La diferencia de fondo con MercadoPago está en quién avisa del cobro.
MercadoPago redirige al comprador a su propio sitio y después notifica por
webhook; si el aviso se pierde —o llega a un servidor dormido, que es lo que
pasa en el plan gratuito de Render— el pedido se queda pendiente aunque la
tarjeta ya se haya cobrado. Niubiz no notifica: la respuesta a la autorización
**es** la confirmación, y llega dentro de la misma petición que la pide. No hay
nada que pueda perderse por el camino.

El flujo son tres tokens encadenados y dos llamadas desde el servidor:

    1. Token de acceso   GET  /api.security/v1/security
                         Con usuario y contraseña en Basic. Dura pocos minutos.

    2. Clave de sesión   POST /api.ecommerce/v2/ecommerce/token/session/{id}
                         Se le dice el monto y desde qué IP se compra. Devuelve
                         una `sessionKey` atada a ese monto.

    3. El formulario     El navegador carga `checkout.js`, que abre un modal
                         SOBRE la tienda con esa clave de sesión. La tarjeta se
                         escribe ahí y viaja a Niubiz, nunca a este servidor.
                         Al terminar, el modal hace un POST del navegador a la
                         dirección de retorno con un `transactionToken`.

    4. Autorización      POST /api.authorization/v3/authorization/ecommerce/{id}
                         Se canjea ese `transactionToken` por el cobro. La
                         respuesta dice si se aprobó.

Que la tarjeta no pase por aquí es lo que mantiene a la tienda fuera del
alcance de PCI-DSS, igual que con MercadoPago: de la tarjeta solo se conocen
después los cuatro últimos dígitos y la marca.
"""

import base64
import json
import time
from dataclasses import dataclass
from typing import Optional

import httpx

from app.core.config import get_settings


# Direcciones de cada entorno. Las tres cambian a la vez, y por eso van juntas:
# apuntar la API a producción y el formulario a pruebas da un error opaco en
# mitad del pago, que es justo lo que no se quiere depurar en vivo.
ENTORNOS = {
    "test": {
        "api": "https://apisandbox.vnforappstest.com",
        "checkout_js": "https://static-content-qas.vnforapps.com/vToken/js/checkout.js",
    },
    "produccion": {
        "api": "https://apiprod.vnforapps.com",
        "checkout_js": "https://static-content.vnforapps.com/vToken/js/checkout.js",
    },
}

# Cuánto se reutiliza el token de acceso antes de volver a pedirlo. Niubiz lo
# entrega con unos minutos de vida; cuatro deja margen de sobra y evita una
# llamada extra en cada compra.
VIDA_DEL_TOKEN_EN_SEGUNDOS = 240

# Niubiz aprueba con este código y rechaza con cualquier otro.
CODIGO_DE_APROBACION = "000"


class ErrorDeNiubiz(Exception):
    """
    Algo salió mal hablando con Niubiz.

    `es_rechazo` separa los dos casos que tienen consecuencias distintas para el
    pedido. Un rechazo es Niubiz diciendo que esa tarjeta no paga: la compra no
    va a completarse y el pedido se cancela. Cualquier otro fallo —la red, un
    token inválido, la pasarela caída— no dice nada sobre la tarjeta, así que el
    pedido se queda pendiente y se puede reintentar. Cancelarlo también en ese
    caso sería regalar una forma de anular pedidos ajenos a quien mandara basura
    a la dirección de retorno, que es pública.
    """

    def __init__(self, mensaje: str, es_rechazo: bool = False):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.es_rechazo = es_rechazo


@dataclass
class SesionDeCobro:
    """Todo lo que el navegador necesita para abrir el formulario de Niubiz."""

    session_key: str
    merchant_id: str
    purchase_number: str
    amount: str
    checkout_js: str
    action_url: str
    es_de_prueba: bool


class NiubizService:
    def __init__(self):
        ajustes = get_settings()
        self.usuario = ajustes.NIUBIZ_USER
        self.clave = ajustes.NIUBIZ_PASSWORD
        self.merchant_id = ajustes.NIUBIZ_MERCHANT_ID
        self.entorno = (ajustes.NIUBIZ_ENTORNO or "test").strip().lower()
        self._token: Optional[str] = None
        self._token_pedido_en: float = 0.0

    # ── Estado de la configuración ───────────────────────────────────────
    @property
    def esta_configurado(self) -> bool:
        """
        Si hay con qué cobrar.

        Hacen falta las tres credenciales. Con una sola que falte, el checkout
        no ofrece Niubiz en lugar de ofrecerlo y fallar cuando el comprador ya
        tiene la tarjeta en la mano.
        """
        return bool(self.usuario and self.clave and self.merchant_id)

    @property
    def es_de_prueba(self) -> bool:
        """
        Si se cobra contra el entorno de pruebas.

        Aquí no hay nada que adivinar, al revés que con MercadoPago: las
        credenciales de Niubiz no llevan marca de entorno, así que manda lo
        declarado y punto. Cualquier valor que no sea "produccion" se toma como
        pruebas, porque equivocarse hacia el lado de no cobrar de verdad es el
        error barato.
        """
        return self.entorno != "produccion"

    @property
    def _base(self) -> str:
        return ENTORNOS["test" if self.es_de_prueba else "produccion"]["api"]

    @property
    def _checkout_js(self) -> str:
        return ENTORNOS["test" if self.es_de_prueba else "produccion"]["checkout_js"]

    # ── 1. Token de acceso ───────────────────────────────────────────────
    async def _token_de_acceso(self) -> str:
        """
        Pide (o reutiliza) el token que autoriza las demás llamadas.

        Se guarda en memoria unos minutos. No es una caché por ahorrar: sin
        ella, cada compra gastaría dos llamadas donde basta una, y en el plan
        gratuito de Render cada llamada de más es latencia que el comprador
        espera mirando una pantalla en blanco.

        Las tres llamadas a Niubiz son asíncronas a propósito. El servidor
        corre con un solo proceso, así que una llamada bloqueante que tardara
        veinte segundos en agotar su plazo dejaría clavada la tienda entera —no
        solo la compra— mientras tanto.
        """
        ahora = time.monotonic()
        if self._token and ahora - self._token_pedido_en < VIDA_DEL_TOKEN_EN_SEGUNDOS:
            return self._token

        credenciales = base64.b64encode(
            f"{self.usuario}:{self.clave}".encode("utf-8")
        ).decode("ascii")

        try:
            async with httpx.AsyncClient(timeout=20.0) as cliente:
                respuesta = await cliente.get(
                    f"{self._base}/api.security/v1/security",
                    headers={"Authorization": f"Basic {credenciales}"},
                )
        except httpx.HTTPError as exc:
            raise ErrorDeNiubiz(f"No se pudo contactar con Niubiz: {exc}") from exc

        if respuesta.status_code not in (200, 201):
            raise ErrorDeNiubiz(
                f"Niubiz rechazó las credenciales ({respuesta.status_code}). "
                "Revisa NIUBIZ_USER, NIUBIZ_PASSWORD y NIUBIZ_ENTORNO."
            )

        # El token viaja como texto plano, no como JSON. Se contempla el JSON
        # igualmente porque algunos entornos lo envuelven en {"accessToken":...}
        # y descubrirlo en producción costaría un pago fallido.
        cuerpo = respuesta.text.strip()
        if cuerpo.startswith("{"):
            try:
                cuerpo = json.loads(cuerpo).get("accessToken", "")
            except json.JSONDecodeError:
                cuerpo = ""

        if not cuerpo:
            raise ErrorDeNiubiz("Niubiz no devolvió un token de acceso.")

        self._token = cuerpo
        self._token_pedido_en = ahora
        return cuerpo

    # ── 2. Clave de sesión ───────────────────────────────────────────────
    async def crear_sesion(
        self,
        *,
        monto: float,
        numero_de_compra: str,
        ip_del_cliente: str,
        correo: str,
        identificador_del_cliente: str,
        antiguedad_en_dias: float,
        action_url: str,
    ) -> SesionDeCobro:
        """
        Abre una sesión de cobro por un monto concreto.

        La clave que devuelve está atada a ese monto: el formulario no puede
        cobrar otra cosa aunque alguien manipule lo que se ve en la pantalla.

        Lo que va en `antifraud` es lo que Niubiz mira con su propio motor, y
        aquí coincide en parte con lo que mira el modelo de esta tienda: el
        correo del comprador, quién es y cuántos días lleva su cuenta abierta.
        No sustituye a la evaluación propia —que ya ocurrió, antes de llegar
        aquí— sino que la acompaña.
        """
        if not self.esta_configurado:
            raise ErrorDeNiubiz("Niubiz no está configurado en este servidor.")

        # Como cadena con dos decimales, no como número: 10.1 escrito como
        # float viaja a veces como 10.100000000000001, y el monto de la sesión
        # tiene que coincidir exactamente con el de la autorización.
        importe = f"{round(float(monto), 2):.2f}"

        cuerpo = {
            "channel": "web",
            "amount": importe,
            "antifraud": {
                "clientIp": ip_del_cliente,
                "merchantDefineData": {
                    "MDD4": correo,
                    "MDD32": identificador_del_cliente,
                    "MDD75": "Registrado",
                    "MDD77": int(max(0, antiguedad_en_dias)),
                },
            },
        }

        autorizacion = await self._token_de_acceso()

        try:
            async with httpx.AsyncClient(timeout=20.0) as cliente:
                respuesta = await cliente.post(
                    f"{self._base}/api.ecommerce/v2/ecommerce/token/session/{self.merchant_id}",
                    headers={
                        "Authorization": autorizacion,
                        "Content-Type": "application/json",
                    },
                    json=cuerpo,
                )
        except httpx.HTTPError as exc:
            raise ErrorDeNiubiz(f"No se pudo contactar con Niubiz: {exc}") from exc

        # 200 o 201: Niubiz no es consistente entre entornos con cuál de los
        # dos usa para esto, y rechazar el 201 dejaría la tienda sin cobrar por
        # una diferencia que no significa nada.
        if respuesta.status_code not in (200, 201):
            raise ErrorDeNiubiz(
                f"Niubiz no abrió la sesión de pago ({respuesta.status_code}): "
                f"{respuesta.text[:200]}"
            )

        clave = (respuesta.json() or {}).get("sessionKey")
        if not clave:
            raise ErrorDeNiubiz("Niubiz no devolvió la clave de sesión.")

        return SesionDeCobro(
            session_key=clave,
            merchant_id=self.merchant_id,
            purchase_number=numero_de_compra,
            amount=importe,
            checkout_js=self._checkout_js,
            action_url=action_url,
            es_de_prueba=self.es_de_prueba,
        )

    # ── 3. Autorización ──────────────────────────────────────────────────
    async def autorizar(
        self, *, token_de_transaccion: str, numero_de_compra: str, monto: float
    ) -> dict:
        """
        Cobra de verdad y devuelve la respuesta de Niubiz.

        Solo devuelve si el cobro se aprobó; un rechazo sale como
        `ErrorDeNiubiz(es_rechazo=True)`, porque no es lo mismo que la pasarela
        no conteste.
        """
        if not self.esta_configurado:
            raise ErrorDeNiubiz("Niubiz no está configurado en este servidor.")

        importe = f"{round(float(monto), 2):.2f}"

        cuerpo = {
            "channel": "web",
            # Automática: el cargo queda hecho en el acto. Es lo que espera el
            # resto del sistema, que retiene la orden marcada por el modelo
            # DESPUÉS de cobrar y anula el cargo si la revisión confirma el
            # fraude. Con captura manual el dinero solo quedaría reservado y
            # habría que capturarlo en otra llamada; sería una mejora, pero
            # cambia una regla del negocio y no se hace de tapadillo.
            "captureType": "automatic",
            "countable": True,
            "order": {
                "tokenId": token_de_transaccion,
                "purchaseNumber": numero_de_compra,
                "amount": importe,
                "currency": "PEN",
            },
        }

        autorizacion = await self._token_de_acceso()

        try:
            async with httpx.AsyncClient(timeout=30.0) as cliente:
                respuesta = await cliente.post(
                    f"{self._base}/api.authorization/v3/authorization/ecommerce/{self.merchant_id}",
                    headers={
                        "Authorization": autorizacion,
                        "Content-Type": "application/json",
                    },
                    json=cuerpo,
                )
        except httpx.HTTPError as exc:
            raise ErrorDeNiubiz(f"No se pudo contactar con Niubiz: {exc}") from exc

        try:
            datos = respuesta.json()
        except ValueError:
            raise ErrorDeNiubiz(
                f"Niubiz respondió algo que no es JSON ({respuesta.status_code})."
            ) from None

        # Un rechazo llega como 400 con el motivo dentro. Que la tarjeta no
        # pase es una respuesta legítima de la pasarela, no una avería.
        if respuesta.status_code == 400:
            raise ErrorDeNiubiz(_motivo_del_rechazo(datos), es_rechazo=True)

        if respuesta.status_code not in (200, 201):
            raise ErrorDeNiubiz(
                f"Niubiz falló al autorizar ({respuesta.status_code}): "
                f"{respuesta.text[:200]}"
            )

        mapa = datos.get("dataMap") or {}
        if str(mapa.get("ACTION_CODE", "")).strip() != CODIGO_DE_APROBACION:
            raise ErrorDeNiubiz(_motivo_del_rechazo(datos), es_rechazo=True)

        return datos


def _motivo_del_rechazo(datos: dict) -> str:
    """Por qué dijo Niubiz que no, en la frase que traiga la respuesta."""
    mapa = datos.get("dataMap") or {}
    return (
        mapa.get("ACTION_DESCRIPTION")
        or datos.get("errorMessage")
        or mapa.get("STATUS")
        or "Niubiz rechazó el pago."
    )


def datos_del_pago_de_niubiz(respuesta: dict) -> dict:
    """
    Saca de la respuesta de Niubiz lo que la tienda puede guardar.

    Es el gemelo de `payment_service.datos_del_pago` —lleva el nombre largo
    para que las dos puedan convivir en el mismo import sin confundirse— y
    devuelve exactamente las
    mismas claves, porque las dos pasarelas escriben en las mismas columnas de
    la orden a través de `registrar_resultado_del_pago`.

    Igual que allí, de la tarjeta se conservan **los cuatro últimos dígitos y
    nada más**. Niubiz la entrega ya enmascarada (`455687******8232`), así que
    el número completo no llega a este servidor en ningún momento.

    Sobre el titular: Niubiz no lo devuelve en la autorización con la
    constancia con que lo hace MercadoPago, y cuando no viene el campo queda
    nulo. Se buscan las claves donde podría aparecer en lugar de inventarlo,
    porque el panel prefiere decir que no lo sabe a enseñar un nombre que nadie
    verificó. Es la señal que usa el revisor para el fraude con tarjeta robada,
    así que conviene mirar la primera respuesta real y ajustar aquí si Niubiz
    la trae con otro nombre.
    """
    mapa = respuesta.get("dataMap") or {}
    enmascarada = str(mapa.get("CARD") or "")
    ultimos = enmascarada[-4:] if len(enmascarada) >= 4 else None

    titular = (
        mapa.get("CARD_HOLDER")
        or mapa.get("CARDHOLDER_NAME")
        or mapa.get("NOMBRE_TITULAR")
        or None
    )

    return {
        "payment_id": str(
            mapa.get("TRANSACTION_ID")
            or mapa.get("TRACE_NUMBER")
            or mapa.get("ID_UNICO")
            or ""
        )
        or None,
        # La marca de la tarjeta ocupa el mismo hueco que el medio de pago de
        # MercadoPago: es lo que el panel enseña como "con qué se pagó".
        "payment_method": (mapa.get("BRAND") or "niubiz"),
        "card_last_four": ultimos,
        "card_holder": titular,
        "payment_gateway": "niubiz",
    }


def leer_retorno(formulario: dict) -> tuple[Optional[str], Optional[str]]:
    """
    Saca (transactionToken, motivo_del_error) del POST que hace el formulario.

    Cuando el comprador completa el pago, `checkout.js` envía desde el
    navegador un formulario a la dirección de retorno. Si algo falló antes de
    llegar a la tarjeta —la sesión caducó, el comprador cerró el modal— llega
    en cambio un mensaje de error.
    """
    token = formulario.get("transactionToken") or formulario.get("tokenId")
    error = formulario.get("errorMessage") or formulario.get("ACTION_DESCRIPTION")
    return (str(token) if token else None, str(error) if error else None)


niubiz_service = NiubizService()
