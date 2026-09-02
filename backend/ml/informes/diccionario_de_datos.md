# Diccionario de datos

Las cuatro variables que mira el modelo, más la etiqueta.

| Columna | Qué representa | Unidad | De dónde sale |
| --- | --- | --- | --- |
| `total_amount` | Monto total del pedido | soles (S/) | Suma de precio × cantidad de cada ítem, calculada por el backend al crear la orden. |
| `high_risk_items_count` | Unidades de categorías de alto riesgo | unidades | Cuenta las unidades cuya categoría está marcada como `is_high_risk` (tarjetas de video, procesadores): componentes caros y de reventa inmediata, que es lo que busca quien usa una tarjeta robada. |
| `checkout_duration_seconds` | Duración del checkout | segundos | Tiempo entre que la persona abre la pantalla de pago y confirma. Lo mide el frontend y viaja con el pedido. Un checkout de pocos segundos sugiere datos de pago ya cargados o automatizados. |
| `is_new_shipping_address` | Dirección de envío nueva | 0 o 1 | Vale 1 si ese cliente nunca antes había enviado a esa dirección. El backend lo resuelve consultando sus pedidos anteriores. |
| `is_fraud` | Etiqueta: el pedido resultó fraudulento | 0 o 1 | En los datos de la tienda, lo que un administrador marcó tras revisar el pedido. En el conjunto sintético, la clase con la que se generó. |
