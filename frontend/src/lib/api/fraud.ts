/** Modelo de detección de fraude: métricas, etiquetado y reentrenamiento. */

import { request } from "./cliente";
import type {
  FraudHistoryResponse,
  FraudLogResponse,
  FraudMetricsResponse,
} from "./tipos";

export const fraud = {
  async getMetrics() {
    return request<FraudMetricsResponse>("/fraud/metrics");
  },
  // Las mismas decisiones repartidas en el tiempo. `getMetrics` dice cómo va
  // el modelo; esto dice cómo ha ido, que es lo que distingue una tendencia de
  // un mal día.
  async history(params?: {
    granularity?: "day" | "week" | "month" | "year";
    periods?: number;
  }) {
    const qs = new URLSearchParams();
    if (params?.granularity) qs.set("granularity", params.granularity);
    if (params?.periods) qs.set("periods", String(params.periods));
    const cadena = qs.toString();
    return request<FraudHistoryResponse>(`/fraud/history${cadena ? `?${cadena}` : ""}`);
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
