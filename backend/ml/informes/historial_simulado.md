# Historial simulado de la tienda

1000 compras repartidas entre el 01/01/2026 y el 10/09/2026, evaluadas una por una por el modelo que está en producción.

El tramo antiguo decide con una regla fija sin modelo (bloquear si el monto pasa de S/ 1,500 y la dirección es nueva; revisar si pasa de ese monto o lleva 2 o más artículos de alto riesgo); el nuevo, con el modelo y los umbrales que el entrenamiento eligió minimizando el costo en soles (0.2 / 0.9). El tráfico se genera igual en los dos: lo único que cambia es el criterio de decisión.

## Los tres indicadores

Son los que mide la tesis. El corte es la entrada del modelo; a la izquierda, cómo operaba la tienda antes.

El reparto de compras entre los dos tramos no sigue al calendario, y conviene decirlo en vez de dejar que se deduzca del gráfico. Las tasas se calculan solo sobre los fraudes ya confirmados, y en el tramo nuevo —que son semanas, no meses— muchos contracargos aún no han llegado: hace falta más tráfico para terminar con la misma cantidad de casos comprobados. Por eso el tramo nuevo lleva más compras y mayor densidad diaria. Lo que se iguala no son las compras, sino los casos sobre los que se puede medir.

Las dos tasas de arriba se dividen entre los fraudes confirmados: son la exhaustividad del modelo. Los indicadores DTF y NFND que enseña el panel dividen entre el total de transacciones, así que sus valores son mucho menores —su techo es la propia tasa de fraude de la tienda— y no hay que confundir unos con otros.

| Indicador | Antes | Después | Debe |
| :--- | ---: | ---: | :---: |
| Tasa de fraudes detectados | 83.3% | **94.9%** | subir |
| Tasa de fraude no detectado | 16.7% | **5.1%** | bajar |
| Tiempo de detección | 4.3 h | **1.6 ms** | bajar |

El tiempo de detección no compara dos clasificadores: compara **no tener detector** con tenerlo. Antes del modelo la regla fija solo levantaba la mano y quien decidía era una persona, cuando le llegaba el turno en la cola de revisión; ese es el tiempo de la izquierda. El de la derecha lo cronometra el propio servicio al puntuar cada compra, una por una, dentro de la petición que crea el pedido.

## Las cuentas

500 cuentas con nombres, teléfonos y correos como los de cualquier cliente de Trujillo (@gmail.com, @outlook.es, @hotmail.com, @yahoo.com). 5 de ellas son administradores —personal de la tienda, se ven en Panel → Usuarios con su rol y no compran— y las otras 495 son los clientes entre los que se reparten las compras: la mayoría compra una sola vez, unos pocos son habituales con nueve pedidos.

## El detalle

| | Antes | Después |
| :--- | ---: | ---: |
| Compras evaluadas | 450 | 550 |
| Aprobadas | 299 | 274 |
| A revisión | 108 | 226 |
| Bloqueadas | 43 | 50 |
| Fraudes confirmados | 30 | 39 |
| Fraudes detectados | 25 | 37 |
| **Tasa de detección** | **83.3%** | **94.9%** |
| Compras buenas bloqueadas | 24 | 14 |
| Fraude que pasó (S/) | 2,763.00 | 1,598.00 |
| Margen perdido por frenar de más (S/) | 8,503.80 | 5,767.95 |
| **Costo total (S/)** | **11,266.80** | **7,365.95** |

Por compra evaluada, el costo de los errores baja de **S/ 25.04** a **S/ 13.39** (46.5%).


Quedan 183 compras sin etiquetar, casi todas recientes: el contracargo todavía no ha llegado o el plazo no ha vencido. Aparecen en el panel como evaluadas pero sin confirmar, que es como se ve una tienda de verdad — los indicadores del mes pasado están completos y los de esta semana se siguen llenando.


Las compras que el sistema dejó pasar llevan además datos de cobro simulados —medio de pago, cuatro últimos dígitos y titular—, con la misma forma que los que deja un pago real. En una parte de ellas el titular no coincide con el de la cuenta: es la señal más común de tarjeta robada, y ninguna de las cuatro variables del modelo la ve, así que solo puede verla la persona que revisa.


---

**Estas compras son simuladas.** El puntaje, la decisión, la explicación y el tiempo de cada una los produjo el modelo real evaluándolas de una en una; lo simulado es el tráfico: qué se compró, cuándo, y cuáles acabaron en contracargo. Sirven para demostrar el sistema y para medir el efecto del cambio de criterio, no como datos de venta. Las genera `app/scripts/simular_historial.py`.
