/** Modelo de detección de fraude: métricas, etiquetado y reentrenamiento. */

import { descargar, request } from "./cliente";
import type {
  FraudHistoryResponse,
  FraudLogResponse,
  FraudMetricsResponse,
  FraudModelInfo,
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

  // Con qué se publicó el modelo que está sirviendo. No son las métricas de la
  // tienda —esas se mueven con cada revisión—, sino las que midió el
  // entrenamiento antes de publicarlo.
  async model() {
    return request<FraudModelInfo>("/fraud/model");
  },

  // El mismo reporte que enseña el panel, en un archivo de Excel.
  async downloadReport(params?: { granularity?: "day" | "week" | "month" | "year" }) {
    const qs = new URLSearchParams();
    if (params?.granularity) qs.set("granularity", params.granularity);
    const cadena = qs.toString();
    return descargar(
      `/fraud/report.xlsx${cadena ? `?${cadena}` : ""}`,
      "indicadores-antifraude.xlsx"
    );
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
