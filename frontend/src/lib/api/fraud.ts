/** Modelo de detección de fraude: métricas, etiquetado y reentrenamiento. */

import { descargar, request } from "./cliente";
import type {
  EscalaDelHistorial,
  FraudHistoryResponse,
  ModelComparisonResponse,
  FraudLogResponse,
  FraudMetricsResponse,
  FraudModelInfo,
} from "./tipos";

/** Escala y tramo de calendario con los que se consulta el historial. */
export interface RangoDelHistorial {
  granularity?: EscalaDelHistorial;
  // Fechas en ISO (AAAA-MM-DD), tal como las devuelve un <input type="date">.
  // Vacías significa «la ventana que termina hoy», que es el comportamiento de
  // siempre.
  startDate?: string;
  endDate?: string;
}

/**
 * Arma la cadena de consulta del historial.
 *
 * Está en una función y no repetida en cada método porque `history` y
 * `downloadReport` tienen que mandar exactamente los mismos parámetros: el
 * archivo que se descarga no puede cubrir un tramo distinto del que se está
 * viendo en pantalla.
 */
function consultaDelHistorial(params?: RangoDelHistorial): URLSearchParams {
  const qs = new URLSearchParams();
  if (params?.granularity) qs.set("granularity", params.granularity);
  if (params?.startDate) qs.set("start_date", params.startDate);
  if (params?.endDate) qs.set("end_date", params.endDate);
  return qs;
}

export const fraud = {
  // Por qué LightGBM y no otro clasificador. Sale del informe que escribe el
  // entrenamiento, así que no puede desviarse del modelo que está sirviendo.
  async comparison() {
    return request<ModelComparisonResponse>("/fraud/comparison");
  },

  async getMetrics() {
    return request<FraudMetricsResponse>("/fraud/metrics");
  },
  // Las mismas decisiones repartidas en el tiempo. `getMetrics` dice cómo va
  // el modelo; esto dice cómo ha ido, que es lo que distingue una tendencia de
  // un mal día.
  async history(params?: RangoDelHistorial & { periods?: number }) {
    const qs = consultaDelHistorial(params);
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

  // El mismo reporte que enseña el panel, en un archivo de Excel. Recibe los
  // mismos parámetros que `history` a propósito: si el rango se quedara en la
  // pantalla, quien exporta mirando un día concreto se llevaría otra cosa.
  async downloadReport(params?: RangoDelHistorial) {
    const cadena = consultaDelHistorial(params).toString();
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
