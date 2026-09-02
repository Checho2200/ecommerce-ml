"use client";

import { useState, useCallback } from "react";
import ServiceModal from "@/components/admin/ServicioModal";
import { ESTADOS_DE_SERVICIO, type EstadoDeServicio } from "@/lib/estados";
import { useRecurso } from "@/hooks/useRecurso";
import { api, type ServiceOrderResponse } from "@/lib/api";

// MUI
import {
  Box,
  Typography,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Paper,
  Skeleton,
  Pagination,
  IconButton,
  Tooltip,
  Snackbar,
  Alert,
  alpha,
} from "@mui/material";

// MUI Icons
import EditIcon from "@mui/icons-material/Edit";


export default function ServicesPage() {
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState("");
  const [selected, setSelected] = useState<ServiceOrderResponse | null>(null);
  const [snack, setSnack] = useState<{ msg: string; severity: "success" | "error" } | null>(null);

  const consultar = useCallback(
    () =>
      api.serviceOrders.list({
        page,
        status: statusFilter || undefined,
      }),
    [page, statusFilter]
  );


  // La carga, el estado de «cargando» y la recarga manual salen del hook
  // compartido: ver src/hooks/useRecurso.ts.
  const { datos, cargando: loading, recargar: recargarServicios } =
    useRecurso(consultar);

  const services = datos?.items ?? [];
  const total = datos?.total ?? 0;
  const pages = datos?.pages ?? 1;



  const showSnack = (msg: string, severity: "success" | "error" = "success") =>
    setSnack({ msg, severity });

  const handleUpdate = async (id: string, data: { diagnosis?: string; status?: string; estimated_cost?: number }) => {
    try {
      await api.serviceOrders.update(id, data);
      showSnack("Servicio actualizado");
      recargarServicios();
      setSelected(null);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Error";
      showSnack(message, "error");
    }
  };

  const FILTER_OPTIONS = [
    { value: "", label: "Todos" },
    ...Object.entries(ESTADOS_DE_SERVICIO).map(([key, val]) => ({ value: key, label: val.label })),
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
                const st = ESTADOS_DE_SERVICIO[s.status as EstadoDeServicio] || { label: s.status, color: "info" as const };
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
