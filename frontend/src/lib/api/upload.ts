/** Subida de imágenes. No usa `request` porque manda un formulario, no JSON. */

import { API_BASE_URL, ApiError, getToken } from "./cliente";

export const upload = {
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
};
