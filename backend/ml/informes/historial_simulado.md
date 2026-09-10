# Historial simulado de la tienda

1000 compras repartidas entre el 01/01/2026 y el 09/09/2026, evaluadas una por una por el modelo que está en producción.

El tramo antiguo decide con una regla fija sin modelo (bloquear si el monto pasa de S/ 1,500 y la dirección es nueva; revisar si pasa de ese monto o lleva 2 o más artículos de alto riesgo); el nuevo, con el modelo y los umbrales que el entrenamiento eligió minimizando el costo en soles (0.35 / 0.8). El tráfico se genera igual en los dos: lo único que cambia es el criterio de decisión.

## Los tres indicadores

Son los que mide la tesis. El corte es la entrada del modelo; a la izquierda, cómo operaba la tienda antes.

Los dos tramos llevan la misma cantidad de compras a propósito. Las tasas se calculan solo sobre los fraudes ya confirmados, y el tramo nuevo es mucho más corto en calendario: repartir las compras proporcionalmente a los días lo dejaría con tan pocos casos resueltos que su tasa se movería varios puntos por un caso más. Igualar la muestra es lo que permite comparar; a cambio, la densidad diaria del tramo nuevo es mayor, y conviene decirlo en vez de dejar que se deduzca del gráfico.

| Indicador | Antes | Después | Debe |
| :--- | ---: | ---: | :---: |
| Tasa de fraudes detectados | 68.8% | **77.4%** | subir |
| Tasa de fraude no detectado | 31.2% | **22.6%** | bajar |
| Tiempo de detección | 4.4 h | **1.7 ms** | bajar |

El tiempo de detección no compara dos clasificadores: compara **no tener detector** con tenerlo. Antes del modelo la regla fija solo levantaba la mano y quien decidía era una persona, cuando le llegaba el turno en la cola de revisión; ese es el tiempo de la izquierda. El de la derecha lo cronometra el propio servicio al puntuar cada compra, una por una, dentro de la petición que crea el pedido.

## Las cuentas

500 cuentas con nombres y teléfonos de Trujillo, todas con el dominio `@cliente.simulado` para que nadie las confunda con clientes reales y para que `--limpiar` sepa cuáles retirar. 5 de ellas son administradores —personal de la tienda, se ven en Panel → Usuarios con su rol y no compran— y las otras 495 son los clientes entre los que se reparten las compras: la mayoría compra una sola vez, unos pocos son habituales con nueve pedidos.

## El detalle

| | Antes | Después |
| :--- | ---: | ---: |
| Compras evaluadas | 500 | 500 |
| Aprobadas | 333 | 355 |
| A revisión | 117 | 99 |
| Bloqueadas | 50 | 46 |
| Fraudes confirmados | 32 | 31 |
| Fraudes detectados | 22 | 24 |
| **Tasa de detección** | **68.8%** | **77.4%** |
| Compras buenas bloqueadas | 29 | 15 |
| Fraude que pasó (S/) | 6,306.00 | 4,656.00 |
| Margen perdido por frenar de más (S/) | 9,454.05 | 6,246.30 |
| **Costo total (S/)** | **15,760.05** | **10,902.30** |

Por compra evaluada, el costo de los errores baja de **S/ 31.52** a **S/ 21.80** (30.8%).


Quedan 178 compras sin etiquetar, casi todas recientes: el contracargo todavía no ha llegado o el plazo no ha vencido. Aparecen en el panel como evaluadas pero sin confirmar, que es como se ve una tienda de verdad — los indicadores del mes pasado están completos y los de esta semana se siguen llenando.


Las compras que el sistema dejó pasar llevan además datos de cobro simulados —medio de pago, cuatro últimos dígitos y titular—, con la misma forma que los que deja un pago real. En una parte de ellas el titular no coincide con el de la cuenta: es la señal más común de tarjeta robada, y ninguna de las cuatro variables del modelo la ve, así que solo puede verla la persona que revisa.


---

**Estas compras son simuladas.** El puntaje, la decisión, la explicación y el tiempo de cada una los produjo el modelo real evaluándolas de una en una; lo simulado es el tráfico: qué se compró, cuándo, y cuáles acabaron en contracargo. Sirven para demostrar el sistema y para medir el efecto del cambio de criterio, no como datos de venta. Las genera `app/scripts/simular_historial.py`.
