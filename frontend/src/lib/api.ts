/**
 * HTTP Client wrapper con autenticación JWT automática.
 * Centraliza todas las llamadas al backend FastAPI.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

interface FetchOptions extends RequestInit {
  skipAuth?: boolean;
}

class ApiError extends Error {
  status: number;
  data: Record<string, unknown>;

  constructor(message: string, status: number, data: Record<string, unknown> = {}) {
    super(message);
    this.status = status;
    this.data = data;
    this.name = "ApiError";
  }
}

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
}

function setToken(token: string): void {
  localStorage.setItem("access_token", token);
}

function removeToken(): void {
  localStorage.removeItem("access_token");
}

async function request<T>(
  endpoint: string,
  options: FetchOptions = {}
): Promise<T> {
  const { skipAuth = false, headers: customHeaders, ...rest } = options;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(customHeaders as Record<string, string>),
  };

  if (!skipAuth) {
    const token = getToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...rest,
    headers,
  });

  if (response.status === 401) {
    removeToken();
    throw new ApiError("No autorizado", 401);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const data = await response.json();

  if (!response.ok) {
    throw new ApiError(
      data.detail || "Error en la solicitud",
      response.status,
      data
    );
  }

  return data as T;
}

// ===== API Methods =====

export const api = {
  // --- System ---
  system: {
    async health() {
      const url = API_BASE_URL.replace('/api/v1', '/health');
      const response = await fetch(url);
      if (!response.ok) throw new Error("Health check failed");
      return response.json() as Promise<{ status: string; database: string; ml_model: string }>;
    }
  },

  // --- Auth ---
  auth: {
    async login(email: string, password: string) {
      const data = await request<{ access_token: string; token_type: string }>(
        "/auth/login",
        {
          method: "POST",
          body: JSON.stringify({ email, password }),
          skipAuth: true,
        }
      );
      setToken(data.access_token);
      return data;
    },

    async register(payload: {
      email: string;
      password: string;
      full_name: string;
      phone?: string;
    }) {
      return request("/auth/register", {
        method: "POST",
        body: JSON.stringify(payload),
        skipAuth: true,
      });
    },

    async me() {
      return request<{
        id: string;
        email: string;
        full_name: string;
        phone: string | null;
        role: string;
        is_active: boolean;
        created_at: string;
        avatar_url?: string | null;
      }>("/auth/me");
    },

    async updateProfile(data: { full_name?: string; phone?: string; avatar_url?: string | null }) {
      return request<{
        id: string;
        email: string;
        full_name: string;
        phone: string | null;
        role: string;
        is_active: boolean;
        created_at: string;
        avatar_url?: string | null;
      }>("/auth/me", {
        method: "PATCH",
        body: JSON.stringify(data),
      });
    },

    logout() {
      removeToken();
      if (typeof window !== "undefined") {
        window.location.href = "/";
      }
    },

    isAuthenticated(): boolean {
      return !!getToken();
    },
  },

  // --- Products ---
  products: {
    async list(params?: {
      page?: number;
      per_page?: number;
      category_id?: number;
      search?: string;
      active_only?: boolean;
    }) {
      const searchParams = new URLSearchParams();
      if (params?.page) searchParams.set("page", String(params.page));
      if (params?.per_page) searchParams.set("per_page", String(params.per_page));
      if (params?.category_id) searchParams.set("category_id", String(params.category_id));
      if (params?.search) searchParams.set("search", params.search);
      if (params?.active_only !== undefined)
        searchParams.set("active_only", String(params.active_only));

      const qs = searchParams.toString();
      return request<{
        items: ProductResponse[];
        total: number;
        page: number;
        pages: number;
      }>(`/products${qs ? `?${qs}` : ""}`);
    },

    async get(id: string) {
      return request<ProductResponse>(`/products/${id}`);
    },

    async create(data: ProductCreate) {
      return request<ProductResponse>("/products", {
        method: "POST",
        body: JSON.stringify(data),
      });
    },

    async update(id: string, data: Partial<ProductCreate>) {
      return request<ProductResponse>(`/products/${id}`, {
        method: "PUT",
        body: JSON.stringify(data),
      });
    },

    async toggle(id: string) {
      return request<ProductResponse>(`/products/${id}/toggle`, {
        method: "PATCH",
      });
    },
  },

  // --- Categories ---
  categories: {
    async list() {
      return request<CategoryResponse[]>("/categories");
    },

    async create(data: { name: string; slug: string; is_high_risk: boolean }) {
      return request<CategoryResponse>("/categories", {
        method: "POST",
        body: JSON.stringify(data),
      });
    },

    async update(
      id: number,
      data: { name?: string; slug?: string; is_high_risk?: boolean }
    ) {
      return request<CategoryResponse>(`/categories/${id}`, {
        method: "PUT",
        body: JSON.stringify(data),
      });
    },

    async delete(id: number) {
      return request(`/categories/${id}`, { method: "DELETE" });
    },
  },

  // --- Orders ---
  orders: {
    async list(params?: { page?: number; per_page?: number; status?: string }) {
      const searchParams = new URLSearchParams();
      if (params?.page) searchParams.set("page", String(params.page));
      if (params?.per_page) searchParams.set("per_page", String(params.per_page));
      if (params?.status) searchParams.set("status", params.status);

      const qs = searchParams.toString();
      return request<{
        items: OrderResponse[];
        total: number;
        page: number;
        pages: number;
      }>(`/orders${qs ? `?${qs}` : ""}`);
    },

    async updateStatus(id: string, status: string) {
      return request<OrderResponse>(`/orders/${id}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      });
    },

    async create(data: { items: { product_id: string; quantity: number; unit_price: number }[]; shipping_address?: string; shipping_city?: string; checkout_duration_seconds?: number }) {
      return request<OrderResponse>("/orders", {
        method: "POST",
        body: JSON.stringify(data),
      });
    },

    async listMyOrders(params?: { page?: number; per_page?: number }) {
      const searchParams = new URLSearchParams();
      if (params?.page) searchParams.set("page", String(params.page));
      if (params?.per_page) searchParams.set("per_page", String(params.per_page));
      
      const qs = searchParams.toString();
      return request<{
        items: OrderResponse[];
        total: number;
        page: number;
        pages: number;
      }>(`/orders/my-orders${qs ? `?${qs}` : ""}`);
    },

    async cancel(id: string) {
      return request<OrderResponse>(`/orders/my-orders/${id}/cancel`, {
        method: "PATCH",
      });
    },
  },

  // --- Service Orders ---
  serviceOrders: {
    async list(params?: { page?: number; status?: string }) {
      const searchParams = new URLSearchParams();
      if (params?.page) searchParams.set("page", String(params.page));
      if (params?.status) searchParams.set("status", params.status);

      const qs = searchParams.toString();
      return request<{
        items: ServiceOrderResponse[];
        total: number;
        page: number;
        pages: number;
      }>(`/service-orders${qs ? `?${qs}` : ""}`);
    },

    async update(
      id: string,
      data: { diagnosis?: string; status?: string; estimated_cost?: number }
    ) {
      return request<ServiceOrderResponse>(`/service-orders/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      });
    },

    async listMyServices(params?: { page?: number; per_page?: number }) {
      const searchParams = new URLSearchParams();
      if (params?.page) searchParams.set("page", String(params.page));
      if (params?.per_page) searchParams.set("per_page", String(params.per_page));

      const qs = searchParams.toString();
      return request<{
        items: ServiceOrderResponse[];
        total: number;
        page: number;
        pages: number;
      }>(`/service-orders/my-services${qs ? `?${qs}` : ""}`);
    },

    async create(data: { device_type: string; brand?: string; issue_description: string }) {
      return request<ServiceOrderResponse>("/service-orders", {
        method: "POST",
        body: JSON.stringify(data),
      });
    },
  },

  // --- Reviews ---
  reviews: {
    async getProductReviews(productId: string) {
      return request<ProductReviewResponse[]>(`/reviews/product/${productId}`, { skipAuth: true });
    },
    async create(data: { product_id: string; rating: number; comment?: string }) {
      return request<ProductReviewResponse>("/reviews", {
        method: "POST",
        body: JSON.stringify(data),
      });
    },
  },

  // --- Upload ---
  upload: {
    async image(file: File): Promise<{ url: string; filename: string }> {
      const token = getToken();
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(`${API_BASE_URL}/upload/image`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      });

      if (!response.ok) {
        const data = await response.json();
        throw new ApiError(data.detail || "Error al subir imagen", response.status);
      }

      return response.json();
    },
  },

  // --- Fraud ---
  fraud: {
    async getMetrics() {
      return request<FraudMetricsResponse>("/fraud/metrics");
    },
    async getLogs() {
      return request<FraudLogResponse[]>("/fraud/logs");
    },
    async markActualFraud(id: string) {
      return request<FraudLogResponse>(`/fraud/logs/${id}/actual-fraud`, {
        method: "PUT"
      });
    }
  },
};


// ===== Types =====

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
  admin_notes: string | null;
  is_actual_fraud: boolean;
  detection_time_ms: number | null;
  evaluated_at: string;
}

export interface FraudMetricsResponse {
  total_evaluations: number;
  detected_fraud_rate: number;
  undetected_fraud_rate: number;
  average_detection_time_ms: number;
}

export { ApiError, getToken, setToken, removeToken };
export default api;
