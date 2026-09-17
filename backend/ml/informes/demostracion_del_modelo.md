# El modelo decidiendo: cuatro compras

Cuatro compras hechas contra la API real de la tienda (`POST /api/v1/orders`), con el recorrido completo: reserva de inventario, evaluación del modelo LightGBM, decisión, cobro y estado final del pedido. Ninguno de los puntajes de abajo está escrito a mano; son los que devolvió el modelo cargado en ese momento.

| Caso | Monto | Antigüedad | Dirección | Checkout | Puntaje | Decisión | Estado final |
| :--- | ---: | ---: | :--- | ---: | ---: | :---: | :--- |
| Compra normal, aprobada y pagada | S/ 149.00 | 120 d | nueva | 150 s | 26.3% | APPROVED | **COMPLETED** |
| Compra retenida por el modelo | S/ 499.00 | 1 d | nueva | 60 s | 56.4% | REVIEW | **FRAUD_REVIEW** |
| Compra bloqueada antes de cobrar | S/ 2,799.00 | 0 d | nueva | 22 s | 98.9% | BLOCKED | **REJECTED** |
| Aprobada por el modelo, rechazada por el banco | S/ 149.00 | 120 d | conocida | 150 s | 21.3% | APPROVED | **CANCELLED** |

---

## Compra normal, aprobada y pagada

Una clienta de hace cuatro meses comprando algo barato y tomándose su tiempo. Es el perfil que el modelo tiene que dejar pasar sin fricción: si a esta compra le pusiera una traba, la tienda perdería clientes legítimos y el sistema no serviría.

- **Quién compra:** Rosa Medina Vargas · cuenta de 120 día(s)
- **Producto:** TP-Link TL-SG108 Gigabit · S/ 149.00
- **Tiempo en el checkout:** 150 segundos
- **Puntaje del modelo:** 26.3% → **APPROVED**
- **Estado al crearse:** PENDING
- **Cobro:** aprobado · código `00`
- **Referencia del cobro:** `SIM-20260917112045-E6DD`
- **Tarjeta guardada:** •••• 0258 · titular «Rosa Medina Vargas»
- **Estado final:** **COMPLETED**
- **Stock del producto:** 25 → 24

> Riesgo bajo (26%). Lo que pesó a favor: cuenta de 4 meses, 0 artículos de alto riesgo, monto de S/ 149.00.


## Compra retenida por el modelo

Cuenta abierta ayer, dirección estrenada y un monto que ya duele. No hay nada concluyente, y por eso no se bloquea: se cobra y se para antes de enviar. Al revisor le queda delante el dato que no existía hasta que se pagó —el titular de la tarjeta— y aquí no coincide con el dueño de la cuenta.

- **Quién compra:** Kevin Salas Ortiz · cuenta de 1 día(s)
- **Producto:** Logitech G733 Lightspeed · S/ 499.00
- **Tiempo en el checkout:** 60 segundos
- **Puntaje del modelo:** 56.4% → **REVIEW**
- **Estado al crearse:** PENDING
- **Cobro:** aprobado · código `00`
- **Referencia del cobro:** `SIM-20260917112046-2E04`
- **Tarjeta guardada:** •••• 0258 · titular «M. ANGELA TORRES P»
- **Estado final:** **FRAUD_REVIEW**
- **Stock del producto:** 12 → 11

> Riesgo medio (56%); requiere revisión manual. Lo que pesó en contra: checkout de 1.0 min, cuenta de ayer, dirección de envío nueva.


## Compra bloqueada antes de cobrar

Cuenta creada hace un momento, dirección nueva, componente caro de reventa inmediata y checkout resuelto en veintidós segundos. Las cinco variables apuntan al mismo sitio. El pedido nace rechazado: no se le pide la tarjeta a nadie y el inventario vuelve en el acto.

- **Quién compra:** Luis Paredes Ruiz · cuenta de 0 día(s)
- **Producto:** NVIDIA RTX 4070 Super · S/ 2,799.00 · categoría de alto riesgo
- **Tiempo en el checkout:** 22 segundos
- **Puntaje del modelo:** 98.9% → **BLOCKED**
- **Estado al crearse:** REJECTED
- **Cobro:** no llegó a pedirse
- **Estado final:** **REJECTED**
- **Stock del producto:** 4 → 4

> Riesgo alto (99%); pedido rechazado. Lo que pesó en contra: checkout de 22 s, cuenta abierta hoy, monto de S/ 2,799.00.


## Aprobada por el modelo, rechazada por el banco

La misma clienta y la misma compra del primer caso, con una tarjeta sin fondos. El modelo la aprueba —no hay nada sospechoso— y el cobro no prospera. El pedido se cancela y el stock vuelve a la tienda. Sirve para separar dos cosas que se confunden: que el sistema antifraude diga que no, y que el banco diga que no.

- **Quién compra:** Rosa Medina Vargas · cuenta de 120 día(s)
- **Producto:** TP-Link TL-SG108 Gigabit · S/ 149.00
- **Tiempo en el checkout:** 150 segundos
- **Puntaje del modelo:** 21.3% → **APPROVED**
- **Estado al crearse:** PENDING
- **Cobro:** rechazado · código `51` · Fondos insuficientes.
- **Estado final:** **CANCELLED**
- **Stock del producto:** 24 → 24

> Riesgo bajo (21%). Lo que pesó a favor: cuenta de 4 meses, dirección de envío conocida, 0 artículos de alto riesgo.


*Generado por `app/scripts/demostracion.py`. Las compras y las cuentas son de demostración; las decisiones del modelo y los estados del pedido son los que produjo el sistema.*
