"""
Schemas Pydantic para órdenes de compra.
"""

from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


# --- OrderItem ---
class OrderItemCreate(BaseModel):
    """Item dentro de una orden."""
    product_id: str
    quantity: int = Field(..., gt=0)


class OrderItemResponse(BaseModel):
    """Respuesta de item de orden."""
    id: int
    product_id: str
    product_name: Optional[str] = None
    quantity: int
    unit_price: float

    model_config = {"from_attributes": True}


# --- Order ---
class OrderCreate(BaseModel):
    """Crear nueva orden de compra."""
    items: List[OrderItemCreate] = Field(..., min_length=1)
    shipping_address: str = Field(..., min_length=5)
    shipping_city: str = Field(..., min_length=2, max_length=100)
    checkout_duration_seconds: Optional[float] = None


class OrderStatusUpdate(BaseModel):
    """Actualizar estado de una orden (admin)."""
    status: str


class OrderResponse(BaseModel):
    """Respuesta de orden con items."""
    id: str
    user_id: str
    total_amount: float
    status: str
    shipping_address: Optional[str] = None
    shipping_city: Optional[str] = None
    items: List[OrderItemResponse] = []
    fraud_score: Optional[float] = None
    fraud_decision: Optional[str] = None
    fraud_explanation: Optional[str] = None
    fraud_log_id: Optional[str] = None
    payment_url: Optional[str] = None

    # ── Quién compró y con qué pagó ───────────────────────────────────────
    #
    # El correo y el nombre salen de la cuenta; los datos de tarjeta, del
    # cobro, y solo cuando lo hubo. Son los cuatro últimos dígitos y el
    # titular: el número completo y el código de seguridad nunca llegan a la
    # tienda, los maneja MercadoPago.
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    payment_id: Optional[str] = None
    payment_method: Optional[str] = None
    payment_gateway: Optional[str] = None
    card_last_four: Optional[str] = None
    card_holder: Optional[str] = None
    paid_at: Optional[datetime] = None

    # Si este servidor puede cobrar con Niubiz. La tienda ofrece dos pasarelas
    # y cada una depende de sus propias credenciales, así que el checkout tiene
    # que saber cuáles hay antes de pintar los botones: ofrecer una que no está
    # configurada manda al comprador a un error con la tarjeta ya en la mano.
    niubiz_disponible: bool = False

    # Si este servidor está cobrando con la pasarela simulada. El checkout lo
    # necesita para enseñar el formulario propio en lugar de mandar a nadie a
    # una pasarela, y para avisar de que no se hará ningún cargo.
    pago_simulado: bool = False

    created_at: datetime

    model_config = {"from_attributes": True}


class PagoSimuladoRequest(BaseModel):
    """
    La tarjeta que alguien escribe en el formulario de pago simulado.

    El número viaja para poder validarlo —con Luhn, como haría una pasarela— y
    para sacar los cuatro últimos dígitos, pero **no se guarda**: de él solo
    sobreviven esos cuatro. Aunque aquí no haya dinero de por medio, la
    costumbre de no conservar el número completo es lo que evita el accidente el
    día que lo haya.
    """

    numero: str = Field(..., min_length=13, max_length=25)
    mes: int = Field(..., ge=1, le=12)
    anio: int = Field(..., ge=2000, le=2100)
    cvv: str = Field(..., min_length=3, max_length=4)
    titular: str = Field(..., min_length=3, max_length=150)


class PagoSimuladoResponse(BaseModel):
    """Cómo terminó el intento de cobro simulado."""

    aprobado: bool
    # Qué le pasó al pedido: "completada", "retenida", "cancelada"…
    estado_del_pedido: str
    # El motivo del rechazo, cuando lo hay. Una pasarela real tampoco dice más.
    motivo: Optional[str] = None


class NiubizSessionResponse(BaseModel):
    """
    Lo que el navegador necesita para abrir el formulario de Niubiz.

    Todo viene del backend, incluida la dirección del script y la del retorno.
    Así el frontend no tiene que saber en qué entorno se está cobrando ni
    guardar una copia de esas direcciones que se quede vieja: hay una sola
    fuente de verdad, que es la configuración del servidor.

    Aquí no viaja ningún secreto. La clave de sesión sirve para un solo cobro,
    por un monto fijo, y el código de comercio es público por definición: va en
    el formulario que ve cualquiera.
    """

    session_key: str
    merchant_id: str
    purchase_number: str
    amount: str
    checkout_js: str
    action_url: str
    # Para poder avisar en pantalla cuando se está cobrando contra el entorno
    # de pruebas, y que nadie crea que pagó de verdad.
    es_de_prueba: bool


class OrderListResponse(BaseModel):
    """Respuesta paginada de órdenes."""
    items: List[OrderResponse]
    total: int
    page: int
    pages: int


class OrderSummaryResponse(BaseModel):
    """
    Resumen de la tienda para el panel: cuántos pedidos hay en cada estado y
    cuánto dinero representan.

    Existe para que el panel no tenga que pedir la lista de órdenes una vez por
    estado solo para leer el `total` de cada respuesta. Es una consulta
    agrupada, no seis paginadas.
    """

    total: int
    # Estado del pedido -> cuántos hay. Solo aparecen los que existen.
    by_status: Dict[str, int]
    # Cobrado de verdad: pedidos aprobados o completados.
    revenue: float
    # Pedidos que el modelo dejó retenidos y esperan que alguien los mire.
    awaiting_review: int
