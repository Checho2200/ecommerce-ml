# Historial simulado de la tienda

1000 compras repartidas entre el 01/05/2026 y el 06/09/2026, evaluadas una por una por el modelo que está en producción.

El tramo antiguo decide con los umbrales que el sistema traía escritos a mano (0.3 / 0.7); el nuevo, con los que el entrenamiento eligió minimizando el costo en soles (0.35 / 0.8). El tráfico se genera igual en los dos: lo único que cambia es el criterio de decisión.

| | Antes | Después |
| :--- | ---: | ---: |
| Compras evaluadas | 100 | 900 |
| Aprobadas | 72 | 612 |
| A revisión | 15 | 181 |
| Bloqueadas | 13 | 107 |
| Fraudes confirmados | 6 | 39 |
| Fraudes detectados | 5 | 34 |
| **Tasa de detección** | **83.3%** | **87.2%** |
| Compras buenas bloqueadas | 9 | 35 |
| Fraude que pasó (S/) | 699.00 | 5,790.00 |
| Margen perdido por frenar de más (S/) | 3,166.65 | 14,814.60 |
| **Costo total (S/)** | **3,865.65** | **20,604.60** |

Por compra evaluada, el costo de los errores baja de **S/ 38.66** a **S/ 22.89** (40.8%).


> **Cuidado con la tasa de deteccion de antes.** Se calcula sobre menos de 30 fraudes confirmados, asi que un caso mas o menos la mueve varios puntos. Sirve para ver que el sistema mide, no para sostener que un tramo detecta mejor que el otro: para eso hay que alargar el tramo corto con --antes o --cuantas.


Quedan 304 compras sin etiquetar, casi todas recientes: el contracargo todavía no ha llegado o el plazo no ha vencido. Aparecen en el panel como evaluadas pero sin confirmar, que es como se ve una tienda de verdad — los indicadores del mes pasado están completos y los de esta semana se siguen llenando.


---

**Estas compras son simuladas.** El puntaje, la decisión, la explicación y el tiempo de cada una los produjo el modelo real evaluándolas de una en una; lo simulado es el tráfico: qué se compró, cuándo, y cuáles acabaron en contracargo. Sirven para demostrar el sistema y para medir el efecto del cambio de criterio, no como datos de venta. Las genera `app/scripts/simular_historial.py`.
