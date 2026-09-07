# Historial simulado de la tienda

1000 compras repartidas entre el 01/06/2026 y el 06/09/2026, evaluadas una por una por el modelo que está en producción.

El tramo antiguo decide con los umbrales que el sistema traía escritos a mano (0.3 / 0.7); el nuevo, con los que el entrenamiento eligió minimizando el costo en soles (0.35 / 0.8). El tráfico se genera igual en los dos: lo único que cambia es el criterio de decisión.

| | Antes | Después |
| :--- | ---: | ---: |
| Compras evaluadas | 100 | 900 |
| Aprobadas | 77 | 662 |
| A revisión | 5 | 88 |
| Bloqueadas | 18 | 150 |
| Fraudes confirmados | 6 | 47 |
| Fraudes detectados | 4 | 30 |
| **Tasa de detección** | **66.7%** | **63.8%** |
| Compras buenas bloqueadas | 12 | 82 |
| Fraude que pasó (S/) | 2,224.00 | 13,724.00 |
| Margen perdido por frenar de más (S/) | 5,787.60 | 53,521.20 |
| **Costo total (S/)** | **8,011.60** | **67,245.20** |

Por compra evaluada, el costo de los errores baja de **S/ 80.12** a **S/ 74.72** (6.7%).


> **Cuidado con la tasa de deteccion de antes.** Se calcula sobre menos de 30 fraudes confirmados, asi que un caso mas o menos la mueve varios puntos. Sirve para ver que el sistema mide, no para sostener que un tramo detecta mejor que el otro: para eso hay que alargar el tramo corto con --antes o --cuantas.


Quedan 310 compras sin etiquetar, casi todas recientes: el contracargo todavía no ha llegado o el plazo no ha vencido. Aparecen en el panel como evaluadas pero sin confirmar, que es como se ve una tienda de verdad — los indicadores del mes pasado están completos y los de esta semana se siguen llenando.


---

**Estas compras son simuladas.** El puntaje, la decisión, la explicación y el tiempo de cada una los produjo el modelo real evaluándolas de una en una; lo simulado es el tráfico: qué se compró, cuándo, y cuáles acabaron en contracargo. Sirven para demostrar el sistema y para medir el efecto del cambio de criterio, no como datos de venta. Las genera `app/scripts/simular_historial.py`.
