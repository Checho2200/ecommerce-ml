"""
Comparación de LightGBM contra alternativas más simples.

    python -m ml.baselines [--sinteticos]

Sirve para responder la pregunta que siempre aparece en una sustentación:
*¿por qué un modelo de gradient boosting y no algo más sencillo?* La respuesta
solo vale si está medida, con la misma partición y las mismas métricas para
todos los candidatos.

Los cuatro competidores:

- **Reglas heurísticas.** Lo que haría un programador sin aprendizaje
  automático: marcar el pedido si el monto es alto, el checkout fue rápido y
  la dirección es nueva. Es la línea base honesta, la que hay que superar para
  justificar todo lo demás.
- **Regresión logística.** El clasificador lineal clásico. Si empatara con
  LightGBM, la conclusión sería que el problema no necesita un modelo no
  lineal.
- **Árbol de decisión.** Un solo árbol, interpretable de un vistazo.
- **Bosque aleatorio.** El otro método de conjunto, para separar "sirve
  ensamblar árboles" de "sirve *este* algoritmo en concreto".

El resultado se guarda como JSON y como tabla Markdown, lista para pegar en el
documento.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import GridSearchCV, StratifiedKFold
from lightgbm import LGBMClassifier

from ml import evaluacion
from ml.dataset import FEATURES, RANDOM_SEED, cargar_datos
from ml.train import UMBRALES_DE_REFERENCIA, _particiones

DIRECTORIO_INFORMES = Path(__file__).resolve().parent / "informes"

# Los cortes de la heurística salen de la descripción del dominio: un pedido
# caro, resuelto en menos de un minuto y enviado a una dirección estrenada.
MONTO_SOSPECHOSO = 1500.0
CHECKOUT_RAPIDO_SEGUNDOS = 60.0
ARTICULOS_DE_RIESGO = 2


class ReglasHeuristicas:
    """
    Clasificador sin aprendizaje: cuenta cuántas señales de alarma se cumplen.

    Devuelve la proporción de reglas disparadas como "probabilidad", que es lo
    que permite dibujarle una curva ROC y compararlo de igual a igual con los
    modelos entrenados.
    """

    def fit(self, X, y=None):
        return self

    def predict_proba(self, X):
        X = pd.DataFrame(X, columns=FEATURES)
        señales = (
            (X["total_amount"] > MONTO_SOSPECHOSO).astype(int)
            + (X["checkout_duration_seconds"] < CHECKOUT_RAPIDO_SEGUNDOS).astype(int)
            + (X["is_new_shipping_address"] == 1).astype(int)
            + (X["high_risk_items_count"] >= ARTICULOS_DE_RIESGO).astype(int)
        )
        p = (señales / 4.0).to_numpy()
        return np.column_stack([1 - p, p])


def _candidatos() -> dict:
    """
    Cada candidato con la rejilla de hiperparámetros que se le va a buscar.

    Todos los que tienen algo que ajustar lo ajustan, con la misma validación
    cruzada y la misma métrica. Antes solo LightGBM salía de la comparación con
    sus hiperparámetros elegidos —los buscaba `ml/train.py` para publicarlo— y
    aquí competía con los valores de fábrica: la tabla comparaba un LightGBM
    peor que el de producción contra unos rivales también sin afinar, y ninguna
    de las dos cifras era la que se quería enseñar.

    Afinar solo al ganador sería el sesgo contrario y todavía peor. Se afina a
    todos o a ninguno; se afina a todos, que es lo que hace comparable la
    tabla.

    Las reglas heurísticas y el clasificador trivial no tienen nada que
    ajustar, y van con la rejilla vacía.
    """
    return {
        "Reglas heurísticas": (ReglasHeuristicas(), {}),
        "Clasificador trivial": (
            DummyClassifier(strategy="stratified", random_state=RANDOM_SEED),
            {},
        ),
        "Regresión logística": (
            make_pipeline(
                StandardScaler(),
                LogisticRegression(
                    class_weight="balanced", max_iter=2000, random_state=RANDOM_SEED
                ),
            ),
            {"logisticregression__C": [0.01, 0.1, 1.0, 10.0]},
        ),
        "Árbol de decisión": (
            DecisionTreeClassifier(class_weight="balanced", random_state=RANDOM_SEED),
            {"max_depth": [3, 5, 7, None], "min_samples_leaf": [1, 5, 20]},
        ),
        "Bosque aleatorio": (
            RandomForestClassifier(
                class_weight="balanced", random_state=RANDOM_SEED, n_jobs=-1
            ),
            {"n_estimators": [100, 200], "max_depth": [5, 10, None]},
        ),
        # La misma rejilla que usa `ml/train.py` para publicar el modelo, para
        # que el LightGBM de esta tabla sea el que de verdad está sirviendo.
        "LightGBM": (
            LGBMClassifier(class_weight="balanced", random_state=RANDOM_SEED, verbose=-1),
            {
                "n_estimators": [50, 100, 150],
                "learning_rate": [0.01, 0.05, 0.1],
                "max_depth": [3, 5, 7],
                "num_leaves": [15, 31],
            },
        ),
    }


def _afinado(modelo, rejilla: dict, X, y):
    """El candidato con sus mejores hiperparámetros, o tal cual si no tiene."""
    if not rejilla:
        return modelo, {}
    busqueda = GridSearchCV(
        modelo,
        rejilla,
        cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_SEED),
        scoring="average_precision",
        n_jobs=-1,
    )
    busqueda.fit(X, y)
    return busqueda.best_estimator_, busqueda.best_params_


def comparar(preferir_reales: bool = True) -> dict:
    datos = cargar_datos(preferir_reales=preferir_reales)
    print(f"Datos — origen: {datos.origen} ({datos.detalle})\n")

    X_entrena, y_entrena, X_valida, y_valida, X_prueba, y_prueba = _particiones(
        datos.X, datos.y
    )
    costos = evaluacion.Costos()

    filas = []
    for nombre, (candidato, rejilla) in _candidatos().items():
        modelo, mejores = _afinado(candidato, rejilla, X_entrena, y_entrena)
        modelo.fit(X_entrena, y_entrena)
        prob_valida = modelo.predict_proba(X_valida)[:, 1]
        prob_prueba = modelo.predict_proba(X_prueba)[:, 1]

        # Cada candidato juega con sus mejores umbrales, elegidos sobre
        # validación con el mismo criterio de costo. Compararlos todos con los
        # umbrales de LightGBM sería injusto para los demás.
        umbrales, _ = evaluacion.buscar_umbrales(
            y_valida, prob_valida, X_valida["total_amount"], costos
        )
        t_bajo, t_alto = umbrales["t_bajo"], umbrales["t_alto"]

        m = evaluacion.metricas(y_prueba, prob_prueba, umbral=t_alto)
        costo = evaluacion.costo_de_los_umbrales(
            y_prueba, prob_prueba, X_prueba["total_amount"], t_bajo, t_alto, costos
        )

        filas.append(
            {
                "modelo": nombre,
                "hiperparametros": mejores,
                "average_precision": m["average_precision"],
                "roc_auc": m["roc_auc"],
                "precision": m["precision"],
                "recall": m["recall"],
                "f1": m["f1"],
                "umbrales": [t_bajo, t_alto],
                "fraudes_aprobados": costo["fraudes_aprobados"],
                "legitimos_bloqueados": costo["legitimos_bloqueados"],
                "perdida_total": costo["costo_total"],
            }
        )
        print(
            f"{nombre:<22} AUC-PR {m['average_precision']:.4f}  "
            f"AUC-ROC {m['roc_auc']:.4f}  F1 {m['f1']:.4f}  "
            f"pérdida S/ {costo['costo_total']:,.2f}"
        )

    filas.sort(key=lambda f: -f["average_precision"])

    informe = {
        "datos": {"origen": datos.origen, "detalle": datos.detalle},
        "particion_de_prueba": int(len(X_prueba)),
        "costos_usados": evaluacion.costos_como_diccionario(costos),
        "umbrales_de_referencia": list(UMBRALES_DE_REFERENCIA),
        "resultados": filas,
    }

    DIRECTORIO_INFORMES.mkdir(parents=True, exist_ok=True)
    (DIRECTORIO_INFORMES / "comparacion_de_modelos.json").write_text(
        json.dumps(informe, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    tabla = _tabla_markdown(filas)
    (DIRECTORIO_INFORMES / "comparacion_de_modelos.md").write_text(tabla, encoding="utf-8")

    print(f"\n{tabla}")
    print(f"Guardado en {DIRECTORIO_INFORMES}")
    return informe


def _tabla_markdown(filas: list[dict]) -> str:
    """Tabla lista para pegar en el documento de la tesis."""
    cabecera = (
        "| Modelo | AUC-PR | AUC-ROC | Precisión | Exhaustividad | F1 | "
        "Fraudes aprobados | Legítimas bloqueadas | Pérdida (S/) |\n"
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |\n"
    )
    cuerpo = "".join(
        f"| {f['modelo']} | {f['average_precision']:.4f} | {f['roc_auc']:.4f} | "
        f"{f['precision']:.4f} | {f['recall']:.4f} | {f['f1']:.4f} | "
        f"{f['fraudes_aprobados']} | {f['legitimos_bloqueados']} | "
        f"{f['perdida_total']:,.2f} |\n"
        for f in filas
    )
    return cabecera + cuerpo


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Compara modelos de detección de fraude.")
    parser.add_argument(
        "--sinteticos",
        action="store_true",
        help="Usa el conjunto sintético aunque haya datos reales suficientes.",
    )
    argumentos = parser.parse_args()
    comparar(preferir_reales=not argumentos.sinteticos)
