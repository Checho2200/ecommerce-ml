"""
Servicio de detección de fraude.

Envuelve el modelo LightGBM entrenado en `ml/train.py` y traduce su salida a
una decisión que el resto del sistema entiende: aprobar, mandar a revisión o
bloquear.

Dos cosas que no son obvias:

**Los umbrales no están escritos aquí.** Vienen del archivo
`fraud_model.meta.json` que produce el entrenamiento, donde se eligieron
minimizando el costo en soles de los errores (ver `ml/evaluacion.py`). Si ese
archivo no existe se usan los valores históricos 0.30 y 0.70, que es lo que
había antes de medirlos.

**La explicación se calcula, no se inventa.** LightGBM puede devolver, para
cada predicción, cuánto empujó cada variable el resultado —son valores SHAP,
calculados de forma exacta por el propio árbol, sin ninguna librería extra—.
Con eso el administrador ve *por qué* se bloqueó un pedido. Antes todos los
pedidos de alto riesgo recibían la misma frase fija, que no explicaba nada.
"""

import json
import os
import time
from dataclasses import dataclass, field
from typing import Optional

import joblib
import pandas as pd

# El orden importa: es el mismo con el que se entrenó el modelo.
FEATURES = [
    "total_amount",
    "high_risk_items_count",
    "checkout_duration_seconds",
    "is_new_shipping_address",
]

UMBRAL_APROBACION_POR_DEFECTO = 0.30
UMBRAL_BLOQUEO_POR_DEFECTO = 0.70

# Cuántos factores se nombran en la explicación. Tres es lo que cabe en una
# línea del panel sin que deje de leerse.
FACTORES_EN_LA_EXPLICACION = 3


@dataclass
class Evaluacion:
    """Lo que el modelo dice de un pedido."""

    puntaje: float
    decision: str  # APPROVED | REVIEW | BLOCKED
    nivel_de_riesgo: str  # LOW | MEDIUM | HIGH
    explicacion: str
    milisegundos: float
    aportes: dict = field(default_factory=dict)


# Nombre legible de cada variable, para el panel de administración.
NOMBRES = {
    "total_amount": "monto del pedido",
    "high_risk_items_count": "artículos de alto riesgo",
    "checkout_duration_seconds": "duración del checkout",
    "is_new_shipping_address": "dirección de envío",
}


def _frase(variable: str, valor: float) -> str:
    """
    Describe una variable y su valor en una sola frase.

    Se arma completa en lugar de pegar "nombre + valor" porque en español eso
    produce cosas como "artículos de alto riesgo 4 artículos de alto riesgo".
    """
    if variable == "total_amount":
        return f"monto de S/ {valor:,.2f}"
    if variable == "checkout_duration_seconds":
        if valor < 60:
            return f"checkout de {valor:.0f} s"
        return f"checkout de {valor / 60:.1f} min"
    if variable == "high_risk_items_count":
        cantidad = int(valor)
        return f"{cantidad} artículo{'s' if cantidad != 1 else ''} de alto riesgo"
    if variable == "is_new_shipping_address":
        return "dirección de envío nueva" if int(valor) else "dirección de envío conocida"
    return f"{NOMBRES.get(variable, variable)}: {valor:g}"


class FraudDetectionService:
    def __init__(self):
        self.model = None
        self.model_path = os.path.join(os.path.dirname(__file__), "fraud_model.joblib")
        self.meta_path = os.path.join(os.path.dirname(__file__), "fraud_model.meta.json")
        self.umbral_aprobacion = UMBRAL_APROBACION_POR_DEFECTO
        self.umbral_bloqueo = UMBRAL_BLOQUEO_POR_DEFECTO
        self.metadatos: dict = {}
        # Se calcula la primera vez que se pide y no cambia mientras el modelo
        # sea el mismo; `recargar` lo borra.
        self._valor_base: Optional[float] = None

    # ── Carga ────────────────────────────────────────────────────────────────
    def load_model(self):
        """Carga el modelo LightGBM y los umbrales que se eligieron al entrenarlo."""
        if self.model is None:
            if os.path.exists(self.model_path):
                try:
                    self.model = joblib.load(self.model_path)
                    print(f"✅ Modelo de fraude cargado desde: {self.model_path}")
                except Exception as e:
                    print(f"⚠️ Error al cargar el modelo de fraude desde {self.model_path}: {e}")
            else:
                print(f"⚠️ Advertencia: No se encontró el modelo en {self.model_path}")

        self._cargar_umbrales()

    def _cargar_umbrales(self) -> None:
        """
        Lee los umbrales del informe de entrenamiento.

        Si el archivo no está —por ejemplo con un modelo entrenado antes de que
        esto existiera— se siguen usando los valores históricos, para que el
        sistema nunca se quede sin criterio de decisión.
        """
        if not os.path.exists(self.meta_path):
            return

        try:
            with open(self.meta_path, encoding="utf-8") as archivo:
                self.metadatos = json.load(archivo)
            self.umbral_aprobacion = float(
                self.metadatos.get("umbral_aprobacion", UMBRAL_APROBACION_POR_DEFECTO)
            )
            self.umbral_bloqueo = float(
                self.metadatos.get("umbral_bloqueo", UMBRAL_BLOQUEO_POR_DEFECTO)
            )
            print(
                f"📐 Umbrales del modelo: aprobar < {self.umbral_aprobacion}, "
                f"bloquear ≥ {self.umbral_bloqueo}"
            )
        except Exception as e:  # noqa: BLE001 - se sigue con los valores por defecto
            print(f"⚠️ No se pudieron leer los umbrales ({e}); se usan los históricos.")

    def valor_base(self) -> Optional[float]:
        """
        El punto de partida del modelo, en escala logit, antes de mirar el
        pedido.

        Es la última columna que devuelve `pred_contrib`, y vale lo mismo para
        cualquier entrada: es una constante del modelo, no algo del pedido. Con
        ella la decisión se puede reconstruir a mano —puntaje = sigmoide(base +
        suma de los aportes)—, que es lo que convierte "el modelo dijo 88 %" en
        una cuenta que alguien puede rehacer.

        OJO: no es la tasa de fraude de la tienda. El entrenamiento equilibra
        las clases (`class_weight="balanced"`), así que este punto de partida
        queda mucho más alto que la proporción real de compras fraudulentas.
        """
        if self.model is None:
            return None
        if self._valor_base is None:
            try:
                fila = pd.DataFrame([{variable: 0.0 for variable in FEATURES}])
                contribuciones = self.model.booster_.predict(fila, pred_contrib=True)
                self._valor_base = round(float(contribuciones[0][-1]), 4)
            except Exception as e:  # noqa: BLE001 - es información, no una decisión
                print(f"⚠️ No se pudo leer el valor base del modelo: {e}")
                return None
        return self._valor_base

    def cantidad_de_arboles(self) -> Optional[int]:
        """Cuántos árboles suma el modelo para llegar a su puntaje."""
        if self.model is None:
            return None
        try:
            return int(self.model.booster_.num_trees())
        except Exception:  # noqa: BLE001
            return None

    def is_loaded(self) -> bool:
        """Devuelve True si el modelo está cargado exitosamente."""
        return self.model is not None

    def recargar(self) -> None:
        """Vuelve a leer el modelo del disco, tras un reentrenamiento."""
        self.model = None
        self.metadatos = {}
        self._valor_base = None
        self.load_model()

    # ── Explicación ──────────────────────────────────────────────────────────
    def _aportes(self, datos: pd.DataFrame) -> Optional[dict]:
        """
        Cuánto empujó cada variable el puntaje de este pedido.

        Son valores SHAP en escala logit: positivo empuja hacia fraude,
        negativo hacia compra legítima. LightGBM los calcula él mismo con
        `pred_contrib`, así que no hace falta instalar nada más.
        """
        try:
            contribuciones = self.model.booster_.predict(datos, pred_contrib=True)[0]
        except Exception as e:  # noqa: BLE001 - la explicación no puede tumbar una compra
            print(f"⚠️ No se pudieron calcular los aportes por variable: {e}")
            return None

        # La última columna es el valor base (la predicción media), no una variable.
        return {
            variable: round(float(aporte), 4)
            for variable, aporte in zip(FEATURES, contribuciones[:-1])
        }

    def _explicar(self, puntaje: float, decision: str, valores: dict, aportes: Optional[dict]) -> str:
        """Arma la frase que lee el administrador en el panel."""
        encabezado = {
            "APPROVED": f"Riesgo bajo ({puntaje:.0%})",
            "REVIEW": f"Riesgo medio ({puntaje:.0%}); requiere revisión manual",
            "BLOCKED": f"Riesgo alto ({puntaje:.0%}); pedido rechazado",
        }[decision]

        if not aportes:
            return f"{encabezado}."

        # Se nombran los factores que más pesaron en el sentido de la decisión:
        # los que empujan hacia el fraude cuando se bloquea o se revisa, y los
        # que lo alejan cuando se aprueba.
        hacia_fraude = decision in ("BLOCKED", "REVIEW")
        relevantes = [
            (variable, aporte)
            for variable, aporte in aportes.items()
            if (aporte > 0) == hacia_fraude and aporte != 0
        ]
        relevantes.sort(key=lambda par: -abs(par[1]))
        relevantes = relevantes[:FACTORES_EN_LA_EXPLICACION]

        if not relevantes:
            return f"{encabezado}."

        detalle = ", ".join(_frase(variable, valores[variable]) for variable, _ in relevantes)
        conector = "pesó en contra" if hacia_fraude else "pesó a favor"
        return f"{encabezado}. Lo que {conector}: {detalle}."

    # ── Evaluación ───────────────────────────────────────────────────────────
    def evaluar(
        self,
        total_amount: float,
        high_risk_items_count: int,
        checkout_duration_seconds: float,
        is_new_shipping_address: int,
    ) -> Evaluacion:
        """Evalúa un pedido y devuelve puntaje, decisión y explicación."""
        if self.model is None:
            self.load_model()

        valores = {
            "total_amount": float(total_amount),
            "high_risk_items_count": int(high_risk_items_count),
            "checkout_duration_seconds": float(checkout_duration_seconds),
            "is_new_shipping_address": int(is_new_shipping_address),
        }

        if self.model is None:
            # Sin modelo se aprueba y se dice claramente por qué: es preferible
            # a bloquear compras legítimas por una falla de infraestructura.
            return Evaluacion(
                puntaje=0.0,
                decision="APPROVED",
                nivel_de_riesgo="LOW",
                explicacion="El modelo de fraude no está disponible; el pedido se aprobó sin evaluar.",
                milisegundos=0.0,
                aportes={},
            )

        datos = pd.DataFrame([valores])

        inicio = time.perf_counter()
        puntaje = float(self.model.predict_proba(datos)[0][1])
        aportes = self._aportes(datos)
        milisegundos = (time.perf_counter() - inicio) * 1000.0

        if puntaje < self.umbral_aprobacion:
            decision, nivel = "APPROVED", "LOW"
        elif puntaje < self.umbral_bloqueo:
            decision, nivel = "REVIEW", "MEDIUM"
        else:
            decision, nivel = "BLOCKED", "HIGH"

        return Evaluacion(
            puntaje=puntaje,
            decision=decision,
            nivel_de_riesgo=nivel,
            explicacion=self._explicar(puntaje, decision, valores, aportes),
            milisegundos=milisegundos,
            aportes=aportes or {},
        )

    # Nombre anterior, que sigue usándose desde la API. Devuelve la evaluación
    # completa; los que solo quieren el puntaje leen `.puntaje`.
    evaluate_transaction = evaluar


# Instancia global del servicio
fraud_service = FraudDetectionService()
