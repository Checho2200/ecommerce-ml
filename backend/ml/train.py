"""
Entrenamiento del modelo de detección de fraude (LightGBM).

Estrategia de datos, en orden de preferencia:

1. **Transacciones reales de la tienda.** En cuanto existan al menos
   MIN_SAMPLES_FOR_TRAINING pedidos con su evaluación de fraude y su etiqueta
   real (`is_actual_fraud`, que el administrador marca cuando ocurre un
   contracargo), el modelo se entrena con ellos.

2. **Conjunto sintético del dominio.** Mientras la tienda no acumule ese
   historial, se genera un conjunto de datos etiquetado a partir de
   distribuciones que describen cómo se comporta un pedido legítimo frente a
   uno fraudulento en una tienda de componentes de cómputo.

   Nota metodológica: las clases se muestrean primero y las variables se
   generan condicionadas a la clase, con solapamiento deliberado entre ambas.
   Es decir, el modelo NO aprende una regla determinista: hay pedidos
   legítimos caros, rápidos y a direcciones nuevas, y pedidos fraudulentos que
   parecen normales. Eso es lo que hace que el problema sea de clasificación
   estadística y no un simple `if`.

   Un intento anterior usaba un CSV público de fraude bancario y mapeaba sus
   columnas a estas cuatro variables. No funcionó: las semánticas no
   coincidían (`checkout_duration_seconds` se derivaba de una marca de tiempo
   ajena, con lo que resultaba ruido puro) y el modelo terminaba rechazando
   compras perfectamente normales.

Uso:  python -m ml.train
"""

import json
import os
import sqlite3

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.metrics import accuracy_score, classification_report, roc_auc_score
from sklearn.model_selection import GridSearchCV, train_test_split

MIN_SAMPLES_FOR_TRAINING = 50
RANDOM_SEED = 42

FEATURES = [
    "total_amount",
    "high_risk_items_count",
    "checkout_duration_seconds",
    "is_new_shipping_address",
]


# ─────────────────────────────────────────────────────────────────────────────
# 1. Datos reales de la tienda
# ─────────────────────────────────────────────────────────────────────────────
def fetch_real_data() -> pd.DataFrame | None:
    """Devuelve las transacciones reales etiquetadas, o None si aún no bastan."""
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sanchez_ecommerce.db")
    if not os.path.exists(db_path):
        return None

    try:
        conn = sqlite3.connect(db_path)
        df_db = pd.read_sql_query(
            """
            SELECT o.total_amount, f.feature_vector, f.is_actual_fraud
            FROM orders o
            JOIN fraud_logs f ON o.id = f.order_id
            """,
            conn,
        )
        conn.close()
    except Exception as exc:
        print(f"No se pudo consultar la base de datos ({exc}).")
        return None

    if len(df_db) < MIN_SAMPLES_FOR_TRAINING:
        print(
            f"Solo hay {len(df_db)} transacciones etiquetadas; se necesitan "
            f"{MIN_SAMPLES_FOR_TRAINING} para entrenar con datos reales."
        )
        return None

    rows = []
    for _, row in df_db.iterrows():
        vec = row["feature_vector"]
        if isinstance(vec, str):
            try:
                vec = json.loads(vec)
            except json.JSONDecodeError:
                vec = {}
        vec = vec or {}
        rows.append(
            {
                "total_amount": float(row["total_amount"]),
                "high_risk_items_count": int(vec.get("high_risk_items_count", 0)),
                "checkout_duration_seconds": float(vec.get("checkout_duration_seconds", 0.0)),
                "is_new_shipping_address": int(vec.get("is_new_shipping_address", 0)),
                "is_fraud": int(row["is_actual_fraud"]),
            }
        )

    print(f"Entrenando con {len(rows)} transacciones reales de la tienda.")
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Conjunto sintético del dominio
# ─────────────────────────────────────────────────────────────────────────────
def generate_domain_data(n_samples: int = 10000, fraud_rate: float = 0.07) -> pd.DataFrame:
    """
    Genera transacciones etiquetadas para una tienda de componentes de cómputo.

    Las distribuciones por clase se solapan a propósito: un cliente honesto
    puede comprar una tarjeta de video cara, rápido y a una dirección nueva.
    Ese solapamiento es lo que obliga al modelo a ponderar señales en vez de
    aplicar un umbral por variable.
    """
    rng = np.random.default_rng(RANDOM_SEED)

    n_fraud = int(n_samples * fraud_rate)
    n_legit = n_samples - n_fraud

    def draw(n, amount_mu, amount_sigma, risk_lambda, dur_mu, dur_sigma, p_new_addr):
        return pd.DataFrame(
            {
                # Montos con cola larga: la mayoría de pedidos son modestos y
                # unos pocos son de equipos completos.
                "total_amount": np.clip(rng.lognormal(amount_mu, amount_sigma, n), 40, 30000),
                "high_risk_items_count": np.clip(rng.poisson(risk_lambda, n), 0, 12),
                # La duración del checkout también es asimétrica: quien duda
                # tarda minutos; quien tiene los datos cargados, segundos.
                "checkout_duration_seconds": np.clip(rng.lognormal(dur_mu, dur_sigma, n), 4, 3600),
                "is_new_shipping_address": rng.binomial(1, p_new_addr, n),
            }
        )

    # Pedido legítimo típico: ticket moderado, pocos componentes de reventa
    # fácil, el cliente se toma minutos en decidir y suele enviar a una
    # dirección que ya usó antes.
    legit = draw(
        n_legit,
        amount_mu=np.log(450), amount_sigma=1.00,
        risk_lambda=0.50,
        dur_mu=np.log(200), dur_sigma=0.85,
        p_new_addr=0.20,
    )
    legit["is_fraud"] = 0

    # Pedido fraudulento típico: ticket alto concentrado en componentes de
    # reventa fácil, checkout resuelto en menos de un minuto porque los datos
    # de pago ya venían cargados, y envío a una dirección nueva.
    fraud = draw(
        n_fraud,
        amount_mu=np.log(2200), amount_sigma=0.90,
        risk_lambda=2.00,
        dur_mu=np.log(50), dur_sigma=0.85,
        p_new_addr=0.72,
    )
    fraud["is_fraud"] = 1

    df = pd.concat([legit, fraud], ignore_index=True)

    # Ruido de etiqueta: en la práctica no todo fraude se detecta ni toda
    # denuncia de contracargo es real. Sin este ruido las clases quedan casi
    # perfectamente separables, el modelo responde siempre 0 o 1, y la banda
    # intermedia de revisión manual (0.30 – 0.70) nunca se activa.
    flip = rng.random(len(df)) < 0.015
    df.loc[flip, "is_fraud"] = 1 - df.loc[flip, "is_fraud"]

    df = df.sample(frac=1, random_state=RANDOM_SEED).reset_index(drop=True)

    print(
        f"Conjunto sintético del dominio: {len(df)} transacciones "
        f"({df['is_fraud'].sum()} fraudulentas, {df['is_fraud'].mean() * 100:.1f}%)."
    )
    return df


def load_training_data() -> pd.DataFrame:
    return fetch_real_data() if fetch_real_data() is not None else generate_domain_data()


# ─────────────────────────────────────────────────────────────────────────────
# 3. Entrenamiento
# ─────────────────────────────────────────────────────────────────────────────
def train_and_save_model() -> None:
    df = load_training_data()

    X = df[FEATURES]
    y = df["is_fraud"]

    print("\nDistribución de clases (1 = fraude):")
    print((y.value_counts(normalize=True) * 100).round(2).to_string())

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_SEED, stratify=y
    )

    print("\nBuscando hiperparámetros con GridSearchCV...")
    # `class_weight='balanced'` compensa que el fraude sea minoritario. Además
    # mantiene las probabilidades repartidas en todo el rango [0, 1], que es lo
    # que hace que los umbrales de 0.30 y 0.70 del servicio sean utilizables.
    base_model = LGBMClassifier(class_weight="balanced", random_state=RANDOM_SEED, verbose=-1)
    param_grid = {
        "n_estimators": [50, 100, 150],
        "learning_rate": [0.01, 0.05, 0.1],
        "max_depth": [3, 5, 7],
    }
    grid = GridSearchCV(base_model, param_grid, cv=3, scoring="roc_auc", n_jobs=-1)
    grid.fit(X_train, y_train)

    model = grid.best_estimator_
    print(f"Mejores hiperparámetros: {grid.best_params_}")

    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]

    print(f"\nAccuracy: {accuracy_score(y_test, y_pred):.4f}")
    print(f"ROC AUC:  {roc_auc_score(y_test, y_prob):.4f}")
    print("\n" + classification_report(y_test, y_pred, target_names=["Legítima", "Fraude"]))

    print("Importancia de cada variable:")
    for feat, imp in sorted(zip(FEATURES, model.feature_importances_), key=lambda x: -x[1]):
        print(f"  {imp:>6}  {feat}")

    services_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app", "services")
    os.makedirs(services_dir, exist_ok=True)
    model_path = os.path.join(services_dir, "fraud_model.joblib")

    import joblib

    joblib.dump(model, model_path)
    print(f"\nModelo guardado en: {model_path}")


if __name__ == "__main__":
    train_and_save_model()
