# Historial simulado de la tienda

1000 compras repartidas entre el 01/01/2026 y el 09/09/2026, evaluadas una por una por el modelo que está en producción.

El tramo antiguo decide con una regla fija sin modelo (bloquear si el monto pasa de S/ 1,500 y la dirección es nueva; revisar si pasa de ese monto o lleva 2 o más artículos de alto riesgo); el nuevo, con el modelo y los umbrales que el entrenamiento eligió minimizando el costo en soles (0.35 / 0.8). El tráfico se genera igual en los dos: lo único que cambia es el criterio de decisión.

## Los tres indicadores

Son los que mide la tesis. El corte es la entrada del modelo; a la izquierda, cómo operaba la tienda antes.

Los dos tramos llevan la misma cantidad de compras a propósito. Las tasas se calculan solo sobre los fraudes ya confirmados, y el tramo nuevo es mucho más corto en calendario: repartir las compras proporcionalmente a los días lo dejaría con tan pocos casos resueltos que su tasa se movería varios puntos por un caso más. Igualar la muestra es lo que permite comparar; a cambio, la densidad diaria del tramo nuevo es mayor, y conviene decirlo en vez de dejar que se deduzca del gráfico.

| Indicador | Antes | Después | Debe |
| :--- | ---: | ---: | :---: |
| Tasa de fraudes detectados | 82.9% | **90.6%** | subir |
| Tasa de fraude no detectado | 17.1% | **9.4%** | bajar |
| Tiempo de detección | 4.3 h | **1.8 ms** | bajar |

El tiempo de detección no compara dos clasificadores: compara **no tener detector** con tenerlo. Antes del modelo la regla fija solo levantaba la mano y quien decidía era una persona, cuando le llegaba el turno en la cola de revisión; ese es el tiempo de la izquierda. El de la derecha lo cronometra el propio servicio al puntuar cada compra, una por una, dentro de la petición que crea el pedido.

## El detalle

| | Antes | Después |
| :--- | ---: | ---: |
| Compras evaluadas | 500 | 500 |
| Aprobadas | 339 | 343 |
| A revisión | 112 | 102 |
| Bloqueadas | 49 | 55 |
| Fraudes confirmados | 35 | 32 |
| Fraudes detectados | 29 | 29 |
| **Tasa de detección** | **82.9%** | **90.6%** |
| Compras buenas bloqueadas | 26 | 15 |
| Fraude que pasó (S/) | 4,901.00 | 1,676.00 |
| Margen perdido por frenar de más (S/) | 9,976.50 | 5,821.50 |
| **Costo total (S/)** | **14,877.50** | **7,497.50** |

Por compra evaluada, el costo de los errores baja de **S/ 29.76** a **S/ 14.99** (49.6%).


Quedan 182 compras sin etiquetar, casi todas recientes: el contracargo todavía no ha llegado o el plazo no ha vencido. Aparecen en el panel como evaluadas pero sin confirmar, que es como se ve una tienda de verdad — los indicadores del mes pasado están completos y los de esta semana se siguen llenando.


Las compras que el sistema dejó pasar llevan además datos de cobro simulados —medio de pago, cuatro últimos dígitos y titular—, con la misma forma que los que deja un pago real. En una parte de ellas el titular no coincide con el de la cuenta: es la señal más común de tarjeta robada, y ninguna de las cuatro variables del modelo la ve, así que solo puede verla la persona que revisa.


---

**Estas compras son simuladas.** El puntaje, la decisión, la explicación y el tiempo de cada una los produjo el modelo real evaluándolas de una en una; lo simulado es el tráfico: qué se compró, cuándo, y cuáles acabaron en contracargo. Sirven para demostrar el sistema y para medir el efecto del cambio de criterio, no como datos de venta. Las genera `app/scripts/simular_historial.py`.
