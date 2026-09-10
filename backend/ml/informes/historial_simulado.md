# Historial simulado de la tienda

8000 compras repartidas entre el 01/01/2026 y el 07/09/2026, evaluadas una por una por el modelo que está en producción.

El tramo antiguo decide con una regla fija sin modelo (bloquear si el monto pasa de S/ 1,500 y la dirección es nueva; revisar si pasa de ese monto o lleva 2 o más artículos de alto riesgo); el nuevo, con el modelo y los umbrales que el entrenamiento eligió minimizando el costo en soles (0.15 / 0.9). El tráfico se genera igual en los dos: lo único que cambia es el criterio de decisión.

## Los tres indicadores

Son los que mide la tesis. El corte es la entrada del modelo; a la izquierda, cómo operaba la tienda antes.

El reparto de compras entre los dos tramos no sigue al calendario, y conviene decirlo en vez de dejar que se deduzca del gráfico. Las tasas se calculan solo sobre los fraudes ya confirmados, y en el tramo nuevo —que son semanas, no meses— muchos contracargos aún no han llegado: hace falta más tráfico para terminar con la misma cantidad de casos comprobados. Por eso el tramo nuevo lleva más compras y mayor densidad diaria. Lo que se iguala no son las compras, sino los casos sobre los que se puede medir.

Las dos tasas de arriba se dividen entre los fraudes confirmados: son la exhaustividad del modelo. Los indicadores DTF y NFND que enseña el panel dividen entre el total de transacciones, así que sus valores son mucho menores —su techo es la propia tasa de fraude de la tienda— y no hay que confundir unos con otros.

| Indicador | Antes | Después | Debe |
| :--- | ---: | ---: | :---: |
| Tasa de fraudes detectados | 77.6% | **91.7%** | subir |
| Tasa de fraude no detectado | 22.4% | **8.3%** | bajar |
| Tiempo de detección | 4.5 h | **1.5 ms** | bajar |

El tiempo de detección no compara dos clasificadores: compara **no tener detector** con tenerlo. Antes del modelo la regla fija solo levantaba la mano y quien decidía era una persona, cuando le llegaba el turno en la cola de revisión; ese es el tiempo de la izquierda. El de la derecha lo cronometra el propio servicio al puntuar cada compra, una por una, dentro de la petición que crea el pedido.

## Las cuentas

4000 cuentas con nombres, teléfonos y correos como los de cualquier cliente de Trujillo (@gmail.com, @outlook.es, @hotmail.com, @yahoo.com). 5 de ellas son administradores —personal de la tienda, se ven en Panel → Usuarios con su rol y no compran— y las otras 3995 son los clientes entre los que se reparten las compras: la mayoría compra una sola vez, unos pocos son habituales con nueve pedidos.

## El detalle

| | Antes | Después |
| :--- | ---: | ---: |
| Compras evaluadas | 6772 | 1228 |
| Aprobadas | 4627 | 394 |
| A revisión | 1474 | 731 |
| Bloqueadas | 671 | 103 |
| Fraudes confirmados | 576 | 72 |
| Fraudes detectados | 447 | 66 |
| **Tasa de detección** | **77.6%** | **91.7%** |
| Compras buenas bloqueadas | 332 | 25 |
| Fraude que pasó (S/) | 103,165.00 | 4,022.00 |
| Margen perdido por frenar de más (S/) | 125,721.45 | 11,187.90 |
| **Costo total (S/)** | **228,886.45** | **15,209.90** |

Por compra evaluada, el costo de los errores baja de **S/ 33.80** a **S/ 12.39** (63.4%).


Quedan 691 compras sin etiquetar, casi todas recientes: el contracargo todavía no ha llegado o el plazo no ha vencido. Aparecen en el panel como evaluadas pero sin confirmar, que es como se ve una tienda de verdad — los indicadores del mes pasado están completos y los de esta semana se siguen llenando.


Las compras que el sistema dejó pasar llevan además datos de cobro simulados —medio de pago, cuatro últimos dígitos y titular—, con la misma forma que los que deja un pago real. En una parte de ellas el titular no coincide con el de la cuenta: es la señal más común de tarjeta robada, y ninguna de las cuatro variables del modelo la ve, así que solo puede verla la persona que revisa.


---

**Estas compras son simuladas.** El puntaje, la decisión, la explicación y el tiempo de cada una los produjo el modelo real evaluándolas de una en una; lo simulado es el tráfico: qué se compró, cuándo, y cuáles acabaron en contracargo. Sirven para demostrar el sistema y para medir el efecto del cambio de criterio, no como datos de venta. Las genera `app/scripts/simular_historial.py`.
