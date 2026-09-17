/** Pedidos: creación, seguimiento del cliente y gestión del administrador. */

import { request } from "./cliente";
import type {
  PagoSimuladoRequest,
  PagoSimuladoResponse,
  OrderResponse,
  OrderSummaryResponse,
} from "./tipos";

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

  // Cuántos pedidos hay en cada estado y cuánto se cobró, en una sola
  // consulta agrupada: antes el panel pedía la lista una vez por estado solo
  // para leer el `total` de cada respuesta.
  async summary() {
    return request<OrderSummaryResponse>("/orders/summary");
  },

  // Libera una orden retenida por el modelo. No es lo mismo que ponerle
  // PENDING a mano: el backend le genera además el enlace de pago que nunca
  // tuvo, sin el cual el cliente no podría pagarla.
  async release(id: string) {
    return request<OrderResponse>(`/orders/${id}/release`, { method: "PATCH" });
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

  // Cobra un pedido con la pasarela simulada. No mueve dinero, y el pedido
  // queda marcado como simulado para que nunca se confunda con un cobro real.
  // Una orden concreta. El formulario de pago la pide para enseñar qué se está
  // pagando: un checkout que no dice el importe no se parece a ninguno real.
  async get(id: string) {
    return request<OrderResponse>(`/orders/${id}`);
  },

  async pagarSimulado(id: string, datos: PagoSimuladoRequest) {
    return request<PagoSimuladoResponse>(`/orders/${id}/pago-simulado`, {
      method: "POST",
      body: JSON.stringify(datos),
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
