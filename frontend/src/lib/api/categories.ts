/** Categorías del catálogo. */

import { request } from "./cliente";
import type { CategoryResponse } from "./tipos";

export const categories = {
  async list() {
    return request<CategoryResponse[]>("/categories");
  },

  async create(data: {
    name: string;
    slug: string;
    is_high_risk: boolean;
    image_url?: string | null;
    parent_id?: number | null;
  }) {
    return request<CategoryResponse>("/categories", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  async update(
    id: number,
    data: {
      name?: string;
      slug?: string;
      is_high_risk?: boolean;
      image_url?: string | null;
      parent_id?: number | null;
    }
  ) {
    return request<CategoryResponse>(`/categories/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  },

  async delete(id: number) {
    return request(`/categories/${id}`, { method: "DELETE" });
  },
};
