"use client";

/**
 * Formulario de diagnóstico y estado de una orden de servicio técnico.
 *
 * Vivía dentro de `app/admin/services/page.tsx`, que así mezclaba la
 * pantalla con el formulario. Separado, cada archivo hace una sola cosa.
 */

import { useState } from "react";
import { ESTADOS_DE_SERVICIO } from "@/lib/estados";
import { type ServiceOrderResponse } from "@/lib/api";
import {
  Box,
  Typography,
  Button,
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
} from "@mui/material";

export default function ServiceModal({
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
                  {Object.entries(ESTADOS_DE_SERVICIO).map(([key, val]) => (
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
