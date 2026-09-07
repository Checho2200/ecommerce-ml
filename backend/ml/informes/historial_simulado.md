# Historial simulado de la tienda

300 compras repartidas entre el 01/06/2026 y el 06/09/2026, evaluadas una por una por el modelo que está en producción.

El tramo antiguo decide con los umbrales que el sistema traía escritos a mano (0.3 / 0.7); el nuevo, con los que el entrenamiento eligió minimizando el costo en soles (0.35 / 0.8). El tráfico se genera igual en los dos: lo único que cambia es el criterio de decisión.

| | Antes | Después |
| :--- | ---: | ---: |
| Compras evaluadas | 100 | 200 |
| Aprobadas | 74 | 146 |
| A revisión | 10 | 17 |
| Bloqueadas | 16 | 37 |
| Fraudes confirmados | 9 | 8 |
| Fraudes detectados | 5 | 7 |
| **Tasa de detección** | **55.6%** | **87.5%** |
| Compras buenas bloqueadas | 11 | 16 |
| Fraude que pasó (S/) | 4,991.00 | 1,676.00 |
| Margen perdido por frenar de más (S/) | 6,514.35 | 8,528.25 |
| **Costo total (S/)** | **11,505.35** | **10,204.25** |

Por compra evaluada, el costo de los errores baja de **S/ 115.05** a **S/ 51.02** (55.7%).


> **Cuidado con la tasa de deteccion de antes y despues.** Se calcula sobre menos de 30 fraudes confirmados, asi que un caso mas o menos la mueve varios puntos. Sirve para ver que el sistema mide, no para sostener que un tramo detecta mejor que el otro: para eso hay que alargar el tramo corto con --antes o --cuantas.


Quedan 79 compras sin etiquetar, casi todas recientes: el contracargo todavía no ha llegado o el plazo no ha vencido. Aparecen en el panel como evaluadas pero sin confirmar, que es como se ve una tienda de verdad — los indicadores del mes pasado están completos y los de esta semana se siguen llenando.


---

**Estas compras son simuladas.** El puntaje, la decisión, la explicación y el tiempo de cada una los produjo el modelo real evaluándolas de una en una; lo simulado es el tráfico: qué se compró, cuándo, y cuáles acabaron en contracargo. Sirven para demostrar el sistema y para medir el efecto del cambio de criterio, no como datos de venta. Las genera `app/scripts/simular_historial.py`.
