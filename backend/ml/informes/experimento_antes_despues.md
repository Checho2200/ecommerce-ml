# Antes y después de mejorar la detección de fraude

Sobre 4,000 compras simuladas que ninguno de los dos modelos vio durante su entrenamiento (7.2 % fraudulentas). Los dos modelos eligen sus umbrales con el mismo método y sobre los mismos datos, para que la comparación no premie a uno por algo que el otro no tuvo.

| Configuración | Umbrales | AUC-PR | Precisión | Exhaustividad | F1 | Fraudes aprobados | Legítimas bloqueadas | A revisión | Pérdida (S/) |
| --- | :---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A. Sistema original | 0.3 / 0.7 | 0.8313 | 0.6402 | 0.8345 | 0.7246 | 18 | 136 | 14.4 % | 73,839.39 |
| B. Modelo anterior + umbrales por costo | 0.35 / 0.9 | 0.8313 | 0.8559 | 0.6552 | 0.7422 | 20 | 32 | 14.8 % | 60,118.91 |
| C. Sistema actual | 0.45 / 0.9 | 0.8924 | 0.9095 | 0.7276 | 0.8084 | 19 | 21 | 7.3 % | 39,028.37 |

## El resultado en una línea

La pérdida sobre esas compras baja de **S/ 73,839.39** a **S/ 39,028.37**: un **47.1 % menos**, S/ 34,811.02 que la tienda deja de perder.

## Pero conviene leer de dónde viene

El modelo reentrenado **distingue mejor** el fraude: el AUC-PR sube de 0.8313 a 0.8924.

El desglose lo confirma:

- **S/ 13,720.48** salen de dejar de elegir los umbrales a ojo (fila A → B: el mismo modelo, distinto criterio de decisión).
- **S/ 21,090.54** salen de reentrenar (fila B → C). Y ni siquiera es porque acierte más: es que sus puntajes se reparten distinto y admiten un corte más barato.

## El intercambio que se está haciendo

El sistema actual deja pasar **1 fraudes más** (18 → 19) y a cambio deja de frenar **115 compras legítimas** (136 → 21).

No es un descuido, es la decisión que toma el criterio de costo: bloquear una compra buena cuesta el margen de esa venta, y frenar 79 de ellas salía más caro que los fraudes adicionales que se cuelan. Si para la tienda el fraude pesara más que la venta perdida, basta con subir `cargo_por_contracargo` o bajar `margen_bruto` en `ml/evaluacion.py` y los umbrales se recolocan solos.

## Lo que este experimento no mide

Tres mejoras del trabajo no aparecen en la tabla porque no son cuestión de acertar más:

- La **explicación por pedido**: antes, una frase idéntica para todos; ahora, los factores concretos de esa compra. Se ve en `compras_de_prueba.md`.
- El **etiquetado en dos sentidos**, que es lo que permite calcular la precisión del modelo con datos de la tienda.
- Las **guardas del reentrenamiento**, que impiden publicar un modelo peor o un resultado sospechosamente perfecto.

Y una advertencia: estas compras son simuladas. El experimento demuestra que el método funciona y cuánto rinde bajo los supuestos de costo declarados, no lo que la tienda ahorrará con clientes reales.
