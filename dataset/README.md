# Conjunto de datos para la detección de fraude

Esta carpeta contiene el conjunto de datos con el que se entrena y se evalúa el
modelo de detección de fraude de la tienda, junto con su documentación y su
análisis descriptivo. Está separada del código a propósito: es material que se
cita y se adjunta en el documento de la tesis, no un subproducto de una
ejecución.

## Qué hay aquí

| Archivo | Qué es |
| --- | --- |
| `dataset_sintetico.csv` | El conjunto completo: una fila por transacción, cuatro variables y la etiqueta |
| `diccionario_de_datos.md` | Qué representa cada columna, en qué unidad y de dónde sale |
| `estadisticas_del_dataset.md` | Media, mediana y cuartiles por clase, y el solapamiento entre clases |
| `estadisticas_del_dataset.json` | Lo mismo, en formato legible por máquina, con la matriz de correlación |
| `distribucion_de_variables.png` | Cómo se distribuye cada variable en cada clase |
| `correlacion_de_variables.png` | Matriz de correlación de Spearman |

## Cómo se regenera

```bash
cd backend
python -m ml.dataset            # el conjunto sintético
python -m ml.dataset --reales   # los pedidos etiquetados de la tienda
```

El generador vive en `backend/ml/dataset.py` y es determinista: con la misma
semilla (42) produce exactamente el mismo conjunto. Eso es lo que hace que los
resultados del entrenamiento sean reproducibles por cualquiera que clone el
repositorio.

## De dónde salen los datos

El sistema contempla dos fuentes y prefiere siempre la primera:

1. **Los pedidos reales de la tienda.** Cada compra deja un registro con las
   cuatro variables que se usaron para evaluarla. Cuando un administrador la
   revisa y la etiqueta —contracargo confirmado o compra legítima—, ese
   registro pasa a ser un ejemplo de entrenamiento. Se exigen al menos 200
   pedidos etiquetados con un mínimo de 30 de cada clase antes de usarlos.

2. **Un conjunto sintético del dominio**, que es el que está publicado aquí,
   mientras la tienda no acumule ese historial.

### Cómo se construye el conjunto sintético

No es un archivo descargado ni una tabla escrita a mano. Se genera con un
procedimiento explícito: primero se sortea la clase de cada transacción (7 % de
fraude) y después se generan sus cuatro variables **condicionadas a esa clase**,
con distribuciones tomadas del comportamiento descrito para una tienda de
componentes de cómputo:

| Variable | Compra legítima | Compra fraudulenta |
| --- | --- | --- |
| Monto | log-normal centrada en S/ 450 | log-normal centrada en S/ 2 200 |
| Artículos de alto riesgo | Poisson, λ = 0.5 | Poisson, λ = 2.0 |
| Duración del checkout | log-normal centrada en 200 s | log-normal centrada en 50 s |
| Dirección nueva | 20 % de los casos | 72 % de los casos |

Sobre el resultado se voltea el 1.5 % de las etiquetas. Ese ruido representa lo
que pasa en la práctica —no todo fraude se detecta ni toda denuncia de
contracargo resulta cierta— y evita que las clases queden perfectamente
separables.

### Por qué las clases se solapan a propósito

Es la decisión metodológica más importante del conjunto, y conviene poder
defenderla: **si las clases fueran separables por un umbral en una variable, el
problema no necesitaría aprendizaje automático** y bastaría un `if`. Las
estadísticas descriptivas muestran que no lo son:

| Variable | Legítimas | Fraudulentas | Solapamiento |
| --- | --- | --- | ---: |
| Monto del pedido | 742.70 (446.32) | 2616.82 (1694.14) | 0.239 |
| Artículos de alto riesgo | 0.52 (0.00) | 1.73 (2.00) | 0.410 |
| Duración del checkout | 292.86 (204.27) | 114.80 (62.30) | 0.264 |
| Dirección de envío nueva | 0.20 | 0.61 | — |

*Media (mediana). El solapamiento es la proporción de compras legítimas que caen
dentro del rango intercuartílico del fraude.*

Entre el 24 % y el 41 % de las compras legítimas caen dentro del rango típico
del fraude según la variable que se mire. Hay clientes honestos que compran una
tarjeta de video cara, rápido y a una dirección estrenada. Por eso el modelo
tiene que **ponderar señales** en lugar de aplicar cortes por variable, y por
eso un árbol de gradiente supera a las reglas heurísticas (0.697 contra 0.531 de
AUC-PR; ver `backend/ml/informes/comparacion_de_modelos.md`).

## Un intento anterior que no funcionó

La primera versión usaba un CSV público de fraude bancario y mapeaba sus
columnas a estas cuatro variables. Se descartó porque las semánticas no
coincidían: `checkout_duration_seconds` acababa derivándose de una marca de
tiempo ajena al checkout, con lo que era ruido puro, y el modelo terminaba
rechazando compras perfectamente normales. Vale la pena mencionarlo en la
metodología: un conjunto sintético bien especificado del propio dominio resultó
más honesto que uno real de otro dominio.

## Advertencia de uso

El conjunto publicado aquí es **sintético**. Sirve para demostrar que el método
funciona, para comparar modelos entre sí y para que los resultados sean
reproducibles. No mide el desempeño que el sistema tendrá con clientes reales:
esa cifra solo existirá cuando la tienda acumule pedidos etiquetados por un
administrador.
