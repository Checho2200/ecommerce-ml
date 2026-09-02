"""
Entrenamiento del modelo de detección de fraude (LightGBM).

    python -m ml.train              # entrena y, si mejora, reemplaza el modelo
    python -m ml.train --sinteticos # fuerza el conjunto sintético
    python -m ml.train --forzar     # reemplaza el modelo aunque no mejore

Qué hace, en orden:

1. Carga los datos (los de la tienda si ya alcanzan; si no, los sintéticos).
2. Parte en tres: entrenamiento, validación y prueba. La partición de prueba
   no se toca hasta el final, y los umbrales se eligen sobre la de validación,
   nunca sobre la de prueba: elegirlos ahí inflaría los resultados.
3. Mide la estabilidad con validación cruzada estratificada repetida, y
   reporta media y desviación. Responde a la pregunta "¿y si tuviste suerte
   con la partición?".
4. Busca hiperparámetros optimizando AUC-PR, no acierto global.
5. Elige los dos umbrales de decisión minimizando el costo en soles.
6. Evalúa en la partición de prueba y guarda el informe y las figuras.
7. Solo reemplaza el modelo en producción si el candidato no es peor que el
   que ya está. Sin esta guarda, un reentrenamiento con pocos casos reales
   podría degradar el sistema en silencio.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.metrics import average_precision_score
from sklearn.model_selection import (
    GridSearchCV,
    RepeatedStratifiedKFold,
    StratifiedKFold,
    cross_validate,
    train_test_split,
)

from ml import evaluacion
from ml.dataset import ETIQUETA, FEATURES, RANDOM_SEED, cargar_datos

RAIZ = Path(__file__).resolve().parent.parent
RUTA_MODELO = RAIZ / "app" / "services" / "fraud_model.joblib"
RUTA_UMBRALES = RAIZ / "app" / "services" / "fraud_model.meta.json"
DIRECTORIO_INFORMES = RAIZ / "ml" / "informes"

# Los umbrales con los que nació el sistema, escritos a mano. Se conservan como
# referencia para poder decir en el informe cuánto se gana al elegirlos por
# costo en lugar de a ojo.
UMBRALES_DE_REFERENCIA = (0.30, 0.70)

# Por encima de este AUC-PR el resultado se considera sospechoso: en detección
# de fraude con datos reales no se acierta el 100 %. Y por debajo de este número
# de casos de prueba, la medición no dice gran cosa.
UMBRAL_DE_SOSPECHA = 0.99
MINIMO_EN_PRUEBA = 40


def _particiones(X, y, semilla=RANDOM_SEED):
    """
    Divide en entrenamiento (60 %), validación (20 %) y prueba (20 %).

    Estratificado en las tres para que la proporción de fraude se mantenga:
    con una clase minoritaria, una partición al azar puede quedarse sin
    positivos y arruinar la medición.
    """
    X_entrena, X_resto, y_entrena, y_resto = train_test_split(
        X, y, test_size=0.4, random_state=semilla, stratify=y
    )
    X_valida, X_prueba, y_valida, y_prueba = train_test_split(
        X_resto, y_resto, test_size=0.5, random_state=semilla, stratify=y_resto
    )
    return X_entrena, y_entrena, X_valida, y_valida, X_prueba, y_prueba


def _validacion_cruzada(modelo, X, y) -> dict:
    """Cinco particiones, dos repeticiones. Devuelve media y desviación."""
    cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=2, random_state=RANDOM_SEED)
    puntajes = cross_validate(
        modelo, X, y, cv=cv, scoring=["average_precision", "roc_auc", "f1"], n_jobs=-1
    )
    return {
        nombre: {
            "media": round(float(np.mean(puntajes[f"test_{nombre}"])), 4),
            "desviacion": round(float(np.std(puntajes[f"test_{nombre}"])), 4),
        }
        for nombre in ("average_precision", "roc_auc", "f1")
    }


def _buscar_hiperparametros(X, y) -> tuple[LGBMClassifier, dict]:
    """
    Rejilla de hiperparámetros optimizando AUC-PR.

    `class_weight="balanced"` compensa que el fraude sea minoritario y mantiene
    las probabilidades repartidas por todo el rango [0, 1], que es lo que hace
    que los umbrales intermedios tengan sentido.
    """
    base = LGBMClassifier(class_weight="balanced", random_state=RANDOM_SEED, verbose=-1)
    rejilla = {
        "n_estimators": [50, 100, 150],
        "learning_rate": [0.01, 0.05, 0.1],
        "max_depth": [3, 5, 7],
        "num_leaves": [15, 31],
    }
    busqueda = GridSearchCV(
        base,
        rejilla,
        cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_SEED),
        scoring="average_precision",
        n_jobs=-1,
    )
    busqueda.fit(X, y)
    return busqueda.best_estimator_, busqueda.best_params_


def decidir_reemplazo(
    ap_candidato: float,
    ap_anterior: float | None,
    casos_de_prueba: int,
    forzar: bool = False,
) -> tuple[bool, str, bool]:
    """
    Decide si el modelo recién entrenado debe sustituir al que está sirviendo.

    Devuelve (reemplaza, motivo, sospechoso). Dos reglas:

    1. **No empeorar.** Solo se publica un candidato que iguale o mejore al
       modelo actual sobre la misma partición de prueba. Sin esto, un
       reentrenamiento con pocos casos reales degradaría el sistema en silencio.

    2. **Desconfiar de lo perfecto.** Un AUC-PR cercano a 1, o una partición de
       prueba diminuta, no son buenas noticias: con datos de verdad un
       clasificador de fraude no acierta el 100 %. Cuando ocurre, casi siempre
       es fuga de datos, clases sembradas separables o tan pocos casos que la
       medición no significa nada. Publicar ese modelo sería cambiar uno medido
       por uno que nadie comprobó, así que se rechaza salvo que se pida
       explícitamente con --forzar.
    """
    sospechoso = ap_candidato >= UMBRAL_DE_SOSPECHA or casos_de_prueba < MINIMO_EN_PRUEBA

    if sospechoso:
        motivo = (
            f"resultado sospechoso: AUC-PR de {ap_candidato:.4f} sobre "
            f"{casos_de_prueba} casos de prueba. Apunta a fuga de datos o a un "
            "conjunto demasiado pequeño o separable, no a un modelo mejor"
        )
        if forzar:
            return True, f"{motivo} — se publica igual porque se pidió --forzar", True
        return False, motivo, True

    if ap_anterior is None:
        return True, "no había un modelo previo con el que comparar", False

    if ap_candidato >= ap_anterior:
        return (
            True,
            f"AUC-PR {ap_candidato:.4f} contra {ap_anterior:.4f} del modelo actual",
            False,
        )

    motivo = (
        f"el candidato es peor: AUC-PR {ap_candidato:.4f} contra "
        f"{ap_anterior:.4f} del modelo actual"
    )
    if forzar:
        return True, f"{motivo} — se publica igual porque se pidió --forzar", False
    return False, motivo, False


def _modelo_en_produccion():
    """Devuelve el modelo que está sirviendo ahora, o None si no hay ninguno."""
    if not RUTA_MODELO.exists():
        return None
    try:
        return joblib.load(RUTA_MODELO)
    except Exception as exc:  # noqa: BLE001 - un modelo ilegible equivale a no tenerlo
        print(f"No se pudo leer el modelo actual ({exc}); se tratará como inexistente.")
        return None


def entrenar(preferir_reales: bool = True, forzar: bool = False) -> dict:
    datos = cargar_datos(preferir_reales=preferir_reales)
    print(f"\nDatos de entrenamiento — origen: {datos.origen} ({datos.detalle})")

    X, y = datos.X, datos.y
    print("\nDistribución de clases (1 = fraude):")
    print((y.value_counts(normalize=True) * 100).round(2).to_string())

    X_entrena, y_entrena, X_valida, y_valida, X_prueba, y_prueba = _particiones(X, y)
    print(
        f"\nParticiones — entrenamiento: {len(X_entrena)}, "
        f"validación: {len(X_valida)}, prueba: {len(X_prueba)}"
    )

    print("\nBuscando hiperparámetros (métrica: AUC-PR)...")
    modelo, mejores_parametros = _buscar_hiperparametros(X_entrena, y_entrena)
    print(f"Mejores hiperparámetros: {mejores_parametros}")

    print("\nValidación cruzada estratificada (5 particiones × 2 repeticiones)...")
    estabilidad = _validacion_cruzada(modelo, X_entrena, y_entrena)
    for nombre, valores in estabilidad.items():
        print(f"  {nombre:>18}: {valores['media']:.4f} ± {valores['desviacion']:.4f}")

    # --- Umbrales, elegidos sobre validación ---
    prob_valida = modelo.predict_proba(X_valida)[:, 1]
    costos = evaluacion.Costos()
    mejores_umbrales, rejilla = evaluacion.buscar_umbrales(
        y_valida, prob_valida, X_valida["total_amount"], costos
    )
    referencia = evaluacion.costo_de_los_umbrales(
        y_valida, prob_valida, X_valida["total_amount"],
        *UMBRALES_DE_REFERENCIA, costos,
    )
    comparacion = evaluacion.comparar_con_referencia(
        mejores_umbrales, referencia, len(y_valida), costos
    )

    t_bajo, t_alto = mejores_umbrales["t_bajo"], mejores_umbrales["t_alto"]
    print(f"\nUmbrales elegidos por costo: aprobar < {t_bajo}, bloquear ≥ {t_alto}")
    print(
        f"  Pérdida con estos umbrales: S/ {comparacion['costo_con_umbrales_elegidos']:,.2f}"
    )
    print(
        f"  Pérdida con los de referencia {UMBRALES_DE_REFERENCIA}: "
        f"S/ {comparacion['costo_con_umbrales_de_referencia']:,.2f} "
        f"({comparacion['ahorro_porcentual']:+.1f} %)"
    )

    print(
        f"  Pedidos que irían a revisión manual: "
        f"{mejores_umbrales['proporcion_revisada'] * 100:.1f} % "
        f"(tope operativo: {costos.capacidad_de_revision * 100:.0f} %)"
    )
    if not comparacion["la_referencia_cabe_en_la_capacidad"]:
        print(
            "  Nota: los umbrales de referencia mandarían a revisión el "
            f"{comparacion['proporcion_revisada_con_la_referencia'] * 100:.1f} % "
            "de los pedidos, por encima de lo que el negocio puede revisar."
        )

    # --- Modelo definitivo, reajustado con entrenamiento + validación ---
    # Ya se usaron los hiperparámetros y los umbrales que salieron de esas dos
    # particiones, así que ahora conviene reentrenar con todo lo que no es
    # prueba: más datos, mismo procedimiento. La partición de prueba sigue sin
    # haberse tocado, que es lo que hace válida la evaluación de abajo.
    modelo = LGBMClassifier(
        **mejores_parametros,
        class_weight="balanced",
        random_state=RANDOM_SEED,
        verbose=-1,
    ).fit(pd.concat([X_entrena, X_valida]), pd.concat([y_entrena, y_valida]))
    print(
        f"\nModelo definitivo reajustado con "
        f"{len(X_entrena) + len(X_valida)} transacciones."
    )

    # --- Evaluación final, sobre prueba ---
    prob_prueba = modelo.predict_proba(X_prueba)[:, 1]
    metricas_prueba = evaluacion.metricas(y_prueba, prob_prueba, umbral=t_alto)
    metricas_medio = evaluacion.metricas(y_prueba, prob_prueba, umbral=0.5)
    costo_prueba = evaluacion.costo_de_los_umbrales(
        y_prueba, prob_prueba, X_prueba["total_amount"], t_bajo, t_alto, costos
    )

    print("\nResultados en la partición de prueba:")
    print(f"  AUC-PR (average precision): {metricas_prueba['average_precision']:.4f}")
    print(f"  AUC-ROC:                    {metricas_prueba['roc_auc']:.4f}")
    print(f"  Precisión (umbral {t_alto}):    {metricas_prueba['precision']:.4f}")
    print(f"  Exhaustividad:              {metricas_prueba['recall']:.4f}")
    print(f"  F1:                         {metricas_prueba['f1']:.4f}")
    print(f"  Fraudes que se escaparían:  {costo_prueba['fraudes_aprobados']}")
    print(f"  Compras legítimas frenadas: {costo_prueba['legitimos_bloqueados']}")

    importancias = sorted(
        zip(FEATURES, (int(v) for v in modelo.feature_importances_)),
        key=lambda par: -par[1],
    )
    print("\nImportancia de cada variable:")
    for variable, peso in importancias:
        print(f"  {peso:>6}  {variable}")

    # --- ¿Se reemplaza el modelo que está en producción? ---
    anterior = _modelo_en_produccion()
    ap_candidato = float(average_precision_score(y_prueba, prob_prueba))
    ap_anterior = None

    if anterior is not None:
        try:
            ap_anterior = float(
                average_precision_score(y_prueba, anterior.predict_proba(X_prueba)[:, 1])
            )
        except Exception as exc:  # noqa: BLE001 - un modelo incompatible se reemplaza
            print(f"El modelo actual no se pudo evaluar ({exc}); se reemplazará.")

    reemplaza, motivo, sospechoso = decidir_reemplazo(
        ap_candidato, ap_anterior, len(X_prueba), forzar
    )
    if sospechoso:
        print(f"\n⚠️  {motivo}")

    informe = {
        "generado_en": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "datos": {
            "origen": datos.origen,
            "detalle": datos.detalle,
            "total": int(len(X)),
            "tasa_de_fraude": round(float(y.mean()), 4),
            "particiones": {
                "entrenamiento": int(len(X_entrena)),
                "validacion": int(len(X_valida)),
                "prueba": int(len(X_prueba)),
                "ajuste_final": int(len(X_entrena) + len(X_valida)),
            },
        },
        "modelo": {
            "algoritmo": "LightGBM (LGBMClassifier)",
            "hiperparametros": mejores_parametros,
            "variables": FEATURES,
            "importancias": dict(importancias),
        },
        "validacion_cruzada": estabilidad,
        "umbrales": {
            "aprobar_por_debajo_de": t_bajo,
            "bloquear_por_encima_de": t_alto,
            "de_referencia": list(UMBRALES_DE_REFERENCIA),
            "costos_usados": evaluacion.costos_como_diccionario(costos),
            "en_validacion": mejores_umbrales,
            "comparacion_con_referencia": comparacion,
        },
        "prueba": {
            "al_umbral_elegido": metricas_prueba,
            "al_umbral_neutro_0_5": metricas_medio,
            "costo": costo_prueba,
        },
        "reemplazo_del_modelo": {
            "reemplaza": reemplaza,
            "resultado_sospechoso": bool(sospechoso),
            "motivo": motivo,
            "average_precision_candidato": round(ap_candidato, 4),
            "average_precision_anterior": (
                round(ap_anterior, 4) if ap_anterior is not None else None
            ),
        },
    }

    # --- Informe y figuras ---
    DIRECTORIO_INFORMES.mkdir(parents=True, exist_ok=True)
    figuras = evaluacion.guardar_figuras(
        y_prueba, prob_prueba, rejilla, DIRECTORIO_INFORMES, elegido=mejores_umbrales
    )
    matriz = evaluacion.guardar_matriz_de_confusion(
        metricas_prueba, DIRECTORIO_INFORMES, "matriz_de_confusion.png"
    )
    if matriz:
        figuras.append(matriz)
    informe["figuras"] = figuras

    (DIRECTORIO_INFORMES / "informe_entrenamiento.json").write_text(
        json.dumps(informe, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\nInforme guardado en: {DIRECTORIO_INFORMES / 'informe_entrenamiento.json'}")
    if figuras:
        print(f"Figuras guardadas en {DIRECTORIO_INFORMES}: {', '.join(figuras)}")

    # --- Publicación del modelo ---
    if reemplaza:
        RUTA_MODELO.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(modelo, RUTA_MODELO)
        RUTA_UMBRALES.write_text(
            json.dumps(
                {
                    "entrenado_en": informe["generado_en"],
                    "origen_de_los_datos": datos.origen,
                    "variables": FEATURES,
                    "umbral_aprobacion": t_bajo,
                    "umbral_bloqueo": t_alto,
                    "average_precision": round(ap_candidato, 4),
                    "roc_auc": metricas_prueba["roc_auc"],
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        print(f"Modelo guardado en: {RUTA_MODELO} ({motivo}).")
    else:
        print(
            f"El modelo NO se reemplaza: {motivo}. "
            "El informe queda guardado igual para poder revisarlo."
        )

    return informe


def main() -> int:
    parser = argparse.ArgumentParser(description="Entrena el modelo de fraude.")
    parser.add_argument(
        "--sinteticos",
        action="store_true",
        help="Usa el conjunto sintético aunque haya datos reales suficientes.",
    )
    parser.add_argument(
        "--forzar",
        action="store_true",
        help="Reemplaza el modelo en producción aunque el candidato sea peor.",
    )
    args = parser.parse_args()

    informe = entrenar(preferir_reales=not args.sinteticos, forzar=args.forzar)
    return 0 if informe["reemplazo_del_modelo"]["reemplaza"] else 0


if __name__ == "__main__":
    sys.exit(main())
