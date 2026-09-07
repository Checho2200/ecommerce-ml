# Historial simulado de la tienda

1400 compras repartidas entre el 26/06/2026 y el 06/09/2026, evaluadas una por una por el modelo que está en producción.

El tramo antiguo decide con una regla fija sin modelo (bloquear si el monto pasa de S/ 1,500 y la dirección es nueva; revisar si pasa de ese monto o lleva 2 o más artículos de alto riesgo); el nuevo, con el modelo y los umbrales que el entrenamiento eligió minimizando el costo en soles (0.35 / 0.8). El tráfico se genera igual en los dos: lo único que cambia es el criterio de decisión.

| | Antes | Después |
| :--- | ---: | ---: |
| Compras evaluadas | 700 | 700 |
| Aprobadas | 487 | 477 |
| A revisión | 146 | 144 |
| Bloqueadas | 67 | 79 |
| Fraudes confirmados | 49 | 40 |
| Fraudes detectados | 35 | 36 |
| **Tasa de detección** | **71.4%** | **90.0%** |
| Compras buenas bloqueadas | 35 | 27 |
| Fraude que pasó (S/) | 14,541.00 | 3,034.00 |
| Margen perdido por frenar de más (S/) | 14,662.65 | 10,968.00 |
| **Costo total (S/)** | **29,203.65** | **14,002.00** |

Por compra evaluada, el costo de los errores baja de **S/ 41.72** a **S/ 20.00** (52.1%).


Quedan 282 compras sin etiquetar, casi todas recientes: el contracargo todavía no ha llegado o el plazo no ha vencido. Aparecen en el panel como evaluadas pero sin confirmar, que es como se ve una tienda de verdad — los indicadores del mes pasado están completos y los de esta semana se siguen llenando.


---

**Estas compras son simuladas.** El puntaje, la decisión, la explicación y el tiempo de cada una los produjo el modelo real evaluándolas de una en una; lo simulado es el tráfico: qué se compró, cuándo, y cuáles acabaron en contracargo. Sirven para demostrar el sistema y para medir el efecto del cambio de criterio, no como datos de venta. Las genera `app/scripts/simular_historial.py`.
