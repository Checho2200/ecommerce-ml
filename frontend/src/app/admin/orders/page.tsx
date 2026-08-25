"use client";

import { useEffect, useState, useCallback } from "react";
import { api, type OrderResponse } from "@/lib/api";

// MUI
import {
  Box,
  Typography,
  Button,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Paper,
  Skeleton,
  Pagination,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Grid,
  IconButton,
  Tooltip,
  Snackbar,
  Alert,
  alpha,
} from "@mui/material";

// MUI Icons
import VisibilityIcon from "@mui/icons-material/Visibility";
import PsychologyIcon from "@mui/icons-material/Psychology";

type StatusKey = "PENDING" | "FRAUD_REVIEW" | "APPROVED" | "REJECTED" | "COMPLETED" | "CANCELLED";

const STATUS_CONFIG: Record<StatusKey, { label: string; color: "warning" | "error" | "success" | "info" | "default" }> = {
  PENDING: { label: "Pendiente", color: "warning" },
  FRAUD_REVIEW: { label: "Revisión Fraude", color: "error" },
  APPROVED: { label: "Aprobada", color: "success" },
  REJECTED: { label: "Rechazada", color: "error" },
  COMPLETED: { label: "Completada", color: "info" },
  CANCELLED: { label: "Cancelada", color: "default" },
};

export default function OrdersPage() {
  const [orders, setOrders] = useState<OrderResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [statusFilter, setStatusFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [selectedOrder, setSelectedOrder] = useState<OrderResponse | null>(null);
  const [snack, setSnack] = useState<{ msg: string; severity: "success" | "error" } | null>(null);

  const fetchOrders = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.orders.list({
        page,
        per_page: 10,
        status: statusFilter || undefined,
      });
      setOrders(data.items);
      setTotal(data.total);
      setPages(data.pages);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [page, statusFilter]);

  useEffect(() => {
    fetchOrders();
  }, [fetchOrders]);

  const showSnack = (msg: string, severity: "success" | "error" = "success") =>
    setSnack({ msg, severity });

  const handleStatusChange = async (orderId: string, newStatus: string) => {
    try {
      await api.orders.updateStatus(orderId, newStatus);
      showSnack("Estado actualizado");
      fetchOrders();
      setSelectedOrder(null);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Error";
      showSnack(message, "error");
    }
  };

  const FILTER_OPTIONS: { value: string; label: string }[] = [
    { value: "", label: "Todas" },
    { value: "PENDING", label: "Pendientes" },
    { value: "FRAUD_REVIEW", label: "Revisión Fraude" },
    { value: "APPROVED", label: "Aprobadas" },
    { value: "COMPLETED", label: "Completadas" },
    { value: "REJECTED", label: "Rechazadas" },
  ];

  return (
    <>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h5" sx={{ fontWeight: 800 }}>
          Órdenes de Compra
        </Typography>
        <Typography variant="body2" sx={{ color: "text.secondary", mt: 0.5 }}>
          {total} órdenes registradas
        </Typography>
      </Box>

      {/* Filters */}
      <Box sx={{ display: "flex", gap: 1, mb: 3, flexWrap: "wrap" }}>
        {FILTER_OPTIONS.map((opt) => (
          <Chip
            key={opt.value}
            label={opt.label}
            variant={statusFilter === opt.value ? "filled" : "outlined"}
            color={statusFilter === opt.value ? "primary" : "default"}
            onClick={() => { setStatusFilter(opt.value); setPage(1); }}
            sx={{ fontWeight: 700, cursor: "pointer" }}
          />
        ))}
      </Box>

      {/* Table */}
      <Paper
        elevation={0}
        sx={{
          border: "1px solid",
          borderColor: "divider",
          borderRadius: 2,
          overflow: "hidden",
          bgcolor: "background.paper",
        }}
      >
        <Table>
          <TableHead sx={{ bgcolor: "background.default" }}>
            <TableRow>
              {["ID", "Total", "Estado", "Fraude", "Ciudad", "Fecha", ""].map((h, i) => (
                <TableCell
                  key={i}
                  align={i === 6 ? "right" : "left"}
                  sx={{ fontWeight: 700, fontSize: "0.75rem", textTransform: "uppercase", color: "text.secondary" }}
                >
                  {h}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {loading ? (
              [...Array(5)].map((_, i) => (
                <TableRow key={i}>
                  {[...Array(7)].map((_, j) => (
                    <TableCell key={j}><Skeleton height={40} /></TableCell>
                  ))}
                </TableRow>
              ))
            ) : orders.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} align="center" sx={{ py: 6, color: "text.disabled" }}>
                  No hay órdenes
                </TableCell>
              </TableRow>
            ) : (
              orders.map((o) => {
                const st = STATUS_CONFIG[o.status as StatusKey] || { label: o.status, color: "default" as const };
                return (
                  <TableRow key={o.id} hover sx={{ "&:last-child td": { borderBottom: 0 } }}>
                    <TableCell>
                      <Typography
                        component="code"
                        variant="body2"
                        sx={{ color: "primary.main", fontSize: "0.75rem", bgcolor: "action.hover", px: 0.5, borderRadius: 0.5 }}
                      >
                        {o.id.slice(0, 8)}...
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" sx={{ fontWeight: 700, fontFamily: "monospace" }}>
                        S/{o.total_amount.toFixed(2)}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip label={st.label} size="small" color={st.color} variant="outlined" sx={{ fontWeight: 700, fontSize: "0.7rem" }} />
                    </TableCell>
                    <TableCell>
                      {o.fraud_score !== null ? (
                        <Chip
                          label={`${(o.fraud_score * 100).toFixed(0)}%`}
                          size="small"
                          color={o.fraud_score < 0.3 ? "success" : o.fraud_score < 0.7 ? "warning" : "error"}
                          variant="filled"
                          sx={{ fontWeight: 700, fontSize: "0.7rem" }}
                        />
                      ) : (
                        <Chip label="N/A" size="small" variant="outlined" sx={{ fontWeight: 700, fontSize: "0.7rem" }} />
                      )}
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" sx={{ color: "text.secondary", fontSize: "0.8rem" }}>
                        {o.shipping_city || "—"}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" sx={{ color: "text.secondary", fontSize: "0.8rem" }}>
                        {new Date(o.created_at).toLocaleDateString("es-PE")}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      <Tooltip title="Ver detalle">
                        <IconButton
                          size="small"
                          onClick={() => setSelectedOrder(o)}
                          sx={{ color: "primary.main", "&:hover": { bgcolor: (theme) => alpha(theme.palette.primary.main, 0.08) } }}
                        >
                          <VisibilityIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </Paper>

      {/* Pagination */}
      {pages > 1 && (
        <Box sx={{ display: "flex", justifyContent: "center", mt: 3 }}>
          <Pagination
            count={pages}
            page={page}
            onChange={(_, v) => setPage(v)}
            color="primary"
            shape="rounded"
          />
        </Box>
      )}

      {/* Detail Modal */}
      {selectedOrder && (
        <Dialog
          open
          onClose={() => setSelectedOrder(null)}
          maxWidth="sm"
          fullWidth
          sx={{ "& .MuiDialog-paper": { borderRadius: 3 } }}
        >
          <DialogTitle sx={{ fontWeight: 800, pb: 1 }}>
            Detalle de Orden
          </DialogTitle>
          <DialogContent sx={{ pt: 1 }}>
            <Grid container spacing={2} sx={{ mb: 2 }}>
              <Grid size={6}>
                <Typography variant="caption" sx={{ color: "text.secondary", fontWeight: 600, textTransform: "uppercase", fontSize: "0.68rem" }}>
                  ID
                </Typography>
                <Typography
                  component="code"
                  variant="body2"
                  sx={{ display: "block", color: "primary.main", fontSize: "0.75rem", mt: 0.5 }}
                >
                  {selectedOrder.id}
                </Typography>
              </Grid>
              <Grid size={6}>
                <Typography variant="caption" sx={{ color: "text.secondary", fontWeight: 600, textTransform: "uppercase", fontSize: "0.68rem" }}>
                  Total
                </Typography>
                <Typography variant="h6" sx={{ fontWeight: 800, mt: 0.5 }}>
                  S/{selectedOrder.total_amount.toFixed(2)}
                </Typography>
              </Grid>
            </Grid>

            {/* Items */}
            <Typography variant="caption" sx={{ color: "text.secondary", fontWeight: 600, textTransform: "uppercase", fontSize: "0.68rem" }}>
              Items
            </Typography>
            <Box sx={{ display: "flex", flexDirection: "column", gap: 0.75, mt: 1, mb: 2 }}>
              {selectedOrder.items.map((item) => (
                <Box
                  key={item.id}
                  sx={{
                    display: "flex",
                    justifyContent: "space-between",
                    p: 1.5,
                    bgcolor: "action.hover",
                    borderRadius: 1.5,
                  }}
                >
                  <Typography variant="body2">
                    {item.product_name || item.product_id.slice(0, 8)} × {item.quantity}
                  </Typography>
                  <Typography variant="body2" sx={{ fontWeight: 700 }}>
                    S/{(item.unit_price * item.quantity).toFixed(2)}
                  </Typography>
                </Box>
              ))}
            </Box>

            {/* Fraud Score */}
            {selectedOrder.fraud_score !== null && (
              <Box
                sx={{
                  p: 2,
                  bgcolor: (theme) =>
                    selectedOrder.fraud_score! > 0.7
                      ? alpha(theme.palette.error.main, 0.08)
                      : selectedOrder.fraud_score! > 0.3
                      ? alpha(theme.palette.warning.main, 0.08)
                      : alpha(theme.palette.success.main, 0.08),
                  borderRadius: 2,
                  border: "1px solid",
                  borderColor: (theme) =>
                    selectedOrder.fraud_score! > 0.7
                      ? alpha(theme.palette.error.main, 0.2)
                      : selectedOrder.fraud_score! > 0.3
                      ? alpha(theme.palette.warning.main, 0.2)
                      : alpha(theme.palette.success.main, 0.2),
                  mb: 2,
                }}
              >
                <Box sx={{ display: "flex", alignItems: "center", gap: 0.75, mb: 0.5 }}>
                  <PsychologyIcon sx={{ fontSize: 16, color: "text.secondary" }} />
                  <Typography variant="caption" sx={{ color: "text.secondary", fontWeight: 600, textTransform: "uppercase", fontSize: "0.68rem" }}>
                    Score de Fraude
                  </Typography>
                </Box>
                <Typography variant="h5" sx={{ fontWeight: 900 }}>
                  {(selectedOrder.fraud_score * 100).toFixed(1)}%
                </Typography>
                <Typography variant="caption" sx={{ color: "text.secondary" }}>
                  Decisión: {selectedOrder.fraud_decision}
                </Typography>

                {selectedOrder.fraud_decision === "APPROVED" && selectedOrder.fraud_log_id && (
                  <Button
                    variant="outlined"
                    color="error"
                    size="small"
                    sx={{ mt: 2, display: "block", textTransform: "none", fontWeight: 700 }}
                    onClick={async () => {
                      if(window.confirm("¿Estás seguro de marcar esta orden como FRAUDE REAL (Contracargo)? Esto alimentará las métricas de error de la IA.")) {
                        try {
                          await api.fraud.markActualFraud(selectedOrder.fraud_log_id!);
                          showSnack("Marcado como Fraude Real exitosamente");
                          // Refrescar no es estrictamente necesario para la orden, pero sí para el dashboard
                        } catch (err: any) {
                          showSnack(err.message || "Error al marcar fraude", "error");
                        }
                      }
                    }}
                  >
                    Reportar Contracargo (Fraude Real)
                  </Button>
                )}
              </Box>
            )}

            {/* Status Change */}
            <Typography variant="caption" sx={{ color: "text.secondary", fontWeight: 600, textTransform: "uppercase", fontSize: "0.68rem" }}>
              Cambiar Estado
            </Typography>
            <Box sx={{ display: "flex", gap: 1, mt: 1, flexWrap: "wrap" }}>
              {(Object.entries(STATUS_CONFIG) as [StatusKey, typeof STATUS_CONFIG[StatusKey]][]).map(([key, val]) => (
                <Chip
                  key={key}
                  label={val.label}
                  variant={selectedOrder.status === key ? "filled" : "outlined"}
                  color={selectedOrder.status === key ? val.color : "default"}
                  onClick={() => handleStatusChange(selectedOrder.id, key)}
                  disabled={selectedOrder.status === key}
                  sx={{ fontWeight: 700, cursor: "pointer" }}
                />
              ))}
            </Box>
          </DialogContent>
          <DialogActions sx={{ px: 3, pb: 3 }}>
            <Button
              fullWidth
              variant="outlined"
              onClick={() => setSelectedOrder(null)}
              sx={{ textTransform: "none", fontWeight: 700, borderRadius: 2 }}
            >
              Cerrar
            </Button>
          </DialogActions>
        </Dialog>
      )}

      {/* Snackbar */}
      <Snackbar
        open={!!snack}
        autoHideDuration={3000}
        onClose={() => setSnack(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
      >
        <Alert severity={snack?.severity} onClose={() => setSnack(null)} variant="filled" sx={{ width: "100%" }}>
          {snack?.msg}
        </Alert>
      </Snackbar>
    </>
  );
}
