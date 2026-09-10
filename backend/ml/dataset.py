"""
De dónde salen los datos con los que se entrena el modelo de fraude.

Hay dos fuentes, y se prefiere la primera:

1. **Las transacciones de la propia tienda.** Cada pedido deja un registro en
   `fraud_logs` con las variables que se usaron para evaluarlo. Cuando un
   administrador revisa un pedido y lo etiqueta —contracargo real o compra
   legítima—, ese registro pasa a ser un ejemplo de entrenamiento.

2. **Un conjunto sintético del dominio.** Mientras la tienda no acumule
   suficientes casos etiquetados de ambas clases, se genera un conjunto a
   partir de cómo se comporta un pedido legítimo frente a uno fraudulento en
   una tienda de componentes de cómputo.

   Nota metodológica: las clases se muestrean primero y las variables se
   generan condicionadas a la clase, con solapamiento deliberado entre ambas.
   El modelo NO aprende una regla determinista: hay pedidos legítimos caros,
   rápidos y a direcciones nuevas, y pedidos fraudulentos que parecen normales.
   Eso es lo que hace que el problema sea de clasificación estadística y no un
   `if` con umbrales.

   Un intento anterior usaba un CSV público de fraude bancario y mapeaba sus
   columnas a estas cuatro variables. No funcionó: las semánticas no coincidían
   (`checkout_duration_seconds` se derivaba de una marca de tiempo ajena, con
   lo que resultaba ruido puro) y el modelo terminaba rechazando compras
   perfectamente normales.
"""

import asyncio
import json
from dataclasses import dataclass

import numpy as np
import pandas as pd

RANDOM_SEED = 42

FEATURES = [
    "total_amount",
    "high_risk_items_count",
    "checkout_duration_seconds",
    "is_new_shipping_address",
    # Cuántos días llevaba abierta la cuenta cuando llegó la compra.
    #
    # Se añadió después de medir el techo de las otras cuatro: con ellas solas,
    # los fraudes que se escapaban puntuaban todos alrededor de 0.146 —monto
    # normal, prisa normal, dirección conocida—, indistinguibles de una compra
    # corriente. Ningún umbral separa lo que el modelo no mira, así que para
    # subir la detección había que darle algo más que mirar.
    #
    # Ésta es la señal más fuerte que la tienda ya tiene sin pedirle nada al
    # cliente: quien entra a defraudar suele estrenar cuenta, y quien compra de
    # verdad lleva meses registrado. No hace falta huella de dispositivo ni
    # histórico de años —que una MYPE no tiene—, solo la fecha de alta que ya
    # está en la tabla de usuarios.
    "account_age_days",
]

ETIQUETA = "is_fraud"

# Nombres legibles, para los informes y para la explicación que ve el
# administrador en el panel.
NOMBRES_LEGIBLES = {
    "total_amount": "monto del pedido",
    "high_risk_items_count": "artículos de alto riesgo",
    "checkout_duration_seconds": "duración del checkout",
    "is_new_shipping_address": "dirección de envío nueva",
    "account_age_days": "antigüedad de la cuenta",
}

# Cuántos casos etiquetados hacen falta para dejar de usar el conjunto
# sintético. Se exige un mínimo por clase, no solo un total: cincuenta pedidos
# de los que solo uno es fraude no alcanzan para aprender nada, y entrenar con
# ellos empeoraría el modelo que ya está en producción.
MINIMO_TOTAL = 200
MINIMO_POR_CLASE = 30

# Qué antigüedad se supone cuando un registro no la trae —los que se guardaron
# antes de que esta variable existiera—. Es la media de un cliente honesto: un
# cero se leería como cuenta recién abierta, que es la señal de fraude.
ANTIGUEDAD_POR_DEFECTO = 120.0

# Cuántos días lleva abierta la tienda. Acota la antigüedad de cualquier
# cuenta: una tienda que abrió en enero no puede tener clientes de hace dos
# años, y generar antigüedades de mil días haría que el conjunto sintético no
# se pareciera a la tienda sobre la que se va a aplicar.
ANTIGUEDAD_MAXIMA_DIAS = 250.0

# Ver el comentario largo en `generar_datos_sinteticos`.
RUIDO_DE_ETIQUETA = 0.004


@dataclass
class Datos:
    """Un conjunto de entrenamiento y de dónde salió."""

    df: pd.DataFrame
    origen: str  # "tienda" o "sintetico"
    detalle: str

    @property
    def X(self) -> pd.DataFrame:
        return self.df[FEATURES]

    @property
    def y(self) -> pd.Series:
        return self.df[ETIQUETA]


# ─────────────────────────────────────────────────────────────────────────────
# 1. Transacciones reales de la tienda
# ─────────────────────────────────────────────────────────────────────────────
async def _consultar_etiquetados() -> pd.DataFrame:
    """
    Lee de la base los pedidos que un administrador ya revisó y etiquetó.

    Se consulta con el motor de la aplicación y no abriendo un archivo SQLite:
    en producción la base es PostgreSQL en Neon. La versión anterior abría
    `backend/sanchez_ecommerce.db` por ruta, un archivo que en el servidor no
    existe, así que el reentrenamiento "con datos reales" volvía siempre al
    conjunto sintético sin decir nada.
    """
    from sqlalchemy import select

    from app.core.database import AsyncSessionLocal, engine
    from app.models.fraud_log import FraudLog
    from app.models.order import Order

    async with AsyncSessionLocal() as sesion:
        resultado = await sesion.execute(
            select(
                Order.total_amount,
                FraudLog.feature_vector,
                FraudLog.is_actual_fraud,
            )
            .join(FraudLog, FraudLog.order_id == Order.id)
            .where(FraudLog.reviewed_at.is_not(None))
        )
        filas = resultado.all()

    await engine.dispose()

    registros = []
    for total_amount, vector, es_fraude in filas:
        if isinstance(vector, str):
            try:
                vector = json.loads(vector)
            except json.JSONDecodeError:
                vector = {}
        vector = vector or {}
        registros.append(
            {
                "total_amount": float(vector.get("total_amount", total_amount)),
                "high_risk_items_count": int(vector.get("high_risk_items_count", 0)),
                "checkout_duration_seconds": float(
                    vector.get("checkout_duration_seconds", 0.0)
                ),
                "is_new_shipping_address": int(vector.get("is_new_shipping_address", 0)),
                # Los registros anteriores a esta variable no la traen. Se les
                # pone la antigüedad media de un cliente honesto en vez de cero:
                # cero diría «cuenta estrenada hoy», que es justo la señal de
                # fraude, y convertiría todo el historial viejo en sospechoso.
                "account_age_days": float(
                    vector.get("account_age_days", ANTIGUEDAD_POR_DEFECTO)
                ),
                ETIQUETA: int(bool(es_fraude)),
            }
        )

    return pd.DataFrame(registros)


def cargar_datos_reales() -> tuple[pd.DataFrame | None, str]:
    """
    Devuelve (datos, motivo). `datos` es None si todavía no alcanzan.

    El motivo se imprime y se guarda en el informe: en una tesis importa poder
    decir con qué se entrenó y por qué, no solo cuánto acertó.
    """
    try:
        df = asyncio.run(_consultar_etiquetados())
    except Exception as exc:  # noqa: BLE001 - se reporta y se sigue con sintéticos
        return None, f"no se pudo consultar la base de datos ({exc})"

    if df.empty:
        return None, "todavía no hay pedidos revisados y etiquetados"

    fraudes = int(df[ETIQUETA].sum())
    legitimos = len(df) - fraudes

    if len(df) < MINIMO_TOTAL:
        return None, (
            f"solo hay {len(df)} pedidos etiquetados y hacen falta {MINIMO_TOTAL}"
        )

    if fraudes < MINIMO_POR_CLASE or legitimos < MINIMO_POR_CLASE:
        return None, (
            f"faltan casos de alguna clase ({fraudes} fraudes y {legitimos} "
            f"legítimos; se piden {MINIMO_POR_CLASE} de cada una)"
        )

    return df, f"{len(df)} pedidos etiquetados ({fraudes} fraudes, {legitimos} legítimos)"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Conjunto sintético del dominio
# ─────────────────────────────────────────────────────────────────────────────
def generar_datos_sinteticos(
    n_muestras: int = 10000,
    tasa_fraude: float = 0.07,
    semilla: int = RANDOM_SEED,
) -> pd.DataFrame:
    """
    Genera transacciones etiquetadas para una tienda de componentes de cómputo.

    Las distribuciones por clase se solapan a propósito: un cliente honesto
    puede comprar una tarjeta de video cara, rápido y a una dirección nueva.
    Ese solapamiento es lo que obliga al modelo a ponderar señales en vez de
    aplicar un umbral por variable.
    """
    rng = np.random.default_rng(semilla)

    n_fraude = int(n_muestras * tasa_fraude)
    n_legitimo = n_muestras - n_fraude

    def muestrear(
        n, monto_mu, monto_sigma, riesgo_lambda, dur_mu, dur_sigma, p_dir_nueva,
        antiguedad_media,
    ):
        return pd.DataFrame(
            {
                # Montos con cola larga: la mayoría de pedidos son modestos y
                # unos pocos son de equipos completos.
                "total_amount": np.clip(rng.lognormal(monto_mu, monto_sigma, n), 40, 30000),
                "high_risk_items_count": np.clip(rng.poisson(riesgo_lambda, n), 0, 12),
                # La duración del checkout también es asimétrica: quien duda
                # tarda minutos; quien tiene los datos cargados, segundos.
                "checkout_duration_seconds": np.clip(
                    rng.lognormal(dur_mu, dur_sigma, n), 4, 3600
                ),
                "is_new_shipping_address": rng.binomial(1, p_dir_nueva, n),
                # La antigüedad se agota rápido y se corta en la edad de la
                # tienda: hay muchos clientes nuevos porque la tienda es nueva,
                # y ninguno puede llevar más tiempo que ella. Ese tope es
                # también lo que impide que la variable separe demasiado bien y
                # el problema deje de ser estadístico.
                "account_age_days": np.clip(
                    rng.exponential(antiguedad_media, n), 0, ANTIGUEDAD_MAXIMA_DIAS
                ),
            }
        )

    # Pedido legítimo típico: ticket moderado, pocos componentes de reventa
    # fácil, el cliente se toma minutos en decidir y suele enviar a una
    # dirección que ya usó antes.
    legitimos = muestrear(
        n_legitimo,
        monto_mu=np.log(450), monto_sigma=1.00,
        riesgo_lambda=0.50,
        dur_mu=np.log(200), dur_sigma=0.85,
        p_dir_nueva=0.20,
        # Un cliente honesto lleva meses registrado, pero en una tienda joven
        # muchos acaban de darse de alta: uno de cada tres lleva menos de mes y
        # medio. Ese solapamiento es lo que impide que la variable sea un `if`.
        antiguedad_media=120.0,
    )
    legitimos[ETIQUETA] = 0

    # Pedido fraudulento típico: ticket alto concentrado en componentes de
    # reventa fácil, checkout resuelto en menos de un minuto porque los datos
    # de pago ya venían cargados, y envío a una dirección nueva.
    fraudulentos = muestrear(
        n_fraude,
        monto_mu=np.log(2200), monto_sigma=0.90,
        riesgo_lambda=2.00,
        dur_mu=np.log(50), dur_sigma=0.85,
        p_dir_nueva=0.72,
        # Quien entra a defraudar estrena cuenta, pero no siempre: una parte usa
        # cuentas robadas con años de historial, y ésas caen en la cola larga.
        antiguedad_media=14.0,
    )
    fraudulentos[ETIQUETA] = 1

    df = pd.concat([legitimos, fraudulentos], ignore_index=True)

    # Ruido de etiqueta: ni todo fraude se denuncia ni toda denuncia es real.
    # Sin nada de ruido las clases quedan casi separables, el modelo responde
    # siempre 0 o 1 y la banda de revisión manual no se activa nunca.
    #
    # Estaba en el 1.5 % y era demasiado, pero no por la cifra en sí: se aplica
    # sobre TODAS las compras y el fraude es solo el 7 %, así que casi todo lo
    # que voltea son compras legítimas que pasan a constar como fraude. Con el
    # 1.5 %, una de cada seis filas de la clase «fraude» se había comportado
    # como una compra corriente —mismo monto, misma prisa, misma cuenta— y
    # ningún modelo puede detectarla: el techo de detección quedaba en el 83 %
    # por construcción, y se estaba leyendo como un límite del clasificador.
    #
    # El 0.4 % se acerca a lo que reportan las pasarelas para el contracargo
    # abusivo —el cliente que sí compró y luego reclama—, deja el techo cerca
    # del 95 % y conserva el solapamiento, que es lo que hacía falta.
    voltear = rng.random(len(df)) < RUIDO_DE_ETIQUETA
    df.loc[voltear, ETIQUETA] = 1 - df.loc[voltear, ETIQUETA]

    return df.sample(frac=1, random_state=semilla).reset_index(drop=True)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Punto de entrada
# ─────────────────────────────────────────────────────────────────────────────
def cargar_datos(preferir_reales: bool = True) -> Datos:
    """Devuelve el mejor conjunto disponible, diciendo de dónde salió."""
    if preferir_reales:
        df, motivo = cargar_datos_reales()
        if df is not None:
            return Datos(df=df, origen="tienda", detalle=motivo)
        print(f"Se usa el conjunto sintético: {motivo}.")

    df = generar_datos_sinteticos()
    fraudes = int(df[ETIQUETA].sum())
    return Datos(
        df=df,
        origen="sintetico",
        detalle=(
            f"{len(df)} transacciones generadas "
            f"({fraudes} fraudulentas, {fraudes / len(df) * 100:.1f}%)"
        ),
    )


if __name__ == "__main__":
    # `python -m ml.dataset` exporta el conjunto y su análisis descriptivo a
    # ml/informes/: el CSV para adjuntarlo como anexo, el diccionario de datos,
    # las estadísticas por clase y las figuras de distribución y correlación.
    import argparse

    from ml.exploracion import exportar

    parser = argparse.ArgumentParser(
        description="Exporta el conjunto de datos de entrenamiento y lo describe."
    )
    parser.add_argument(
        "--reales",
        action="store_true",
        help="Exporta los pedidos etiquetados de la tienda en vez del conjunto sintético.",
    )
    argumentos = parser.parse_args()

    exportar(cargar_datos(preferir_reales=argumentos.reales))
