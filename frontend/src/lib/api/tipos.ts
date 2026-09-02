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
}

export interface OrderItemResponse {
  id: number;
  product_id: string;
  product_name: string | null;
  quantity: number;
  unit_price: number;
}

export interface ServiceOrderResponse {
  id: string;
  user_id: string;
  user_name: string | null;
  device_type: string;
  brand: string | null;
  issue_description: string;
  diagnosis: string | null;
  status: string;
  estimated_cost: number | null;
  created_at: string;
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
