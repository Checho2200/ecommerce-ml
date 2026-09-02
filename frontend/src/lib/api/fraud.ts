/** Modelo de detección de fraude: métricas, etiquetado y reentrenamiento. */

import { request } from "./cliente";
import type { FraudLogResponse, FraudMetricsResponse } from "./tipos";

export const fraud = {
  async getMetrics() {
    return request<FraudMetricsResponse>("/fraud/metrics");
  },
  async getLogs() {
    return request<FraudLogResponse[]>("/fraud/logs");
  },
  // Etiqueta una evaluación con lo que realmente pasó. Las dos respuestas
  // cuentan: sin los "era legítima" no hay verdaderos negativos y la
  // precisión del modelo no se puede calcular.
  async label(id: string, isFraud: boolean) {
    return request<FraudLogResponse>(`/fraud/logs/${id}/label`, {
      method: "PUT",
      body: JSON.stringify({ is_fraud: isFraud }),
    });
  },
  async markActualFraud(id: string) {
    return request<FraudLogResponse>(`/fraud/logs/${id}/actual-fraud`, {
      method: "PUT"
    });
  },
  // Reentrena el modelo con los casos marcados como fraude real. El backend
  // responde en cuanto arranca la tarea; el entrenamiento sigue en segundo
  // plano y puede tardar varios minutos.
  async retrain() {
    return request<{ message: string }>("/fraud/retrain", {
      method: "POST",
    });
  },
};
