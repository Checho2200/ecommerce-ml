"""
Cómo se mide el modelo y cómo se eligen sus dos umbrales.

Tres ideas gobiernan este archivo:

1. **El acierto global (accuracy) no sirve aquí.** Con un 7 % de fraude, un
   modelo que apruebe todo acierta el 93 % de las veces y no detecta ni un
   caso. Las métricas que mandan son las de la clase minoritaria: precisión,
   exhaustividad (recall), F1 y sobre todo el **AUC-PR**, que a diferencia del
   AUC-ROC no se infla cuando los negativos son abrumadora mayoría.

2. **Los umbrales no se eligen a ojo.** Aprobar un fraude cuesta la mercadería
   más el cargo del contracargo; bloquear una compra legítima cuesta el margen
   de esa venta; mandar a revisión cuesta el tiempo de una persona. Con esos
   tres precios se puede calcular, para cada par de umbrales, cuánto dinero
   pierde la tienda al año, y quedarse con el par más barato. Eso convierte
   una decisión arbitraria en un resultado defendible.

3. **Todo lo que se calcula se guarda.** Las métricas van a un JSON y las
   figuras a PNG, para que el documento de la tesis cite números que se pueden
   volver a producir, y no capturas de una consola que ya se cerró.
"""

from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)


# ─────────────────────────────────────────────────────────────────────────────
# Métricas de clasificación
# ─────────────────────────────────────────────────────────────────────────────
def metricas(y_true, y_prob, umbral: float = 0.5) -> dict:
    """
    Métricas de un clasificador binario a un umbral dado.

    `average_precision` es el área bajo la curva precisión-exhaustividad: la
    métrica de referencia cuando la clase positiva es rara.
    """
    y_true = np.asarray(y_true)
    y_prob = np.asarray(y_prob)
    y_pred = (y_prob >= umbral).astype(int)

    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()

    return {
        "umbral": round(float(umbral), 4),
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
        "f1": round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score(y_true, y_prob)), 4),
        "average_precision": round(float(average_precision_score(y_true, y_prob)), 4),
        "matriz_de_confusion": {
            "verdaderos_negativos": int(tn),
            "falsos_positivos": int(fp),
            "falsos_negativos": int(fn),
            "verdaderos_positivos": int(tp),
        },
        "positivos_reales": int(y_true.sum()),
        "total": int(len(y_true)),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Umbrales elegidos por costo
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class Costos:
    """
    Lo que cuesta cada tipo de error, en soles.

    Los valores por defecto son los de una tienda de componentes de cómputo:

    - `margen_bruto`: proporción del precio que es ganancia. Bloquear una
      compra legítima no cuesta el pedido entero, cuesta lo que se habría
      ganado con él.
    - `cargo_por_contracargo`: lo que cobra la pasarela por gestionar un
      contracargo, además de devolver el importe. Aprobar un fraude cuesta el
      monto completo (la mercadería ya salió) más este cargo.
    - `revision_manual`: el tiempo de la persona que revisa un pedido dudoso.
    - `acierto_de_la_revision`: con qué frecuencia esa persona decide bien. No
      es 1: quien revisa ve los mismos datos que el modelo y también se
      equivoca. Sin este factor el optimizador descubre que mandar todo a
      revisión sale casi gratis y propone umbrales que dejan el 84 % de los
      pedidos en manos de un humano.
    - `capacidad_de_revision`: qué proporción de los pedidos puede revisar el
      negocio a mano. Es una restricción operativa, no un costo: una tienda
      pequeña no tiene a nadie mirando ocho de cada diez compras, por barato
      que salga en la hoja de cálculo. Los pares de umbrales que se pasan de
      esta capacidad se descartan aunque su costo sea menor.
    - `deteccion_minima`: qué proporción de los fraudes tiene que frenar el
      modelo. Tampoco es un costo, y por eso hace falta declararla: el
      optimizador razona en soles, y en soles un fraude pequeño que se escapa
      sale más barato que las revisiones que costaría atraparlo. La cuenta
      sale bien y el indicador que mide la tesis —la tasa de fraudes
      detectados— se hunde. Fijar un piso obliga a que el par elegido sea el
      más barato *de los que detectan lo suficiente*, en vez del más barato a
      secas.
    """

    margen_bruto: float = 0.15
    cargo_por_contracargo: float = 30.0
    revision_manual: float = 4.0
    acierto_de_la_revision: float = 0.90
    capacidad_de_revision: float = 0.15
    deteccion_minima: float = 0.80


def costo_de_los_umbrales(y_true, y_prob, montos, t_bajo, t_alto, costos: Costos) -> dict:
    """
    Cuánto dinero pierde la tienda con un par de umbrales dado.

    - Por debajo de `t_bajo` el pedido se aprueba: si era fraude, se pierde el
      monto más el cargo del contracargo.
    - Entre ambos umbrales se revisa a mano: cuesta el tiempo del revisor más
      los errores que ese revisor comete, porque no acierta siempre.
    - Por encima de `t_alto` se bloquea: si era legítimo, se pierde el margen
      de una venta que no ocurrió.
    """
    y_true = np.asarray(y_true)
    y_prob = np.asarray(y_prob)
    montos = np.asarray(montos, dtype=float)

    aprobados = y_prob < t_bajo
    revisados = (y_prob >= t_bajo) & (y_prob < t_alto)
    bloqueados = y_prob >= t_alto

    fraude = y_true == 1
    legitimo = ~fraude

    perdida_por_fraude_aprobado = float(
        (montos[aprobados & fraude] + costos.cargo_por_contracargo).sum()
    )
    perdida_por_venta_bloqueada = float(
        (montos[bloqueados & legitimo] * costos.margen_bruto).sum()
    )
    # La revisión cuesta el tiempo de la persona y, además, sus equivocaciones:
    # el fraude que aprueba por error sale tan caro como si nadie lo hubiera
    # mirado, y la compra legítima que frena cuesta el margen igual.
    error = 1.0 - costos.acierto_de_la_revision
    costo_de_revisiones = float(
        revisados.sum() * costos.revision_manual
        + error * (montos[revisados & fraude] + costos.cargo_por_contracargo).sum()
        + error * (montos[revisados & legitimo] * costos.margen_bruto).sum()
    )

    # Los indicadores que mide la tesis, con la misma definición que usa el
    # panel: un fraude está detectado si el modelo no lo dejó pasar, sea porque
    # lo bloqueó o porque lo mandó a revisión.
    fraudes_totales = int(fraude.sum())
    fraudes_no_detectados = int((aprobados & fraude).sum())
    fraudes_detectados = fraudes_totales - fraudes_no_detectados

    return {
        "t_bajo": round(float(t_bajo), 2),
        "t_alto": round(float(t_alto), 2),
        "costo_total": round(
            perdida_por_fraude_aprobado + perdida_por_venta_bloqueada + costo_de_revisiones, 2
        ),
        "perdida_por_fraude_aprobado": round(perdida_por_fraude_aprobado, 2),
        "perdida_por_venta_bloqueada": round(perdida_por_venta_bloqueada, 2),
        "costo_de_revisiones": round(costo_de_revisiones, 2),
        "pedidos_aprobados": int(aprobados.sum()),
        "pedidos_revisados": int(revisados.sum()),
        "pedidos_bloqueados": int(bloqueados.sum()),
        "fraudes_aprobados": fraudes_no_detectados,
        "legitimos_bloqueados": int((bloqueados & legitimo).sum()),
        "fraudes_detectados": fraudes_detectados,
        "tasa_de_deteccion": round(fraudes_detectados / fraudes_totales, 4) if fraudes_totales else 0.0,
        "tasa_de_no_deteccion": round(fraudes_no_detectados / fraudes_totales, 4) if fraudes_totales else 0.0,
    }


def buscar_umbrales(
    y_true,
    y_prob,
    montos,
    costos: Costos | None = None,
    paso: float = 0.05,
) -> tuple[dict, list[dict]]:
    """
    Prueba todos los pares de umbrales y devuelve (el mejor, la rejilla entera).

    "El mejor" es el más barato **entre los que caben en la capacidad de
    revisión del negocio y detectan al menos la proporción de fraude que se
    exige**. Las dos restricciones existen por el mismo motivo: el optimizador
    razona en soles, y hay respuestas baratísimas que ninguna tienda aceptaría.

    - Sin el tope de revisión, el óptimo manda a revisión manual la mayoría de
      los pedidos.
    - Sin el piso de detección, deja escapar los fraudes pequeños, porque
      atraparlos cuesta más revisiones de lo que valen. La cuenta sale bien y
      el indicador que mide la tesis se hunde.

    Cuando ningún par cumple las dos cosas, se elige el que más fraude detecta
    entre los que sí caben en la capacidad, y el resultado lo dice en
    `regla_aplicada`: es información que la tesis tiene que poder citar, no un
    detalle que convenga esconder.

    La rejilla completa se devuelve para dibujar la superficie de costo: esa
    figura muestra que el par elegido no fue una corazonada, y cuánto margen
    hay alrededor del óptimo.
    """
    costos = costos or Costos()
    candidatos = np.round(np.arange(paso, 1.0, paso), 2)
    total = len(np.asarray(y_true))

    rejilla = [
        costo_de_los_umbrales(y_true, y_prob, montos, t_bajo, t_alto, costos)
        for t_bajo in candidatos
        for t_alto in candidatos
        if t_alto >= t_bajo
    ]

    for fila in rejilla:
        fila["proporcion_revisada"] = round(fila["pedidos_revisados"] / total, 4)
        fila["dentro_de_capacidad"] = (
            fila["proporcion_revisada"] <= costos.capacidad_de_revision
        )
        fila["detecta_lo_suficiente"] = (
            fila["tasa_de_deteccion"] >= costos.deteccion_minima
        )

    caben = [fila for fila in rejilla if fila["dentro_de_capacidad"]] or rejilla
    detectan = [fila for fila in caben if fila["detecta_lo_suficiente"]]

    if detectan:
        mejor = min(detectan, key=lambda fila: fila["costo_total"])
        regla = (
            f"el más barato entre los que caben en la capacidad de revisión "
            f"({costos.capacidad_de_revision:.0%}) y detectan al menos el "
            f"{costos.deteccion_minima:.0%} del fraude"
        )
    else:
        # Ningún par llega al piso. Antes que rebajar el objetivo en silencio,
        # se elige el que más detecta —desempatando por costo— y se deja dicho.
        mejor = min(caben, key=lambda fila: (-fila["tasa_de_deteccion"], fila["costo_total"]))
        regla = (
            f"ningún par alcanzó el piso de detección del "
            f"{costos.deteccion_minima:.0%}; se eligió el que más fraude detecta "
            f"({mejor['tasa_de_deteccion']:.0%}) dentro de la capacidad de revisión"
        )

    mejor = {**mejor, "regla_aplicada": regla}
    return mejor, rejilla


def comparar_con_referencia(mejor: dict, referencia: dict, total: int, costos: Costos) -> dict:
    """
    Cuánto se ahorra respecto de unos umbrales de referencia (los antiguos).

    Se informa además si esa referencia era siquiera operable. La comparación
    de costos por sí sola puede engañar: unos umbrales que mandan a revisión
    manual la mitad de los pedidos salen baratísimos en la ecuación —revisar
    cuesta poco— pero no existe quien haga ese trabajo. Cuando la referencia se
    pasa de la capacidad, el ahorro no es la conclusión: la conclusión es que
    la referencia no era aplicable.
    """
    proporcion = referencia["pedidos_revisados"] / total if total else 0.0
    ahorro = referencia["costo_total"] - mejor["costo_total"]
    porcentaje = (ahorro / referencia["costo_total"] * 100) if referencia["costo_total"] else 0.0
    return {
        "costo_con_umbrales_elegidos": mejor["costo_total"],
        "costo_con_umbrales_de_referencia": referencia["costo_total"],
        "ahorro": round(ahorro, 2),
        "ahorro_porcentual": round(porcentaje, 2),
        "proporcion_revisada_con_los_elegidos": mejor.get("proporcion_revisada"),
        "proporcion_revisada_con_la_referencia": round(proporcion, 4),
        "la_referencia_cabe_en_la_capacidad": proporcion <= costos.capacidad_de_revision,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Figuras
# ─────────────────────────────────────────────────────────────────────────────
def guardar_figuras(
    y_true, y_prob, rejilla_de_costos, destino: Path, elegido: dict | None = None
) -> list[str]:
    """
    Escribe las figuras del informe. Devuelve los archivos que llegó a crear.

    matplotlib es dependencia de desarrollo, no de producción: el servidor
    reentrena el modelo sin ella. Si no está instalada no se generan figuras y
    el resto del informe sale igual.
    """
    try:
        import matplotlib

        matplotlib.use("Agg")  # sin ventana: esto corre en consola y en CI
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib no está instalada; se omiten las figuras.")
        return []

    y_true = np.asarray(y_true)
    y_prob = np.asarray(y_prob)
    destino.mkdir(parents=True, exist_ok=True)
    creadas = []

    def cerrar(fig, nombre):
        ruta = destino / nombre
        fig.savefig(ruta, dpi=150, bbox_inches="tight")
        plt.close(fig)
        creadas.append(nombre)

    def dibujar(nombre, construir):
        """
        Genera una figura sin que un fallo suyo tumbe el entrenamiento.

        Pasó de verdad: con pocos datos reales y puntajes casi idénticos, el
        histograma reventaba con "Too many bins for data range" y se llevaba por
        delante toda la ejecución, modelo incluido. Una figura es un adorno del
        informe; el modelo no.
        """
        try:
            construir()
        except Exception as exc:  # noqa: BLE001 - se reporta y se sigue
            print(f"No se pudo generar {nombre}: {exc}")
            plt.close("all")

    def particiones_del_histograma(valores) -> int:
        """
        Cuántas barras admite este conjunto de puntajes.

        Si todos los valores son iguales —clases perfectamente separables, que
        es lo normal con pocos datos— el rango es cero y no se puede partir en
        cuarenta tramos.
        """
        valores = np.asarray(valores)
        # No basta con exigir rango distinto de cero: si todos los puntajes
        # caen en un pañuelo, los bordes de las barras no se distinguen en
        # coma flotante y matplotlib se niega igual.
        if valores.size == 0 or np.ptp(valores) < 1e-6:
            return 1
        return int(min(40, max(5, valores.size // 10)))

    # --- Curva ROC ---
    def curva_roc():
        fpr, tpr, _ = roc_curve(y_true, y_prob)
        fig, ax = plt.subplots(figsize=(5, 4.2))
        ax.plot(fpr, tpr, lw=2, label=f"LightGBM (AUC = {roc_auc_score(y_true, y_prob):.3f})")
        ax.plot([0, 1], [0, 1], "--", color="gray", lw=1, label="Azar")
        ax.set_xlabel("Tasa de falsos positivos")
        ax.set_ylabel("Tasa de verdaderos positivos")
        ax.set_title("Curva ROC")
        ax.legend(loc="lower right")
        cerrar(fig, "curva_roc.png")

    dibujar("la curva ROC", curva_roc)

    # --- Curva precisión-exhaustividad ---
    def curva_pr():
        precision, recall, _ = precision_recall_curve(y_true, y_prob)
        ap = average_precision_score(y_true, y_prob)
        tasa_base = y_true.mean()
        fig, ax = plt.subplots(figsize=(5, 4.2))
        ax.plot(recall, precision, lw=2, label=f"LightGBM (AP = {ap:.3f})")
        ax.axhline(tasa_base, ls="--", color="gray", lw=1, label=f"Azar ({tasa_base:.3f})")
        ax.set_xlabel("Exhaustividad (recall)")
        ax.set_ylabel("Precisión")
        ax.set_title("Curva precisión-exhaustividad")
        ax.legend(loc="upper right")
        cerrar(fig, "curva_precision_exhaustividad.png")

    dibujar("la curva precisión-exhaustividad", curva_pr)

    # --- Distribución de puntajes por clase ---
    def distribucion():
        legitimas = y_prob[y_true == 0]
        fraudulentas = y_prob[y_true == 1]
        fig, ax = plt.subplots(figsize=(5.4, 4.2))
        ax.hist(
            legitimas, bins=particiones_del_histograma(legitimas),
            alpha=0.7, label="Legítimas", color="#0C3A6E",
        )
        ax.hist(
            fraudulentas, bins=particiones_del_histograma(fraudulentas),
            alpha=0.7, label="Fraudulentas", color="#E11D2E",
        )
        ax.set_xlabel("Probabilidad de fraude")
        ax.set_ylabel("Transacciones")
        ax.set_yscale("log")
        ax.set_title("Distribución de los puntajes")
        ax.legend()
        cerrar(fig, "distribucion_de_puntajes.png")

    dibujar("la distribución de puntajes", distribucion)

    # --- Superficie de costo sobre los umbrales ---
    def superficie():
        bajos = sorted({fila["t_bajo"] for fila in rejilla_de_costos})
        altos = sorted({fila["t_alto"] for fila in rejilla_de_costos})
        matriz = np.full((len(altos), len(bajos)), np.nan)
        for fila in rejilla_de_costos:
            matriz[altos.index(fila["t_alto"]), bajos.index(fila["t_bajo"])] = fila["costo_total"]

        # El punto que se marca es el que el sistema usa de verdad, no el
        # mínimo de la superficie: son distintos justamente porque el mínimo
        # suele exigir más revisión manual de la que el negocio puede hacer, y
        # esa diferencia es una de las conclusiones del trabajo.
        sin_restriccion = min(rejilla_de_costos, key=lambda f: f["costo_total"])
        usado = elegido or sin_restriccion

        fig, ax = plt.subplots(figsize=(5.9, 4.6))
        imagen = ax.imshow(matriz, origin="lower", aspect="auto", cmap="viridis_r")
        ax.set_xticks(range(0, len(bajos), 2), [f"{v:.2f}" for v in bajos[::2]], rotation=45)
        ax.set_yticks(range(0, len(altos), 2), [f"{v:.2f}" for v in altos[::2]])

        if (sin_restriccion["t_bajo"], sin_restriccion["t_alto"]) != (
            usado["t_bajo"],
            usado["t_alto"],
        ):
            ax.scatter(
                bajos.index(sin_restriccion["t_bajo"]),
                altos.index(sin_restriccion["t_alto"]),
                # Borde negro y no blanco: sobre el mapa se ve igual de bien, y
                # en la leyenda —de fondo claro— el marcador blanco desaparecía.
                marker="o", s=90, facecolor="none", edgecolor="black",
                linewidth=1.8, zorder=3,
                label=(
                    f"Mínimo sin restricción ({sin_restriccion['t_bajo']}, "
                    f"{sin_restriccion['t_alto']})"
                ),
            )

        ax.scatter(
            bajos.index(usado["t_bajo"]),
            altos.index(usado["t_alto"]),
            marker="*", s=240, color="white", edgecolor="black", zorder=4,
            label=f"Umbrales elegidos ({usado['t_bajo']}, {usado['t_alto']})",
        )
        ax.set_xlabel("Umbral de aprobación")
        ax.set_ylabel("Umbral de bloqueo")
        ax.set_title("Costo esperado según los umbrales")
        fig.colorbar(imagen, ax=ax, label="Pérdida total (S/)")
        ax.legend(loc="lower right", fontsize=7.5)
        cerrar(fig, "costo_por_umbrales.png")

    if rejilla_de_costos:
        dibujar("la superficie de costo", superficie)

    return creadas


def guardar_matriz_de_confusion(metricas_dict: dict, destino: Path, nombre: str) -> str | None:
    """Dibuja la matriz de confusión del umbral evaluado."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return None

    m = metricas_dict["matriz_de_confusion"]
    matriz = np.array(
        [
            [m["verdaderos_negativos"], m["falsos_positivos"]],
            [m["falsos_negativos"], m["verdaderos_positivos"]],
        ]
    )

    destino.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(4.4, 4))
    ax.imshow(matriz, cmap="Blues")
    etiquetas = ["Legítima", "Fraude"]
    ax.set_xticks([0, 1], etiquetas)
    ax.set_yticks([0, 1], etiquetas)
    ax.set_xlabel("Predicción")
    ax.set_ylabel("Realidad")
    ax.set_title(f"Matriz de confusión (umbral {metricas_dict['umbral']})")
    for i in range(2):
        for j in range(2):
            ax.text(
                j, i, f"{matriz[i, j]:,}",
                ha="center", va="center",
                color="white" if matriz[i, j] > matriz.max() / 2 else "black",
                fontweight="bold",
            )
    ruta = destino / nombre
    fig.savefig(ruta, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return nombre


def costos_como_diccionario(costos: Costos) -> dict:
    return asdict(costos)
