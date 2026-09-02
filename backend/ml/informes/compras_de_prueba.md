# Compras de prueba: qué decidía cada sistema

Diez compras simuladas, elegidas entre las que cambiaron de decisión y
los extremos de riesgo. Ninguno de los dos modelos vio estas
transacciones durante su entrenamiento.

| # | Monto | Alto riesgo | Checkout | Dirección | ¿Fue fraude? | Antes | Después |
| ---: | ---: | ---: | ---: | :---: | :---: | :--- | :--- |
| 1 | S/ 799 | 2 | 1.4 min | nueva | no | BLOCKED (86%) | REVIEW (85%) |
| 2 | S/ 2,942 | 1 | 1.4 min | nueva | **sí** | BLOCKED (90%) | REVIEW (85%) |
| 3 | S/ 2,741 | 3 | 2.4 min | conocida | no | BLOCKED (86%) | REVIEW (84%) |
| 4 | S/ 447 | 2 | 57 s | nueva | no | BLOCKED (83%) | REVIEW (84%) |
| 5 | S/ 452 | 2 | 1.0 min | nueva | no | BLOCKED (80%) | REVIEW (84%) |
| 6 | S/ 1,833 | 2 | 1.5 min | conocida | no | BLOCKED (86%) | REVIEW (84%) |
| 7 | S/ 5,069 | 5 | 25 s | nueva | **sí** | BLOCKED (100%) | BLOCKED (99%) |
| 8 | S/ 12,048 | 5 | 13 s | nueva | **sí** | BLOCKED (100%) | BLOCKED (99%) |
| 9 | S/ 40 | 0 | 10.2 min | conocida | no | APPROVED (2%) | APPROVED (5%) |
| 10 | S/ 51 | 1 | 6.1 min | nueva | no | APPROVED (3%) | APPROVED (6%) |

## La explicación que ve el administrador

Para la compra de S/ 5,069 con 5 artículos de alto riesgo:

**Antes:**

> Alto riesgo de fraude detectado por IA. Orden rechazada.

*La misma frase para todos los pedidos de ese nivel de riesgo.*

**Después:**

> Riesgo alto (99%); pedido rechazado. Lo que pesó en contra: 5 artículos de alto riesgo, checkout de 25 s, monto de S/ 5,069.19.

*Los factores son los de este pedido en concreto, calculados con los valores SHAP del propio modelo.*

