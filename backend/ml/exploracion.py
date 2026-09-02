"""
Exporta el conjunto de datos y lo describe.

    python -m ml.dataset              # el conjunto sintético
    python -m ml.dataset --reales     # lo que haya etiquetado en la tienda

Un modelo no se puede defender sin enseñar con qué se entrenó. Esto deja en la
carpeta `dataset/` de la raíz del repositorio cuatro cosas que van directas al
documento:

- el conjunto en CSV, para adjuntarlo como anexo y que cualquiera lo reproduzca;
- el diccionario de datos: qué es cada variable, en qué unidad y de dónde sale;
- estadísticas descriptivas por clase, que es donde se ve *por qué* el problema
  no se resuelve con un `if`: las distribuciones se solapan;
- figuras de distribución por variable y matriz de correlación.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from ml.dataset import ETIQUETA, FEATURES, NOMBRES_LEGIBLES, Datos

# El conjunto de datos vive fuera de ml/informes/ y fuera de backend/, en una
# carpeta propia en la raíz del repositorio. Es material de la tesis por
# derecho propio —se cita, se adjunta y se explica en un capítulo aparte—, no
# un subproducto de una ejecución del entrenamiento.
DIRECTORIO_DATASET = Path(__file__).resolve().parents[2] / "dataset"

# Qué es cada variable, más allá de su nombre en la base.
DICCIONARIO = {
    "total_amount": (
        "Monto total del pedido",
        "soles (S/)",
        "Suma de precio × cantidad de cada ítem, calculada por el backend al "
        "crear la orden.",
    ),
    "high_risk_items_count": (
        "Unidades de categorías de alto riesgo",
        "unidades",
        "Cuenta las unidades cuya categoría está marcada como `is_high_risk` "
        "(tarjetas de video, procesadores): componentes caros y de reventa "
        "inmediata, que es lo que busca quien usa una tarjeta robada.",
    ),
    "checkout_duration_seconds": (
        "Duración del checkout",
        "segundos",
        "Tiempo entre que la persona abre la pantalla de pago y confirma. Lo "
        "mide el frontend y viaja con el pedido. Un checkout de pocos segundos "
        "sugiere datos de pago ya cargados o automatizados.",
    ),
    "is_new_shipping_address": (
        "Dirección de envío nueva",
        "0 o 1",
        "Vale 1 si ese cliente nunca antes había enviado a esa dirección. El "
        "backend lo resuelve consultando sus pedidos anteriores.",
    ),
    ETIQUETA: (
        "Etiqueta: el pedido resultó fraudulento",
        "0 o 1",
        "En los datos de la tienda, lo que un administrador marcó tras revisar "
        "el pedido. En el conjunto sintético, la clase con la que se generó.",
    ),
}


def diccionario_de_datos() -> str:
    """Tabla en Markdown con el significado de cada columna."""
    filas = "".join(
        f"| `{columna}` | {descripcion} | {unidad} | {origen} |\n"
        for columna, (descripcion, unidad, origen) in DICCIONARIO.items()
    )
    return (
        "# Diccionario de datos\n\n"
        "Las cuatro variables que mira el modelo, más la etiqueta.\n\n"
        "| Columna | Qué representa | Unidad | De dónde sale |\n"
        "| --- | --- | --- | --- |\n" + filas
    )


def _es_binaria(columna: pd.Series) -> bool:
    return set(columna.dropna().unique()) <= {0, 1}


def _es_conteo(columna: pd.Series) -> bool:
    """Enteros pequeños: se dibujan como barras, no como histograma."""
    return (
        pd.api.types.is_integer_dtype(columna) or (columna % 1 == 0).all()
    ) and columna.max() <= 20


def describir(df: pd.DataFrame) -> dict:
    """
    Estadísticas por clase de cada variable.

    Se reportan mediana y cuartiles además de la media porque los montos y las
    duraciones tienen cola larga: la media sola daría una imagen equivocada de
    cómo es un pedido típico.
    """
    resumen = {}
    for variable in FEATURES:
        por_clase = {}
        for clase, etiqueta in ((0, "legitimas"), (1, "fraudulentas")):
            valores = df.loc[df[ETIQUETA] == clase, variable]
            por_clase[etiqueta] = {
                "n": int(valores.size),
                "media": round(float(valores.mean()), 2) if valores.size else None,
                "desviacion": round(float(valores.std()), 2) if valores.size > 1 else None,
                "minimo": round(float(valores.min()), 2) if valores.size else None,
                "p25": round(float(valores.quantile(0.25)), 2) if valores.size else None,
                "mediana": round(float(valores.median()), 2) if valores.size else None,
                "p75": round(float(valores.quantile(0.75)), 2) if valores.size else None,
                "maximo": round(float(valores.max()), 2) if valores.size else None,
            }

        # Cuánto se solapan las dos clases en esta variable: la proporción de
        # pedidos legítimos que caen dentro del rango intercuartílico del
        # fraude. Cerca de cero sería una variable que separa sola; lejos de
        # cero es lo que obliga a ponderar señales.
        fraude = df.loc[df[ETIQUETA] == 1, variable]
        legitimos = df.loc[df[ETIQUETA] == 0, variable]
        solapamiento = None
        # En una variable binaria el rango intercuartilico cubre todos los
        # valores posibles y el solapamiento saldria 1 siempre, sin significar
        # nada: ahi lo que se compara son las proporciones de cada clase, que
        # ya estan en la tabla.
        if fraude.size and legitimos.size and not _es_binaria(df[variable]):
            bajo, alto = fraude.quantile(0.25), fraude.quantile(0.75)
            solapamiento = round(
                float(((legitimos >= bajo) & (legitimos <= alto)).mean()), 4
            )

        por_clase["solapamiento_con_el_fraude"] = solapamiento
        resumen[variable] = por_clase

    correlaciones = df[FEATURES + [ETIQUETA]].corr(method="spearman").round(3)
    return {
        "por_variable": resumen,
        "correlacion_spearman": json.loads(correlaciones.to_json()),
    }


def tabla_descriptiva(resumen: dict) -> str:
    """La descripción por clase, en Markdown."""
    lineas = [
        "# Estadísticas descriptivas\n",
        "Media (mediana) de cada variable, separando las dos clases. La última",
        "columna es la proporción de pedidos legítimos que caen dentro del rango",
        "intercuartílico del fraude: cuanto más alta, más se solapan las clases y",
        "menos sirve mirar esa variable por separado.\n",
        "| Variable | Legítimas | Fraudulentas | Solapamiento |",
        "| --- | --- | --- | ---: |",
    ]
    for variable, datos in resumen.items():
        legit, fraude = datos["legitimas"], datos["fraudulentas"]
        lineas.append(
            f"| {NOMBRES_LEGIBLES.get(variable, variable)} | "
            f"{legit['media']} ({legit['mediana']}) | "
            f"{fraude['media']} ({fraude['mediana']}) | "
            f"{datos['solapamiento_con_el_fraude'] if datos['solapamiento_con_el_fraude'] is not None else '—'} |"
        )
    return "\n".join(lineas) + "\n"


def figuras(df: pd.DataFrame, destino: Path) -> list[str]:
    """Distribución de cada variable por clase, y matriz de correlación."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib no está instalada; se omiten las figuras del conjunto.")
        return []

    destino.mkdir(parents=True, exist_ok=True)
    creadas = []

    # --- Una rejilla 2×2 con la distribución de cada variable ---
    try:
        fig, ejes = plt.subplots(2, 2, figsize=(10, 7))
        for eje, variable in zip(ejes.ravel(), FEATURES):
            legitimos = df.loc[df[ETIQUETA] == 0, variable]
            fraude = df.loc[df[ETIQUETA] == 1, variable]

            if _es_binaria(df[variable]) or _es_conteo(df[variable]):
                # Conteos pequeños y variables binarias: barras por valor. En
                # escala logarítmica se apelotonarían todas sobre el mismo
                # punto y no se vería nada.
                valores = sorted(df[variable].unique())
                posiciones = np.arange(len(valores))
                eje.bar(
                    posiciones - 0.2,
                    [float((legitimos == v).mean()) for v in valores],
                    width=0.4, label="Legítimas", color="#0C3A6E",
                )
                eje.bar(
                    posiciones + 0.2,
                    [float((fraude == v).mean()) for v in valores],
                    width=0.4, label="Fraudulentas", color="#E11D2E",
                )
                if variable == "is_new_shipping_address":
                    eje.set_xticks(posiciones, ["Conocida", "Nueva"])
                else:
                    eje.set_xticks(posiciones, [str(int(v)) for v in valores])
                eje.set_ylabel("Proporción")
            else:
                # Escala logarítmica: montos y duraciones tienen cola larga.
                bordes = np.logspace(
                    np.log10(max(df[variable].min(), 0.5)),
                    np.log10(df[variable].max()),
                    35,
                )
                eje.hist(legitimos, bins=bordes, alpha=0.65, label="Legítimas", color="#0C3A6E", density=True)
                eje.hist(fraude, bins=bordes, alpha=0.65, label="Fraudulentas", color="#E11D2E", density=True)
                eje.set_xscale("log")
                eje.set_ylabel("Densidad")

            eje.set_title(NOMBRES_LEGIBLES.get(variable, variable))
            eje.legend(fontsize=8)

        fig.suptitle("Distribución de las variables por clase", fontweight="bold")
        fig.tight_layout()
        ruta = destino / "distribucion_de_variables.png"
        fig.savefig(ruta, dpi=150, bbox_inches="tight")
        plt.close(fig)
        creadas.append(ruta.name)
    except Exception as exc:  # noqa: BLE001 - una figura no puede tumbar la exportación
        print(f"No se pudo generar la distribución de variables: {exc}")
        plt.close("all")

    # --- Matriz de correlación ---
    try:
        columnas = FEATURES + [ETIQUETA]
        matriz = df[columnas].corr(method="spearman").to_numpy()
        etiquetas = [NOMBRES_LEGIBLES.get(c, "es fraude") for c in columnas]

        fig, eje = plt.subplots(figsize=(6.2, 5.2))
        imagen = eje.imshow(matriz, cmap="RdBu_r", vmin=-1, vmax=1)
        eje.set_xticks(range(len(columnas)), etiquetas, rotation=35, ha="right", fontsize=8)
        eje.set_yticks(range(len(columnas)), etiquetas, fontsize=8)
        for i in range(len(columnas)):
            for j in range(len(columnas)):
                eje.text(
                    j, i, f"{matriz[i, j]:.2f}", ha="center", va="center", fontsize=8,
                    color="white" if abs(matriz[i, j]) > 0.55 else "black",
                )
        eje.set_title("Correlación de Spearman")
        fig.colorbar(imagen, ax=eje)
        ruta = destino / "correlacion_de_variables.png"
        fig.savefig(ruta, dpi=150, bbox_inches="tight")
        plt.close(fig)
        creadas.append(ruta.name)
    except Exception as exc:  # noqa: BLE001
        print(f"No se pudo generar la matriz de correlación: {exc}")
        plt.close("all")

    return creadas


def exportar(datos: Datos, destino: Path = DIRECTORIO_DATASET) -> dict:
    """Escribe el CSV, el diccionario, las estadísticas y las figuras."""
    destino.mkdir(parents=True, exist_ok=True)
    df = datos.df[FEATURES + [ETIQUETA]]

    nombre_csv = f"dataset_{datos.origen}.csv"
    df.to_csv(destino / nombre_csv, index=False, encoding="utf-8")

    (destino / "diccionario_de_datos.md").write_text(
        diccionario_de_datos(), encoding="utf-8"
    )

    resumen = describir(df)
    informe = {
        "origen": datos.origen,
        "detalle": datos.detalle,
        "filas": int(len(df)),
        "tasa_de_fraude": round(float(df[ETIQUETA].mean()), 4),
        "archivo": nombre_csv,
        **resumen,
    }
    (destino / "estadisticas_del_dataset.json").write_text(
        json.dumps(informe, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (destino / "estadisticas_del_dataset.md").write_text(
        tabla_descriptiva(resumen["por_variable"]), encoding="utf-8"
    )

    archivos = [
        nombre_csv,
        "diccionario_de_datos.md",
        "estadisticas_del_dataset.json",
        "estadisticas_del_dataset.md",
        *figuras(df, destino),
    ]

    print(f"\nConjunto exportado ({datos.origen}): {len(df)} filas")
    print(tabla_descriptiva(resumen["por_variable"]))
    print(f"Archivos en {destino}:")
    for archivo in archivos:
        print(f"  {archivo}")

    return informe
