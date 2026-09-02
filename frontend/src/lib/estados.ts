/**
 * Cómo se muestra cada estado del sistema.
 *
 * El backend maneja los estados en mayúsculas (`FRAUD_REVIEW`, `IN_PROGRESS`);
 * la interfaz necesita un texto en español y un color. Esa traducción estaba
 * copiada en cada pantalla que mostraba un estado, con el riesgo de que la
 * misma etiqueta acabara diciendo cosas distintas según dónde se mirara.
 *
 * Aquí está una sola vez, junto a los tipos que enumeran los valores posibles.
 */

export type EstadoDePedido =
  | "PENDING"
  | "FRAUD_REVIEW"
  | "APPROVED"
  | "REJECTED"
  | "COMPLETED"
  | "CANCELLED";

export type ColorDeEstado = "warning" | "error" | "success" | "info" | "default";

export const ESTADOS_DE_PEDIDO: Record<
  EstadoDePedido,
  { label: string; color: ColorDeEstado }
> = {
  PENDING: { label: "Pendiente", color: "warning" },
  FRAUD_REVIEW: { label: "Revisión Fraude", color: "error" },
  APPROVED: { label: "Aprobada", color: "success" },
  REJECTED: { label: "Rechazada", color: "error" },
  COMPLETED: { label: "Completada", color: "info" },
  CANCELLED: { label: "Cancelada", color: "default" },
};

export type EstadoDeServicio =
  | "RECEIVED"
  | "DIAGNOSING"
  | "IN_PROGRESS"
  | "COMPLETED"
  | "DELIVERED";

export const ESTADOS_DE_SERVICIO: Record<
  EstadoDeServicio,
  { label: string; color: "info" | "warning" | "success" }
> = {
  RECEIVED: { label: "Recibido", color: "info" },
  DIAGNOSING: { label: "Diagnosticando", color: "warning" },
  IN_PROGRESS: { label: "En Proceso", color: "warning" },
  COMPLETED: { label: "Completado", color: "success" },
  DELIVERED: { label: "Entregado", color: "success" },
};
