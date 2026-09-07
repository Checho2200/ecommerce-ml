# Historial simulado de la tienda

1400 compras repartidas entre el 26/06/2026 y el 06/09/2026, evaluadas una por una por el modelo que está en producción.

El tramo antiguo decide con los umbrales que el sistema traía escritos a mano (0.3 / 0.7); el nuevo, con los que el entrenamiento eligió minimizando el costo en soles (0.35 / 0.8). El tráfico se genera igual en los dos: lo único que cambia es el criterio de decisión.

| | Antes | Después |
| :--- | ---: | ---: |
| Compras evaluadas | 700 | 700 |
| Aprobadas | 464 | 477 |
| A revisión | 134 | 144 |
| Bloqueadas | 102 | 79 |
| Fraudes confirmados | 49 | 40 |
| Fraudes detectados | 45 | 36 |
| **Tasa de detección** | **91.8%** | **90.0%** |
| Compras buenas bloqueadas | 53 | 27 |
| Fraude que pasó (S/) | 2,932.00 | 3,034.00 |
| Margen perdido por frenar de más (S/) | 22,009.20 | 10,968.00 |
| **Costo total (S/)** | **24,941.20** | **14,002.00** |

Por compra evaluada, el costo de los errores baja de **S/ 35.63** a **S/ 20.00** (43.9%).


Quedan 282 compras sin etiquetar, casi todas recientes: el contracargo todavía no ha llegado o el plazo no ha vencido. Aparecen en el panel como evaluadas pero sin confirmar, que es como se ve una tienda de verdad — los indicadores del mes pasado están completos y los de esta semana se siguen llenando.


---

**Estas compras son simuladas.** El puntaje, la decisión, la explicación y el tiempo de cada una los produjo el modelo real evaluándolas de una en una; lo simulado es el tráfico: qué se compró, cuándo, y cuáles acabaron en contracargo. Sirven para demostrar el sistema y para medir el efecto del cambio de criterio, no como datos de venta. Las genera `app/scripts/simular_historial.py`.
