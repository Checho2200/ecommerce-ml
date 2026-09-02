# Antes y después de mejorar la detección de fraude

Sobre 4,000 compras simuladas que ninguno de los dos modelos vio durante su entrenamiento (8.1 % fraudulentas). Los dos modelos eligen sus umbrales con el mismo método y sobre los mismos datos, para que la comparación no premie a uno por algo que el otro no tuvo.

| Configuración | Umbrales | AUC-PR | Precisión | Exhaustividad | F1 | Fraudes aprobados | Legítimas bloqueadas | A revisión | Pérdida (S/) |
| --- | :---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A. Sistema original | 0.3 / 0.7 | 0.7690 | 0.6453 | 0.7446 | 0.6914 | 47 | 133 | 14.4 % | 121,024.98 |
| B. Modelo anterior + umbrales por costo | 0.35 / 0.9 | 0.7690 | 0.8696 | 0.6154 | 0.7207 | 51 | 30 | 14.5 % | 105,086.03 |
| C. Sistema actual | 0.4 / 0.85 | 0.7688 | 0.7970 | 0.6523 | 0.7174 | 53 | 54 | 11.6 % | 95,657.40 |

## El resultado en una línea

La pérdida sobre esas compras baja de **S/ 121,024.98** a **S/ 95,657.40**: un **21.0 % menos**, S/ 25,367.58 que la tienda deja de perder.

## Pero conviene leer de dónde viene

El modelo reentrenado **no distingue mejor** el fraude que el anterior: el AUC-PR pasa de 0.7690 a 0.7688, que a efectos prácticos es lo mismo. Los dos ordenan las compras por riesgo casi igual de bien. Toda la mejora está en **qué se hace con ese puntaje**, no en el puntaje.

El desglose lo confirma:

- **S/ 15,938.95** salen de dejar de elegir los umbrales a ojo (fila A → B: el mismo modelo, distinto criterio de decisión).
- **S/ 9,428.63** salen de reentrenar (fila B → C). Y ni siquiera es porque acierte más: es que sus puntajes se reparten distinto y admiten un corte más barato.

## El intercambio que se está haciendo

El sistema actual deja pasar **6 fraudes más** (47 → 53) y a cambio deja de frenar **79 compras legítimas** (133 → 54).

No es un descuido, es la decisión que toma el criterio de costo: bloquear una compra buena cuesta el margen de esa venta, y frenar 79 de ellas salía más caro que los fraudes adicionales que se cuelan. Si para la tienda el fraude pesara más que la venta perdida, basta con subir `cargo_por_contracargo` o bajar `margen_bruto` en `ml/evaluacion.py` y los umbrales se recolocan solos.

## Lo que este experimento no mide

Tres mejoras del trabajo no aparecen en la tabla porque no son cuestión de acertar más:

- La **explicación por pedido**: antes, una frase idéntica para todos; ahora, los factores concretos de esa compra. Se ve en `compras_de_prueba.md`.
- El **etiquetado en dos sentidos**, que es lo que permite calcular la precisión del modelo con datos de la tienda.
- Las **guardas del reentrenamiento**, que impiden publicar un modelo peor o un resultado sospechosamente perfecto.

Y una advertencia: estas compras son simuladas. El experimento demuestra que el método funciona y cuánto rinde bajo los supuestos de costo declarados, no lo que la tienda ahorrará con clientes reales.
