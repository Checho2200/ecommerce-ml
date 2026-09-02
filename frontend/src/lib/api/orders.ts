/** Pedidos: creación, seguimiento del cliente y gestión del administrador. */

import { request } from "./cliente";
import type { OrderResponse } from "./tipos";

export const orders = {
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
};
