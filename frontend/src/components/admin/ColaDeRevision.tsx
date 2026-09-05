"use client";

/**
 * Los pedidos que el modelo retuvo y esperan que alguien decida.
 *
 * Antes esto no existía como pantalla: para revisar un pedido retenido había
 * que ir a Órdenes, filtrar por "Revisión Fraude", abrir cada uno y buscar los
 * botones de etiquetado dentro del diálogo de cambiar estado. Dos trabajos
 * distintos —despachar pedidos y auditar al modelo— mezclados en el mismo
 * sitio.
 *
 * Aquí van juntas las dos decisiones que corresponden a este trabajo: qué se
 * hace con el pedido (aprobarlo o rechazarlo) y qué se le enseña al modelo
 * (era fraude o no lo era). Son distintas: un pedido puede aprobarse y aun así
 * resultar un fraude semanas después, cuando llega el contracargo.
 */

import { useState } from "react";
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Skeleton,
  Stack,
  Tooltip,
  Typography,
} from "@mui/material";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutlined";
import BlockIcon from "@mui/icons-material/Block";
import type { OrderResponse } from "@/lib/api";

const soles = (monto: number) =>
  `S/ ${monto.toLocaleString("es-PE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export default function ColaDeRevision({
  pedidos,
  cargando,
  onDecidir,
  onEtiquetar,
}: {
  pedidos: OrderResponse[];
  cargando: boolean;
  /** Qué se hace con el pedido: dejarlo seguir al cobro o rechazarlo. */
  onDecidir: (pedido: OrderResponse, aprobar: boolean) => void;
  /** Qué se le enseña al modelo sobre este caso. */
  onEtiquetar: (fraudLogId: string, fueFraude: boolean) => void;
}) {
  const [ocupado, setOcupado] = useState<string | null>(null);

  const decidir = async (pedido: OrderResponse, aprobar: boolean) => {
    setOcupado(pedido.id);
    try {
      await onDecidir(pedido, aprobar);
    } finally {
      setOcupado(null);
    }
  };

  return (
    <Card elevation={0} sx={{ border: "1px solid", borderColor: "divider", borderRadius: 3 }}>
      <CardContent sx={{ p: 3 }}>
        <Stack direction="row" spacing={1.5} sx={{ alignItems: "center", mb: 0.5 }}>
          <Typography variant="subtitle1" sx={{ fontWeight: 800 }}>
            Cola de revisión
          </Typography>
          {!cargando && pedidos.length > 0 && (
            <Chip label={pedidos.length} size="small" color="warning" sx={{ fontWeight: 800 }} />
          )}
        </Stack>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3, maxWidth: 720 }}>
          Compras que el modelo no bloqueó del todo pero tampoco dejó pasar. Están
          retenidas antes del cobro: mientras nadie decida, el cliente no puede pagar
          y el stock sigue apartado.
        </Typography>

        {cargando ? (
          <Stack spacing={1.5}>
            {[0, 1].map((i) => (
              <Skeleton key={i} variant="rectangular" height={104} sx={{ borderRadius: 2 }} />
            ))}
          </Stack>
        ) : pedidos.length === 0 ? (
          <Box
            sx={{
              py: 5,
              textAlign: "center",
              border: "1px dashed",
              borderColor: "divider",
              borderRadius: 2,
            }}
          >
            <Typography variant="body2" color="text.secondary">
              No hay pedidos esperando revisión.
            </Typography>
          </Box>
        ) : (
          <Stack spacing={1.5}>
            {pedidos.map((p) => (
              <Box
                key={p.id}
                sx={{ border: "1px solid", borderColor: "divider", borderRadius: 2, p: 2 }}
              >
                <Stack
                  direction={{ xs: "column", md: "row" }}
                  spacing={2}
                  sx={{ justifyContent: "space-between", alignItems: { md: "flex-start" } }}
                >
                  <Box sx={{ minWidth: 0 }}>
                    <Stack direction="row" spacing={1} sx={{ alignItems: "center", flexWrap: "wrap" }}>
                      <Typography component="code" variant="body2" sx={{ fontSize: "0.75rem", color: "text.secondary" }}>
                        {p.id.slice(0, 8)}
                      </Typography>
                      <Typography variant="body2" sx={{ fontWeight: 800 }}>
                        {soles(p.total_amount)}
                      </Typography>
                      {p.fraud_score !== null && (
                        <Chip
                          label={`Riesgo ${(p.fraud_score * 100).toFixed(0)}%`}
                          size="small"
                          color={p.fraud_score < 0.3 ? "success" : p.fraud_score < 0.7 ? "warning" : "error"}
                          sx={{ fontWeight: 700, fontSize: "0.68rem" }}
                        />
                      )}
                      <Typography variant="caption" color="text.secondary">
                        {new Date(p.created_at).toLocaleString("es-PE", {
                          dateStyle: "medium",
                          timeStyle: "short",
                        })}
                      </Typography>
                    </Stack>

                    {p.fraud_explanation && (
                      <Typography variant="body2" color="text.secondary" sx={{ mt: 1, lineHeight: 1.6 }}>
                        {p.fraud_explanation}
                      </Typography>
                    )}

                    <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 1 }}>
                      {p.items.length} {p.items.length === 1 ? "artículo" : "artículos"}
                      {p.shipping_city ? ` · ${p.shipping_city}` : ""}
                    </Typography>
                  </Box>

                  <Stack spacing={1.2} sx={{ flexShrink: 0 }}>
                    <Stack direction="row" spacing={1}>
                      <Button
                        size="small"
                        variant="contained"
                        color="success"
                        disabled={ocupado === p.id}
                        startIcon={<CheckCircleOutlineIcon />}
                        onClick={() => decidir(p, true)}
                        sx={{ textTransform: "none", fontWeight: 700 }}
                      >
                        Dejar pasar
                      </Button>
                      <Button
                        size="small"
                        variant="outlined"
                        color="error"
                        disabled={ocupado === p.id}
                        startIcon={<BlockIcon />}
                        onClick={() => decidir(p, false)}
                        sx={{ textTransform: "none", fontWeight: 700 }}
                      >
                        Rechazar
                      </Button>
                    </Stack>

                    {p.fraud_log_id && (
                      <Tooltip title="Esto no cambia el pedido: es lo que el modelo aprende de este caso.">
                        <Stack direction="row" spacing={1}>
                          <Button
                            size="small"
                            variant="text"
                            color="error"
                            onClick={() => onEtiquetar(p.fraud_log_id!, true)}
                            sx={{ textTransform: "none", fontWeight: 600, fontSize: "0.75rem" }}
                          >
                            Marcar fraude real
                          </Button>
                          <Button
                            size="small"
                            variant="text"
                            onClick={() => onEtiquetar(p.fraud_log_id!, false)}
                            sx={{ textTransform: "none", fontWeight: 600, fontSize: "0.75rem" }}
                          >
                            Marcar legítima
                          </Button>
                        </Stack>
                      </Tooltip>
                    )}
                  </Stack>
                </Stack>
              </Box>
            ))}
          </Stack>
        )}
      </CardContent>
    </Card>
  );
}
