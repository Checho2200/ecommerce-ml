/** Estado del servicio: es lo que consulta el panel y lo que despierta al backend. */

import { API_BASE_URL } from "./cliente";

export const system = {
  async health() {
    const url = API_BASE_URL.replace('/api/v1', '/health');
    const response = await fetch(url);
    if (!response.ok) throw new Error("Health check failed");
    return response.json() as Promise<{
      status: string;
      database: string;
      ml_model: string;
      payments?: string;
    }>;
  }
};
