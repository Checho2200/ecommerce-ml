# Compras de prueba: qué decidía cada sistema

Diez compras simuladas, elegidas entre las que cambiaron de decisión y
los extremos de riesgo. Ninguno de los dos modelos vio estas
transacciones durante su entrenamiento.

| # | Monto | Alto riesgo | Checkout | Dirección | ¿Fue fraude? | Antes | Después |
| ---: | ---: | ---: | ---: | :---: | :---: | :--- | :--- |
| 1 | S/ 231 | 2 | 50 s | nueva | **sí** | REVIEW (60%) | BLOCKED (95%) |
| 2 | S/ 325 | 3 | 56 s | nueva | **sí** | REVIEW (70%) | BLOCKED (95%) |
| 3 | S/ 4,291 | 1 | 2.5 min | conocida | no | REVIEW (69%) | BLOCKED (91%) |
| 4 | S/ 1,441 | 2 | 2.7 min | nueva | **sí** | BLOCKED (84%) | REVIEW (90%) |
| 5 | S/ 15,650 | 1 | 11 s | conocida | no | BLOCKED (97%) | REVIEW (90%) |
| 6 | S/ 1,052 | 3 | 33 s | conocida | no | BLOCKED (94%) | REVIEW (90%) |
| 7 | S/ 4,012 | 3 | 7 s | nueva | **sí** | BLOCKED (100%) | BLOCKED (100%) |
| 8 | S/ 19,957 | 4 | 27 s | nueva | **sí** | BLOCKED (100%) | BLOCKED (100%) |
| 9 | S/ 46 | 0 | 6.9 min | conocida | no | APPROVED (2%) | APPROVED (2%) |
| 10 | S/ 46 | 1 | 1.3 min | conocida | no | APPROVED (3%) | APPROVED (2%) |

## La explicación que ve el administrador

Para la compra de S/ 4,012 con 3 artículos de alto riesgo:

**Antes:**

> Riesgo medio de fraude detectado por IA. Se requiere revisión.

*La misma frase para todos los pedidos de ese nivel de riesgo.*

**Después:**

> Riesgo medio (85%); requiere revisión manual. Lo que pesó en contra: monto de S/ 4,012.04, 3 artículos de alto riesgo, checkout de 7 s.

*Los factores son los de este pedido en concreto, calculados con los valores SHAP del propio modelo.*

