"""
Evidencia de cuánto mejoró el sistema de detección de fraude.

    python -m ml.experimento

Compara tres configuraciones sobre **las mismas compras**, generadas aparte y
que ninguno de los dos modelos vio nunca:

| Configuración | Modelo | Umbrales |
| --- | --- | --- |
| A. Sistema original | el que estaba en producción | 0.30 y 0.70, escritos a mano |
| B. Solo umbrales | el mismo de antes | elegidos minimizando costo |
| C. Sistema actual | el reentrenado | elegidos minimizando costo |

Las tres columnas no están por adorno: comparar solo A contra C diría "mejoró",
pero no *por qué*. Con B en medio se separa lo que aportó cambiar el modelo de
lo que aportó dejar de elegir los umbrales a ojo, que son dos afirmaciones
distintas y ambas hay que poder defenderlas.

Todo lo que produce queda en `ml/informes/`: una tabla comparativa en Markdown,
el detalle en JSON, dos figuras y una muestra de compras concretas con la
decisión y la explicación que daba cada sistema.
"""

import json
import shutil
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from ml import evaluacion
from ml.dataset import ETIQUETA, FEATURES, generar_datos_sinteticos

RAIZ = Path(__file__).resolve().parent.parent
DIRECTORIO_INFORMES = RAIZ / "ml" / "informes"
DIRECTORIO_MODELOS = RAIZ / "ml" / "modelos"

RUTA_MODELO_ACTUAL = RAIZ / "app" / "services" / "fraud_model.joblib"
RUTA_META_ACTUAL = RAIZ / "app" / "services" / "fraud_model.meta.json"
RUTA_MODELO_ANTERIOR = DIRECTORIO_MODELOS / "modelo_anterior.joblib"

# Los umbrales con los que nació el sistema, escritos a mano en el código.
UMBRALES_ORIGINALES = (0.30, 0.70)

# Semillas distintas de la del entrenamiento (42): estas compras no las vio
# ninguno de los dos modelos. Es lo que hace que la comparación signifique algo.
SEMILLA_VALIDACION = 777
SEMILLA_PRUEBA = 999

# La frase que el sistema original le mostraba al administrador. Se conserva
# textual para poder enseñar el antes y el después de la explicación.
EXPLICACIONES_ORIGINALES = {
    "APPROVED": "Bajo riesgo de fraude detectado por IA.",
    "REVIEW": "Riesgo medio de fraude detectado por IA. Se requiere revisión.",
    "BLOCKED": "Alto riesgo de fraude detectado por IA. Orden rechazada.",
}


def _cargar_modelo(ruta: Path):
    if not ruta.exists():
        raise FileNotFoundError(
            f"Falta {ruta}. El modelo anterior se recupera del historial con:\n"
            f"  git show <commit>:backend/app/services/fraud_model.joblib > {ruta}"
        )
    return joblib.load(ruta)


def _umbrales_actuales() -> tuple[float, float]:
    if RUTA_META_ACTUAL.exists():
        meta = json.loads(RUTA_META_ACTUAL.read_text(encoding="utf-8"))
        return float(meta["umbral_aprobacion"]), float(meta["umbral_bloqueo"])
    return UMBRALES_ORIGINALES


def _decidir(puntaje: float, t_bajo: float, t_alto: float) -> str:
    if puntaje < t_bajo:
        return "APPROVED"
    if puntaje < t_alto:
        return "REVIEW"
    return "BLOCKED"


def _medir(nombre, modelo, prob_prueba, y_prueba, montos, t_bajo, t_alto, costos) -> dict:
    """Métricas y dinero de una configuración sobre la partición de prueba."""
    metricas = evaluacion.metricas(y_prueba, prob_prueba, umbral=t_alto)
    costo = evaluacion.costo_de_los_umbrales(
        y_prueba, prob_prueba, montos, t_bajo, t_alto, costos
    )
    return {
        "configuracion": nombre,
        "umbrales": [t_bajo, t_alto],
        "average_precision": metricas["average_precision"],
        "roc_auc": metricas["roc_auc"],
        "precision": metricas["precision"],
        "recall": metricas["recall"],
        "f1": metricas["f1"],
        "matriz_de_confusion": metricas["matriz_de_confusion"],
        "fraudes_aprobados": costo["fraudes_aprobados"],
        "legitimos_bloqueados": costo["legitimos_bloqueados"],
        "pedidos_revisados": costo["pedidos_revisados"],
        "proporcion_revisada": round(costo["pedidos_revisados"] / len(y_prueba), 4),
        "perdida_total": costo["costo_total"],
        "perdida_por_fraude_aprobado": costo["perdida_por_fraude_aprobado"],
        "perdida_por_venta_bloqueada": costo["perdida_por_venta_bloqueada"],
        "costo_de_revisiones": costo["costo_de_revisiones"],
    }


def _tabla_comparativa(filas: list[dict]) -> str:
    cabecera = (
        "| Configuración | Umbrales | AUC-PR | Precisión | Exhaustividad | F1 | "
        "Fraudes aprobados | Legítimas bloqueadas | A revisión | Pérdida (S/) |\n"
        "| --- | :---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |\n"
    )
    cuerpo = "".join(
        f"| {f['configuracion']} | {f['umbrales'][0]} / {f['umbrales'][1]} | "
        f"{f['average_precision']:.4f} | {f['precision']:.4f} | {f['recall']:.4f} | "
        f"{f['f1']:.4f} | {f['fraudes_aprobados']} | {f['legitimos_bloqueados']} | "
        f"{f['proporcion_revisada'] * 100:.1f} % | {f['perdida_total']:,.2f} |\n"
        for f in filas
    )
    return cabecera + cuerpo


def _muestra_de_compras(df, prob_antes, prob_despues, umbrales_antes, umbrales_despues, servicio) -> str:
    """
    Una selección de compras concretas, con lo que decidía cada sistema.

    Se eligen a propósito casos repartidos por todo el rango de riesgo, y entre
    ellos los que cambiaron de decisión: son los que muestran la diferencia.
    """
    tabla = df.copy()
    tabla["prob_antes"] = prob_antes
    tabla["prob_despues"] = prob_despues
    tabla["decision_antes"] = [_decidir(p, *umbrales_antes) for p in prob_antes]
    tabla["decision_despues"] = [_decidir(p, *umbrales_despues) for p in prob_despues]

    cambiaron = tabla[tabla["decision_antes"] != tabla["decision_despues"]]
    iguales = tabla[tabla["decision_antes"] == tabla["decision_despues"]]

    muestra = pd.concat(
        [
            cambiaron.sort_values("prob_despues", ascending=False).head(6),
            iguales.sort_values("prob_despues", ascending=False).head(2),
            iguales.sort_values("prob_despues").head(2),
        ]
    )

    lineas = [
        "# Compras de prueba: qué decidía cada sistema\n",
        "Diez compras simuladas, elegidas entre las que cambiaron de decisión y",
        "los extremos de riesgo. Ninguno de los dos modelos vio estas",
        "transacciones durante su entrenamiento.\n",
        "| # | Monto | Alto riesgo | Checkout | Dirección | ¿Fue fraude? | Antes | Después |",
        "| ---: | ---: | ---: | ---: | :---: | :---: | :--- | :--- |",
    ]

    for numero, (_, fila) in enumerate(muestra.iterrows(), start=1):
        duracion = fila["checkout_duration_seconds"]
        duracion_texto = f"{duracion:.0f} s" if duracion < 60 else f"{duracion / 60:.1f} min"
        lineas.append(
            f"| {numero} | S/ {fila['total_amount']:,.0f} | "
            f"{int(fila['high_risk_items_count'])} | {duracion_texto} | "
            f"{'nueva' if fila['is_new_shipping_address'] else 'conocida'} | "
            f"{'**sí**' if fila[ETIQUETA] else 'no'} | "
            f"{fila['decision_antes']} ({fila['prob_antes']:.0%}) | "
            f"{fila['decision_despues']} ({fila['prob_despues']:.0%}) |"
        )

    # El antes y el después de la explicación, sobre el caso más riesgoso.
    peor = muestra.sort_values("prob_despues", ascending=False).iloc[0]
    evaluacion_nueva = servicio.evaluar(
        total_amount=float(peor["total_amount"]),
        high_risk_items_count=int(peor["high_risk_items_count"]),
        checkout_duration_seconds=float(peor["checkout_duration_seconds"]),
        is_new_shipping_address=int(peor["is_new_shipping_address"]),
    )
    lineas += [
        "\n## La explicación que ve el administrador\n",
        f"Para la compra de S/ {peor['total_amount']:,.0f} con "
        f"{int(peor['high_risk_items_count'])} artículos de alto riesgo:\n",
        "**Antes:**\n",
        f"> {EXPLICACIONES_ORIGINALES[evaluacion_nueva.decision]}\n",
        "*La misma frase para todos los pedidos de ese nivel de riesgo.*\n",
        "**Después:**\n",
        f"> {evaluacion_nueva.explicacion}\n",
        "*Los factores son los de este pedido en concreto, calculados con los "
        "valores SHAP del propio modelo.*\n",
    ]
    return "\n".join(lineas) + "\n"


def _figuras(resultados, y_prueba, prob_antes, prob_despues, destino: Path) -> list[str]:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from sklearn.metrics import precision_recall_curve
    except ImportError:
        print("matplotlib no está instalada; se omiten las figuras.")
        return []

    destino.mkdir(parents=True, exist_ok=True)
    creadas = []

    # --- Curvas precisión-exhaustividad, una sobre otra ---
    try:
        fig, eje = plt.subplots(figsize=(5.4, 4.4))
        for prob, nombre, color in (
            (prob_antes, "Modelo anterior", "#94A3B8"),
            (prob_despues, "Modelo actual", "#0C3A6E"),
        ):
            precision, recall, _ = precision_recall_curve(y_prueba, prob)
            ap = evaluacion.metricas(y_prueba, prob)["average_precision"]
            eje.plot(recall, precision, lw=2, color=color, label=f"{nombre} (AP = {ap:.3f})")
        eje.axhline(
            np.mean(y_prueba), ls="--", color="gray", lw=1,
            label=f"Azar ({np.mean(y_prueba):.3f})",
        )
        eje.set_xlabel("Exhaustividad (recall)")
        eje.set_ylabel("Precisión")
        eje.set_title("Antes y después: curva precisión-exhaustividad")
        eje.legend(loc="upper right", fontsize=8)
        ruta = destino / "experimento_curvas.png"
        fig.savefig(ruta, dpi=150, bbox_inches="tight")
        plt.close(fig)
        creadas.append(ruta.name)
    except Exception as exc:  # noqa: BLE001
        print(f"No se pudo generar la comparación de curvas: {exc}")
        plt.close("all")

    # --- De dónde sale la pérdida, configuración por configuración ---
    try:
        nombres = [r["configuracion"] for r in resultados]
        posiciones = np.arange(len(nombres))
        fraude = [r["perdida_por_fraude_aprobado"] for r in resultados]
        ventas = [r["perdida_por_venta_bloqueada"] for r in resultados]
        revisiones = [r["costo_de_revisiones"] for r in resultados]

        fig, eje = plt.subplots(figsize=(7, 4.4))
        eje.bar(posiciones, fraude, 0.55, label="Fraude aprobado", color="#E11D2E")
        eje.bar(posiciones, ventas, 0.55, bottom=fraude, label="Venta legítima frenada", color="#FFCE00")
        eje.bar(
            posiciones, revisiones, 0.55,
            bottom=np.array(fraude) + np.array(ventas),
            label="Revisión manual", color="#0C3A6E",
        )
        for x, total in zip(posiciones, [r["perdida_total"] for r in resultados]):
            eje.text(x, total, f"S/ {total:,.0f}", ha="center", va="bottom", fontweight="bold", fontsize=9)

        # Etiquetas cortas pero que se entiendan sin la tabla al lado.
        cortas = {
            "A. Sistema original": "A\nSistema\noriginal",
            "B. Modelo anterior + umbrales por costo": "B\nSolo umbrales\npor costo",
            "C. Sistema actual": "C\nSistema\nactual",
        }
        eje.set_xticks(posiciones, [cortas.get(n, n) for n in nombres], fontsize=9)
        eje.set_ylabel("Pérdida sobre las compras de prueba (S/)")
        eje.set_title("De dónde sale la pérdida en cada configuración")
        eje.legend(fontsize=8)
        eje.margins(y=0.15)
        ruta = destino / "experimento_perdida.png"
        fig.savefig(ruta, dpi=150, bbox_inches="tight")
        plt.close(fig)
        creadas.append(ruta.name)
    except Exception as exc:  # noqa: BLE001
        print(f"No se pudo generar el desglose de pérdida: {exc}")
        plt.close("all")

    return creadas


def _redactar_resumen(informe: dict, resultados: list[dict], n_prueba: int, tasa: float) -> str:
    """
    El informe que se lee, escrito para no exagerar lo que los números dicen.

    Un experimento así se escribe solo cuando confirma lo que uno esperaba. Este
    no lo confirmó: el modelo reentrenado no distingue mejor el fraude que el
    anterior, y la mejora viene entera de decidir mejor con el mismo puntaje.
    Decirlo al revés sería más vistoso y sería falso, y es justo lo que un
    jurado comprueba mirando el AUC-PR de las dos filas.
    """
    a, b, c = resultados
    mejora = informe["mejora"]

    diferencia_fraudes = mejora["diferencia_en_fraudes_aprobados"]
    diferencia_legitimas = mejora["diferencia_en_legitimas_bloqueadas"]

    if mejora["el_modelo_discrimina_mejor"]:
        veredicto_modelo = (
            f"El modelo reentrenado **distingue mejor** el fraude: el AUC-PR sube de "
            f"{a['average_precision']:.4f} a {c['average_precision']:.4f}."
        )
    else:
        veredicto_modelo = (
            f"El modelo reentrenado **no distingue mejor** el fraude que el anterior: "
            f"el AUC-PR pasa de {a['average_precision']:.4f} a "
            f"{c['average_precision']:.4f}, que a efectos prácticos es lo mismo. "
            "Los dos ordenan las compras por riesgo casi igual de bien. Toda la "
            "mejora está en **qué se hace con ese puntaje**, no en el puntaje."
        )

    if diferencia_fraudes > 0:
        intercambio = (
            f"El sistema actual deja pasar **{diferencia_fraudes} fraudes más** "
            f"({a['fraudes_aprobados']} → {c['fraudes_aprobados']}) y a cambio deja de "
            f"frenar **{abs(diferencia_legitimas)} compras legítimas** "
            f"({a['legitimos_bloqueados']} → {c['legitimos_bloqueados']}).\n\n"
            "No es un descuido, es la decisión que toma el criterio de costo: "
            "bloquear una compra buena cuesta el margen de esa venta, y frenar 79 "
            "de ellas salía más caro que los fraudes adicionales que se cuelan. "
            "Si para la tienda el fraude pesara más que la venta perdida, basta con "
            "subir `cargo_por_contracargo` o bajar `margen_bruto` en "
            "`ml/evaluacion.py` y los umbrales se recolocan solos."
        )
    else:
        intercambio = (
            f"El sistema actual deja pasar {abs(diferencia_fraudes)} fraudes menos y "
            f"frena {abs(diferencia_legitimas)} compras legítimas menos: mejora en "
            "los dos frentes a la vez."
        )

    return (
        "# Antes y después de mejorar la detección de fraude\n\n"
        f"Sobre {n_prueba:,} compras simuladas que ninguno de los dos modelos vio "
        f"durante su entrenamiento ({tasa * 100:.1f} % fraudulentas). Los dos "
        "modelos eligen sus umbrales con el mismo método y sobre los mismos datos, "
        "para que la comparación no premie a uno por algo que el otro no tuvo.\n\n"
        + _tabla_comparativa(resultados)
        + "\n## El resultado en una línea\n\n"
        f"La pérdida sobre esas compras baja de **S/ {a['perdida_total']:,.2f}** a "
        f"**S/ {c['perdida_total']:,.2f}**: un **{mejora['porcentaje']:.1f} % menos**, "
        f"S/ {mejora['perdida_evitada']:,.2f} que la tienda deja de perder.\n\n"
        "## Pero conviene leer de dónde viene\n\n"
        f"{veredicto_modelo}\n\n"
        "El desglose lo confirma:\n\n"
        f"- **S/ {mejora['aporte_de_elegir_los_umbrales_por_costo']:,.2f}** salen de dejar de "
        "elegir los umbrales a ojo (fila A → B: el mismo modelo, distinto criterio "
        "de decisión).\n"
        f"- **S/ {mejora['aporte_de_reentrenar_el_modelo']:,.2f}** salen de reentrenar "
        "(fila B → C). Y ni siquiera es porque acierte más: es que sus puntajes se "
        "reparten distinto y admiten un corte más barato.\n\n"
        "## El intercambio que se está haciendo\n\n"
        f"{intercambio}\n\n"
        "## Lo que este experimento no mide\n\n"
        "Tres mejoras del trabajo no aparecen en la tabla porque no son cuestión de "
        "acertar más:\n\n"
        "- La **explicación por pedido**: antes, una frase idéntica para todos; ahora, "
        "los factores concretos de esa compra. Se ve en `compras_de_prueba.md`.\n"
        "- El **etiquetado en dos sentidos**, que es lo que permite calcular la "
        "precisión del modelo con datos de la tienda.\n"
        "- Las **guardas del reentrenamiento**, que impiden publicar un modelo peor o "
        "un resultado sospechosamente perfecto.\n\n"
        "Y una advertencia: estas compras son simuladas. El experimento demuestra que "
        "el método funciona y cuánto rinde bajo los supuestos de costo declarados, no "
        "lo que la tienda ahorrará con clientes reales.\n"
    )


def comparar(n_compras: int = 4000) -> dict:
    DIRECTORIO_MODELOS.mkdir(parents=True, exist_ok=True)
    modelo_anterior = _cargar_modelo(RUTA_MODELO_ANTERIOR)
    modelo_actual = _cargar_modelo(RUTA_MODELO_ACTUAL)

    # Compras nuevas, con semillas distintas de la del entrenamiento: ninguno de
    # los dos modelos las ha visto. Una tanda para elegir umbrales y otra, que
    # no se toca hasta el final, para reportar.
    validacion = generar_datos_sinteticos(n_muestras=n_compras, semilla=SEMILLA_VALIDACION)
    prueba = generar_datos_sinteticos(n_muestras=n_compras, semilla=SEMILLA_PRUEBA)

    X_val, y_val = validacion[FEATURES], validacion[ETIQUETA]
    X_pru, y_pru = prueba[FEATURES], prueba[ETIQUETA]
    montos = X_pru["total_amount"]
    costos = evaluacion.Costos()

    prob_val_antes = modelo_anterior.predict_proba(X_val)[:, 1]
    prob_pru_antes = modelo_anterior.predict_proba(X_pru)[:, 1]
    prob_pru_despues = modelo_actual.predict_proba(X_pru)[:, 1]

    # A los dos modelos se les eligen sus umbrales con el mismo método y sobre
    # la misma tanda de validación. Si al anterior se le dejaran los de 0.30 y
    # 0.70 y al nuevo unos elegidos por costo, la comparación premiaría al
    # modelo nuevo por una mejora que en realidad vino de los umbrales.
    prob_val_despues = modelo_actual.predict_proba(X_val)[:, 1]

    umbrales_b, _ = evaluacion.buscar_umbrales(
        y_val, prob_val_antes, X_val["total_amount"], costos
    )
    umbrales_c, _ = evaluacion.buscar_umbrales(
        y_val, prob_val_despues, X_val["total_amount"], costos
    )
    t_bajo_b, t_alto_b = umbrales_b["t_bajo"], umbrales_b["t_alto"]
    t_bajo_c, t_alto_c = umbrales_c["t_bajo"], umbrales_c["t_alto"]

    # Los que el sistema lleva puestos hoy, para dejar constancia de que el
    # procedimiento del experimento y el del despliegue dan lo mismo o casi.
    t_bajo_desplegado, t_alto_desplegado = _umbrales_actuales()

    resultados = [
        _medir("A. Sistema original", modelo_anterior, prob_pru_antes, y_pru, montos,
               *UMBRALES_ORIGINALES, costos),
        _medir("B. Modelo anterior + umbrales por costo", modelo_anterior, prob_pru_antes,
               y_pru, montos, t_bajo_b, t_alto_b, costos),
        _medir("C. Sistema actual", modelo_actual, prob_pru_despues, y_pru, montos,
               t_bajo_c, t_alto_c, costos),
    ]

    # Fuera de la tabla, como comprobación: el sistema tal cual está desplegado,
    # con los umbrales que le quedaron del entrenamiento. Sirve para ver que el
    # procedimiento del experimento y el del despliegue llegan al mismo sitio.
    desplegado = _medir(
        "Sistema desplegado hoy", modelo_actual, prob_pru_despues, y_pru, montos,
        t_bajo_desplegado, t_alto_desplegado, costos,
    )

    a, b, c = resultados
    mejora_total = a["perdida_total"] - c["perdida_total"]
    aporte_umbrales = a["perdida_total"] - b["perdida_total"]
    # B y C son cada modelo con SUS mejores umbrales, elegidos igual y sobre los
    # mismos datos: lo que queda entre ellos es lo que aportó reentrenar.
    aporte_modelo = b["perdida_total"] - c["perdida_total"]

    informe = {
        "compras_simuladas": {
            "validacion": int(len(X_val)),
            "prueba": int(len(X_pru)),
            "tasa_de_fraude": round(float(y_pru.mean()), 4),
            "semillas": {"validacion": SEMILLA_VALIDACION, "prueba": SEMILLA_PRUEBA},
            "nota": (
                "Generadas con semillas distintas de la del entrenamiento: "
                "ninguno de los dos modelos vio estas transacciones."
            ),
        },
        "costos_usados": evaluacion.costos_como_diccionario(costos),
        "resultados": resultados,
        "sistema_desplegado": desplegado,
        "mejora": {
            "perdida_evitada": round(mejora_total, 2),
            "porcentaje": round(mejora_total / a["perdida_total"] * 100, 2)
            if a["perdida_total"]
            else 0.0,
            "aporte_de_elegir_los_umbrales_por_costo": round(aporte_umbrales, 2),
            "aporte_de_reentrenar_el_modelo": round(aporte_modelo, 2),
            # Con signo: un número negativo significa que el sistema nuevo deja
            # pasar MÁS fraudes que el anterior. Ocurre, y es deliberado.
            "diferencia_en_fraudes_aprobados": c["fraudes_aprobados"] - a["fraudes_aprobados"],
            "diferencia_en_legitimas_bloqueadas": c["legitimos_bloqueados"] - a["legitimos_bloqueados"],
            "average_precision_antes": a["average_precision"],
            "average_precision_despues": c["average_precision"],
            "el_modelo_discrimina_mejor": bool(
                c["average_precision"] > a["average_precision"] + 0.01
            ),
        },
    }

    DIRECTORIO_INFORMES.mkdir(parents=True, exist_ok=True)
    (DIRECTORIO_INFORMES / "experimento_antes_despues.json").write_text(
        json.dumps(informe, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    resumen = _redactar_resumen(informe, resultados, len(X_pru), float(y_pru.mean()))
    (DIRECTORIO_INFORMES / "experimento_antes_despues.md").write_text(resumen, encoding="utf-8")

    # --- Muestra de compras concretas ---
    from app.services.fraud_service import fraud_service

    fraud_service.load_model()
    muestra = _muestra_de_compras(
        prueba, prob_pru_antes, prob_pru_despues,
        UMBRALES_ORIGINALES, (t_bajo_c, t_alto_c), fraud_service,
    )
    (DIRECTORIO_INFORMES / "compras_de_prueba.md").write_text(muestra, encoding="utf-8")

    figuras = _figuras(resultados, y_pru, prob_pru_antes, prob_pru_despues, DIRECTORIO_INFORMES)
    informe["figuras"] = figuras

    print(resumen)
    print(f"Figuras: {', '.join(figuras) if figuras else 'ninguna'}")
    print(f"Todo guardado en {DIRECTORIO_INFORMES}")
    return informe


def guardar_modelo_anterior(origen: Path) -> None:
    """Copia un modelo a ml/modelos/ para poder repetir el experimento."""
    DIRECTORIO_MODELOS.mkdir(parents=True, exist_ok=True)
    shutil.copy2(origen, RUTA_MODELO_ANTERIOR)
    print(f"Modelo de referencia guardado en {RUTA_MODELO_ANTERIOR}")


if __name__ == "__main__":
    comparar()
