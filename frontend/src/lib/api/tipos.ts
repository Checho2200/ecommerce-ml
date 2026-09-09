/**
 * Las formas que devuelve el backend.
 *
 * Se declaran aquí y no junto a cada recurso porque varias pantallas las
 * comparten: un `OrderResponse` lo usan el checkout, el panel y el historial
 * del cliente.
 */

export interface ProductResponse {
  id: string;
  name: string;
  description: string | null;
  price: number;
  discount_price: number | null;
  stock: number;
  image_url: string | null;
  category_id: number;
  category: CategoryResponse | null;
  is_active: boolean;
  created_at: string;
}

export interface ProductCreate {
  name: string;
  description?: string;
  price: number;
  discount_price?: number | null;
  stock: number;
  image_url?: string;
  category_id: number;
  is_active?: boolean;
}

export interface CategoryResponse {
  id: number;
  name: string;
  slug: string;
  is_high_risk: boolean;
  image_url: string | null;
  // Nulo en las categorías raíz; el id del padre en las subcategorías.
  parent_id: number | null;
  // Productos activos que cuelgan directamente de la categoría.
  product_count: number;
}

export interface OrderResponse {
  id: string;
  user_id: string;
  total_amount: number;
  status: string;
  shipping_address: string | null;
  shipping_city: string | null;
  items: OrderItemResponse[];
  fraud_score: number | null;
  fraud_decision: string | null;
  // Por qué el modelo decidió eso, con los factores que más pesaron en este
  // pedido concreto.
  fraud_explanation: string | null;
  fraud_log_id: string | null;
  payment_url?: string;
  created_at: string;
  user_email: string | null;
  user_name: string | null;
  payment_id: string | null;
  payment_method: string | null;
  card_last_four: string | null;
  card_holder: string | null;
  paid_at: string | null;
}

// Quién compró y con qué pagó. Los datos de tarjeta solo existen si hubo
// cobro, y son los cuatro últimos dígitos: el número completo nunca llega a la
// tienda, lo maneja MercadoPago.
export interface OrderItemResponse {
  id: number;
  product_id: string;
  product_name: string | null;
  quantity: number;
  unit_price: number;
}

export interface ProductReviewResponse {
  id: string;
  user_id: string;
  user_name: string;
  product_id: string;
  rating: number;
  comment: string | null;
  created_at: string;
}

export interface FraudLogResponse {
  id: string;
  order_id: string;
  fraud_score: number;
  decision: string;
  risk_level: string | null;
  explanation: string | null;
  // Los valores que el modelo leyó de este pedido. Con ellos y los aportes se
  // puede rehacer la cuenta entera de la decisión.
  feature_vector: Record<string, number> | null;
  // Cuánto empujó cada variable el puntaje de este pedido, en escala logit:
  // positivo hacia fraude, negativo hacia compra legítima.
  contributions: Record<string, number> | null;
  admin_notes: string | null;
  is_actual_fraud: boolean;
  // Nulo mientras nadie lo haya revisado. Es lo que separa "legítimo
  // confirmado" de "todavía sin mirar".
  reviewed_at: string | null;
  detection_time_ms: number | null;
  evaluated_at: string;
}

export interface FraudMetricsResponse {
  total_evaluations: number;
  detected_fraud_rate: number;
  undetected_fraud_rate: number;
  average_detection_time_ms: number;

  // Matriz de confusión sobre los pedidos que un administrador ya revisó.
  reviewed_count: number;
  true_positives: number;
  false_positives: number;
  true_negatives: number;
  false_negatives: number;

  precision: number;
  recall: number;
  f1_score: number;

  // En soles.
  loss_prevented: number;
  loss_absorbed: number;
  revenue_lost: number;
}

/** Un día, una semana o un mes del historial del modelo antifraude. */
/**
 * Las escalas en las que se puede leer el historial.
 *
 * Vive aquí y no en el componente para que el cliente de la API y la pantalla
 * no puedan discrepar: el backend valida esta misma lista y devolvería un 422
 * ante cualquier otra.
 */
export type EscalaDelHistorial =
  | "day"
  | "week"
  | "month"
  | "bimester"
  | "quarter"
  | "semester"
  | "year";

export interface FraudHistoryPeriod {
  // Fecha de inicio en ISO (AAAA-MM-DD): el día, el lunes de la semana o el 1.
  period_start: string;
  evaluations: number;
  // "Pasaron": el modelo las dejó seguir hasta el cobro.
  approved: number;
  // "No pasaron": retenidas antes de llegar a la pasarela de pago.
  in_review: number;
  blocked: number;
  approved_amount: number;
  held_amount: number;
  average_score: number;

  // Los tres indicadores de la tesis, en este período.
  reviewed: number;
  actual_frauds: number;
  detected_frauds: number;
  undetected_frauds: number;
  detection_rate: number | null;
  undetected_rate: number | null;
  // Alertas que resultaron ser compras buenas, y la precisión que sale de
  // ellas. Nula mientras no se haya revisado ninguna alerta del período.
  false_alerts: number;
  precision: number | null;
  average_detection_time_ms: number;
}

export interface FraudHistoryResponse {
  granularity: EscalaDelHistorial;
  // El tramo que estos números cubren de verdad, en ISO (AAAA-MM-DD). No es
  // necesariamente el que se pidió: las fechas se redondean al período que las
  // contiene y una final futura se recorta a hoy. Se enseña en pantalla para
  // que nadie tenga que adivinar sobre qué días está leyendo un porcentaje.
  range_start: string;
  range_end: string;
  periods: FraudHistoryPeriod[];
  total_evaluations: number;
  total_approved: number;
  total_held: number;
  total_reviewed: number;
  total_actual_frauds: number;
  total_detected_frauds: number;
  total_undetected_frauds: number;
  // Nulos mientras no haya ningún fraude confirmado en la ventana: un cero
  // diría "no se detectó nada" y lo cierto es que no hay con qué medirlo.
  total_false_alerts: number;
  detection_rate: number | null;
  undetected_rate: number | null;
  precision: number | null;
  average_detection_time_ms: number;
}

/** Con qué se publicó el modelo que está decidiendo ahora mismo. */
export interface FraudModelInfo {
  loaded: boolean;
  trained_at: string | null;
  data_source: string | null;
  approve_below: number;
  block_above: number;
  average_precision: number | null;
  roc_auc: number | null;
  detection_rate: number | null;
  detection_time_ms: number | null;
  // Con qué se reconstruye la aritmética de una decisión:
  // puntaje = sigmoide(base_value + suma de los aportes por variable).
  base_value: number | null;
  n_trees: number | null;
  features: string[];

  // Cuánto le falta a la tienda para reentrenar con sus propias compras en
  // lugar del conjunto sintético.
  labeled_orders: number;
  labeled_frauds: number;
  labeled_legit: number;
  required_total: number;
  required_per_class: number;
  can_train_with_real_data: boolean;
}

/** Resumen de la tienda para el panel: pedidos por estado y lo cobrado. */
export interface OrderSummaryResponse {
  total: number;
  by_status: Record<string, number>;
  revenue: number;
  awaiting_review: number;
}

/**
 * Una cuenta de la tienda, tal como la devuelve la API.
 *
 * Nunca trae la contraseña ni su hash: el backend responde con este mismo
 * recorte en el registro, en el perfil y en el panel.
 */
export interface UserResponse {
  id: string;
  email: string;
  full_name: string;
  phone: string | null;
  role: string;
  is_active: boolean;
  created_at: string;
}

/** Una página del listado de cuentas del panel. */
export interface UserListResponse {
  items: UserResponse[];
  total: number;
  page: number;
  pages: number;
  // Cuántos administradores activos hay. El panel lo usa para avisar antes de
  // degradar al último que queda, en vez de dejar que el backend lo rechace.
  active_admins: number;
}

/** Una fila de la comparación entre LightGBM y las alternativas. */
export interface ModelComparisonRow {
  modelo: string;
  average_precision: number;
  roc_auc: number;
  precision: number;
  recall: number;
  f1: number;
  fraudes_aprobados: number;
  legitimos_bloqueados: number;
  perdida_total: number;
}

/** La comparación completa, tal como la dejó el entrenamiento. */
export interface ModelComparisonResponse {
  disponible: boolean;
  origen_de_los_datos: string | null;
  detalle_de_los_datos: string | null;
  particion_de_prueba: number | null;
  resultados: ModelComparisonRow[];
}
