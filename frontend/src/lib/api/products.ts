/** Catálogo: consulta pública y administración. */

import { request } from "./cliente";
import type { ProductCreate, ProductResponse } from "./tipos";

/** Ordenamientos que admite el listado. Coincide con el backend (products.py). */
export type ProductSort =
  | "recientes"
  | "precio_asc"
  | "precio_desc"
  | "nombre_asc"
  | "nombre_desc";

export const products = {
  async list(params?: {
    page?: number;
    per_page?: number;
    category_id?: number;
    search?: string;
    active_only?: boolean;
    sort?: ProductSort;
  }) {
    const searchParams = new URLSearchParams();
    if (params?.page) searchParams.set("page", String(params.page));
    if (params?.per_page) searchParams.set("per_page", String(params.per_page));
    if (params?.category_id) searchParams.set("category_id", String(params.category_id));
    if (params?.search) searchParams.set("search", params.search);
    if (params?.active_only !== undefined)
      searchParams.set("active_only", String(params.active_only));
    if (params?.sort) searchParams.set("sort", params.sort);

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
};
