# Historial simulado de la tienda

1400 compras repartidas entre el 26/06/2026 y el 08/09/2026, evaluadas una por una por el modelo que está en producción.

El tramo antiguo decide con una regla fija sin modelo (bloquear si el monto pasa de S/ 1,500 y la dirección es nueva; revisar si pasa de ese monto o lleva 2 o más artículos de alto riesgo); el nuevo, con el modelo y los umbrales que el entrenamiento eligió minimizando el costo en soles (0.35 / 0.8). El tráfico se genera igual en los dos: lo único que cambia es el criterio de decisión.

| | Antes | Después |
| :--- | ---: | ---: |
| Compras evaluadas | 700 | 700 |
| Aprobadas | 457 | 472 |
| A revisión | 169 | 144 |
| Bloqueadas | 74 | 84 |
| Fraudes confirmados | 51 | 42 |
| Fraudes detectados | 41 | 37 |
| **Tasa de detección** | **80.4%** | **88.1%** |
| Compras buenas bloqueadas | 37 | 28 |
| Fraude que pasó (S/) | 9,326.00 | 3,812.00 |
| Margen perdido por frenar de más (S/) | 14,032.20 | 9,998.40 |
| **Costo total (S/)** | **23,358.20** | **13,810.40** |

Por compra evaluada, el costo de los errores baja de **S/ 33.37** a **S/ 19.73** (40.9%).


Quedan 240 compras sin etiquetar, casi todas recientes: el contracargo todavía no ha llegado o el plazo no ha vencido. Aparecen en el panel como evaluadas pero sin confirmar, que es como se ve una tienda de verdad — los indicadores del mes pasado están completos y los de esta semana se siguen llenando.


Las compras que el sistema dejó pasar llevan además datos de cobro simulados —medio de pago, cuatro últimos dígitos y titular—, con la misma forma que los que deja un pago real. En una parte de ellas el titular no coincide con el de la cuenta: es la señal más común de tarjeta robada, y ninguna de las cuatro variables del modelo la ve, así que solo puede verla la persona que revisa.


---

**Estas compras son simuladas.** El puntaje, la decisión, la explicación y el tiempo de cada una los produjo el modelo real evaluándolas de una en una; lo simulado es el tráfico: qué se compró, cuándo, y cuáles acabaron en contracargo. Sirven para demostrar el sistema y para medir el efecto del cambio de criterio, no como datos de venta. Las genera `app/scripts/simular_historial.py`.
