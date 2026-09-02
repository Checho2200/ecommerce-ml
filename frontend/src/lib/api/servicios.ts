/** Órdenes de servicio técnico. */

import { request } from "./cliente";
import type { ServiceOrderResponse } from "./tipos";

export const serviceOrders = {
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
};
