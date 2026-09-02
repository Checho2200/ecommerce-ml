# Compras simuladas en la tienda

37 compras hechas contra la API real de la tienda (`POST /api/v1/orders`), con el mismo recorrido que haría un cliente: descuento de stock, evaluación del modelo, decisión y registro.

- Aprobadas: **25**
- A revisión manual: **5**
- Bloqueadas: **7**

| # | Perfil | Monto | Checkout | Puntaje | Decisión | Estado del pedido |
| ---: | :--- | ---: | ---: | ---: | :---: | :--- |
| 1 | corriente | S/ 149.00 | 9.1 min | 8% | APPROVED | PENDING |
| 2 | equipo completo | S/ 8,395.00 | 13.1 min | 88% | BLOCKED | REJECTED |
| 3 | corriente | S/ 468.00 | 7.4 min | 13% | APPROVED | PENDING |
| 4 | sospechosa | S/ 12,393.00 | 37 s | 99% | BLOCKED | REJECTED |
| 5 | corriente | S/ 1,298.00 | 3.1 min | 31% | APPROVED | PENDING |
| 6 | equipo completo | S/ 9,095.00 | 7.4 min | 78% | REVIEW | FRAUD_REVIEW |
| 7 | corriente | S/ 1,028.00 | 8.8 min | 14% | APPROVED | PENDING |
| 8 | equipo completo | S/ 7,996.00 | 14.6 min | 70% | REVIEW | FRAUD_REVIEW |
| 9 | corriente | S/ 189.00 | 8.8 min | 12% | APPROVED | PENDING |
| 11 | corriente | S/ 1,248.00 | 2.1 min | 38% | REVIEW | FRAUD_REVIEW |
| 12 | corriente | S/ 329.00 | 4.1 min | 15% | APPROVED | PENDING |
| 13 | corriente | S/ 1,198.00 | 8.5 min | 14% | APPROVED | PENDING |
| 14 | corriente | S/ 499.00 | 5.5 min | 12% | APPROVED | PENDING |
| 15 | corriente | S/ 329.00 | 9.7 min | 11% | APPROVED | PENDING |
| 16 | sospechosa | S/ 5,596.00 | 41 s | 99% | BLOCKED | REJECTED |
| 17 | corriente | S/ 478.00 | 6.6 min | 12% | APPROVED | PENDING |
| 18 | corriente | S/ 649.00 | 8.0 min | 13% | APPROVED | PENDING |
| 19 | corriente | S/ 1,048.00 | 7.3 min | 14% | APPROVED | PENDING |
| 20 | corriente | S/ 1,198.00 | 6.7 min | 14% | APPROVED | PENDING |
| 21 | corriente | S/ 349.00 | 9.5 min | 11% | APPROVED | PENDING |
| 22 | corriente | S/ 748.00 | 8.5 min | 13% | APPROVED | PENDING |
| 23 | corriente | S/ 189.00 | 5.1 min | 12% | APPROVED | PENDING |
| 25 | corriente | S/ 798.00 | 6.6 min | 13% | APPROVED | PENDING |
| 26 | corriente | S/ 988.00 | 5.7 min | 13% | APPROVED | PENDING |
| 27 | corriente | S/ 399.00 | 2.4 min | 15% | APPROVED | PENDING |
| 28 | corriente | S/ 799.00 | 5.9 min | 14% | APPROVED | PENDING |
| 29 | corriente | S/ 399.00 | 8.3 min | 13% | APPROVED | PENDING |
| 30 | corriente | S/ 279.00 | 5.1 min | 12% | APPROVED | PENDING |
| 31 | sospechosa | S/ 9,194.00 | 18 s | 98% | BLOCKED | REJECTED |
| 32 | corriente | S/ 518.00 | 6.2 min | 12% | APPROVED | PENDING |
| 33 | equipo completo | S/ 4,097.00 | 3.1 min | 82% | BLOCKED | REJECTED |
| 35 | corriente | S/ 699.00 | 6.6 min | 13% | APPROVED | PENDING |
| 36 | equipo completo | S/ 2,398.00 | 4.2 min | 56% | REVIEW | FRAUD_REVIEW |
| 37 | equipo completo | S/ 7,495.00 | 11.7 min | 71% | REVIEW | FRAUD_REVIEW |
| 38 | sospechosa | S/ 4,796.00 | 16 s | 99% | BLOCKED | REJECTED |
| 39 | sospechosa | S/ 5,796.00 | 10 s | 98% | BLOCKED | REJECTED |
| 40 | corriente | S/ 1,028.00 | 4.5 min | 17% | APPROVED | PENDING |

## Explicaciones que quedaron registradas

**Compra 2** (S/ 8,395.00, BLOCKED):

> Riesgo alto (88%); pedido rechazado. Lo que pesó en contra: 5 artículos de alto riesgo, monto de S/ 8,395.00, dirección de envío nueva.

**Compra 4** (S/ 12,393.00, BLOCKED):

> Riesgo alto (99%); pedido rechazado. Lo que pesó en contra: 7 artículos de alto riesgo, monto de S/ 12,393.00, checkout de 37 s.

**Compra 6** (S/ 9,095.00, REVIEW):

> Riesgo medio (78%); requiere revisión manual. Lo que pesó en contra: 5 artículos de alto riesgo, monto de S/ 9,095.00.


*Compras generadas por `app/scripts/simular_compras.py`. Son ficticias: sirven para demostrar el funcionamiento del sistema, no como datos de venta.*
