/** Reseñas de productos. */

import { request } from "./cliente";
import type { ProductReviewResponse } from "./tipos";

export const reviews = {
  async getProductReviews(productId: string) {
    return request<ProductReviewResponse[]>(`/reviews/product/${productId}`, { skipAuth: true });
  },
  async create(data: { product_id: string; rating: number; comment?: string }) {
    return request<ProductReviewResponse>("/reviews", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },
};
