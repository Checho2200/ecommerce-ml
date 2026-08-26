"use client";

import { useEffect, useState, useCallback } from "react";
import { api, type ServiceOrderResponse } from "@/lib/api";

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
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  IconButton,
  Tooltip,
  Snackbar,
  Alert,
  alpha,
} from "@mui/material";

// MUI Icons
import EditIcon from "@mui/icons-material/Edit";

type ServiceStatusKey = "RECEIVED" | "DIAGNOSING" | "IN_PROGRESS" | "COMPLETED" | "DELIVERED";

const STATUS_CONFIG: Record<ServiceStatusKey, { label: string; color: "info" | "warning" | "success" }> = {
  RECEIVED: { label: "Recibido", color: "info" },
  DIAGNOSING: { label: "Diagnosticando", color: "warning" },
  IN_PROGRESS: { label: "En Proceso", color: "warning" },
  COMPLETED: { label: "Completado", color: "success" },
  DELIVERED: { label: "Entregado", color: "success" },
};

export default function ServicesPage() {
  const [services, setServices] = useState<ServiceOrderResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [statusFilter, setStatusFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<ServiceOrderResponse | null>(null);
  const [snack, setSnack] = useState<{ msg: string; severity: "success" | "error" } | null>(null);

  const fetchServices = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.serviceOrders.list({
        page,
        status: statusFilter || undefined,
      });
      setServices(data.items);
      setTotal(data.total);
      setPages(data.pages);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [page, statusFilter]);

  useEffect(() => {
    fetchServices();
  }, [fetchServices]);

  const showSnack = (msg: string, severity: "success" | "error" = "success") =>
    setSnack({ msg, severity });

  const handleUpdate = async (id: string, data: { diagnosis?: string; status?: string; estimated_cost?: number }) => {
    try {
      await api.serviceOrders.update(id, data);
      showSnack("Servicio actualizado");
      fetchServices();
      setSelected(null);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Error";
      showSnack(message, "error");
    }
  };

  const FILTER_OPTIONS = [
    { value: "", label: "Todos" },
    ...Object.entries(STATUS_CONFIG).map(([key, val]) => ({ value: key, label: val.label })),
  ];

  return (
    <>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h5" sx={{ fontWeight: 800 }}>
          Servicio Técnico
        </Typography>
        <Typography variant="body2" sx={{ color: "text.secondary", mt: 0.5 }}>
          {total} órdenes de servicio
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
              {["Cliente", "Dispositivo", "Problema", "Estado", "Costo Est.", "Fecha", ""].map((h, i) => (
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
            ) : services.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} align="center" sx={{ py: 6, color: "text.disabled" }}>
                  No hay órdenes de servicio
                </TableCell>
              </TableRow>
            ) : (
              services.map((s) => {
                const st = STATUS_CONFIG[s.status as ServiceStatusKey] || { label: s.status, color: "info" as const };
                return (
                  <TableRow key={s.id} hover sx={{ "&:last-child td": { borderBottom: 0 } }}>
                    <TableCell>
                      <Typography variant="body2" sx={{ fontWeight: 700, fontSize: "0.8rem" }}>
                        {s.user_name || "—"}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" sx={{ fontSize: "0.8rem" }}>
                        {s.device_type}
                        {s.brand && (
                          <Typography component="span" variant="caption" sx={{ color: "text.secondary", ml: 0.5 }}>
                            ({s.brand})
                          </Typography>
                        )}
                      </Typography>
                    </TableCell>
                    <TableCell sx={{ maxWidth: 200 }}>
                      <Typography
                        variant="body2"
                        sx={{
                          color: "text.secondary",
                          fontSize: "0.8rem",
                          display: "-webkit-box",
                          WebkitLineClamp: 1,
                          WebkitBoxOrient: "vertical",
                          overflow: "hidden",
                        }}
                      >
                        {s.issue_description}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip label={st.label} size="small" color={st.color} variant="outlined" sx={{ fontWeight: 700, fontSize: "0.7rem" }} />
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" sx={{ fontFamily: "monospace", fontSize: "0.8rem" }}>
                        {s.estimated_cost ? `S/${s.estimated_cost.toFixed(2)}` : "—"}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" sx={{ color: "text.secondary", fontSize: "0.8rem" }}>
                        {new Date(s.created_at).toLocaleDateString("es-PE")}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      <Tooltip title="Gestionar">
                        <IconButton
                          size="small"
                          onClick={() => setSelected(s)}
                          sx={{ color: "primary.main", "&:hover": { bgcolor: (theme) => alpha(theme.palette.primary.main, 0.08) } }}
                        >
                          <EditIcon fontSize="small" />
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

      {/* Edit Modal */}
      {selected && (
        <ServiceModal
          service={selected}
          onUpdate={handleUpdate}
          onClose={() => setSelected(null)}
        />
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

function ServiceModal({
  service,
  onUpdate,
  onClose,
}: {
  service: ServiceOrderResponse;
  onUpdate: (id: string, data: { diagnosis?: string; status?: string; estimated_cost?: number }) => void;
  onClose: () => void;
}) {
  const [diagnosis, setDiagnosis] = useState(service.diagnosis || "");
  const [status, setStatus] = useState(service.status);
  const [cost, setCost] = useState(service.estimated_cost || 0);

  return (
    <Dialog
      open
      onClose={onClose}
      maxWidth="sm"
      fullWidth
      sx={{ "& .MuiDialog-paper": { borderRadius: 3 } }}
    >
      <DialogTitle sx={{ fontWeight: 800, pb: 1 }}>
        Gestionar Servicio
      </DialogTitle>
      <DialogContent sx={{ pt: 1 }}>
        {/* Device Info */}
        <Box
          sx={{
            mb: 3,
            p: 2,
            bgcolor: "action.hover",
            borderRadius: 2,
            border: "1px solid",
            borderColor: "divider",
          }}
        >
          <Typography variant="caption" sx={{ color: "text.secondary", fontWeight: 600, textTransform: "uppercase", fontSize: "0.68rem" }}>
            Dispositivo
          </Typography>
          <Typography variant="body1" sx={{ fontWeight: 700 }}>
            {service.device_type} {service.brand ? `(${service.brand})` : ""}
          </Typography>

          <Typography variant="caption" sx={{ color: "text.secondary", fontWeight: 600, textTransform: "uppercase", fontSize: "0.68rem", display: "block", mt: 1.5 }}>
            Problema reportado
          </Typography>
          <Typography variant="body2" sx={{ color: "text.secondary" }}>
            {service.issue_description}
          </Typography>
        </Box>

        <form
          id="service-form"
          onSubmit={(e) => {
            e.preventDefault();
            onUpdate(service.id, { diagnosis, status, estimated_cost: cost });
          }}
        >
          <Grid container spacing={2}>
            <Grid size={12}>
              <TextField
                label="Diagnóstico"
                fullWidth
                multiline
                rows={3}
                value={diagnosis}
                onChange={(e) => setDiagnosis(e.target.value)}
                placeholder="Resultado de la inspección..."
              />
            </Grid>
            <Grid size={6}>
              <FormControl fullWidth>
                <InputLabel>Estado</InputLabel>
                <Select
                  label="Estado"
                  value={status}
                  onChange={(e) => setStatus(e.target.value)}
                >
                  {Object.entries(STATUS_CONFIG).map(([key, val]) => (
                    <MenuItem key={key} value={key}>{val.label}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid size={6}>
              <TextField
                label="Costo Estimado (S/)"
                type="number"
                fullWidth
                slotProps={{ htmlInput: { min: 0, step: 0.01 } }}
                value={cost}
                onChange={(e) => setCost(Number(e.target.value))}
              />
            </Grid>
          </Grid>
        </form>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 3, gap: 1 }}>
        <Button onClick={onClose} variant="outlined" sx={{ textTransform: "none" }}>
          Cancelar
        </Button>
        <Button type="submit" form="service-form" variant="contained" sx={{ textTransform: "none", fontWeight: 700, bgcolor: "#0C3A6E" }}>
          Guardar Cambios
        </Button>
      </DialogActions>
    </Dialog>
  );
}
