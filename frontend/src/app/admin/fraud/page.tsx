"use client";

/**
 * Antifraude · Revisión: lo único que hay que hacer, y hacerlo.
 *
 * Esta pantalla y la de al lado —«Modelo e indicadores»— eran una sola, y era
 * demasiada. Mezclaba dos cosas que se usan en momentos distintos: explicar
 * cómo razona el modelo y medir cómo le va, que se miran de vez en cuando, con
 * la cola de pedidos retenidos, que hay que atender hoy porque mientras tanto
 * el cliente no puede pagar y su stock sigue apartado. Con todo junto, lo
 * urgente quedaba debajo de cuatrocientos píxeles de explicación.
 *
 * Aquí queda solo lo urgente. La teoría y los números están a un clic.
 */

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  Alert,
  Box,
  Button,
  Snackbar,
  Stack,
  Typography,
} from "@mui/material";
import InsightsOutlinedIcon from "@mui/icons-material/InsightsOutlined";

import ColaDeRevision from "@/components/admin/ColaDeRevision";
import { api, type OrderResponse } from "@/lib/api";

export default function AdminFraudPage() {
  const [retenidos, setRetenidos] = useState<OrderResponse[]>([]);
  const [cargando, setCargando] = useState(true);
  const [fallo, setFallo] = useState(false);
  const [aviso, setAviso] = useState<{ texto: string; tipo: "success" | "error" } | null>(null);

  const avisar = (texto: string, tipo: "success" | "error" = "success") =>
    setAviso({ texto, tipo });

  // Devuelve la cola en vez de guardarla: quien la pide decide cuándo tocar el
  // estado, y así una decisión puede refrescarla sin duplicar el manejo.
  const traerCola = useCallback(
    () => api.orders.list({ status: "FRAUD_REVIEW", per_page: 50 }).then((r) => r.items),
    []
  );

  useEffect(() => {
    let vigente = true;
    traerCola()
      .then((cola) => {
        if (vigente) {
          setRetenidos(cola);
          setFallo(false);
        }
      })
      .catch(() => {
        if (vigente) setFallo(true);
      })
      .finally(() => {
        if (vigente) setCargando(false);
      });
    return () => {
      vigente = false;
    };
  }, [traerCola]);

  /**
   * Qué se hace con un pedido retenido.
   *
   * Dejarlo pasar usa el endpoint de liberación y no un cambio de estado a
   * secas: además de moverlo a PENDING le genera el enlace de pago que nunca
   * tuvo. Rechazarlo lo cierra y devuelve su stock. Ninguna de las dos toca la
   * etiqueta del modelo: son decisiones distintas y se registran por separado.
   */
  const decidir = async (pedido: OrderResponse, aprobar: boolean) => {
    try {
      if (aprobar) {
        await api.orders.release(pedido.id);
      } else {
        await api.orders.updateStatus(pedido.id, "REJECTED");
      }
      avisar(aprobar ? "El pedido ya puede pagarse" : "Pedido rechazado");
      setRetenidos(await traerCola());
    } catch (error: unknown) {
      avisar(
        error instanceof Error ? error.message : "No se pudo actualizar el pedido",
        "error"
      );
    }
  };

  /**
   * Qué aprende el modelo de este caso.
   *
   * Las dos respuestas cuentan: sin los "era legítima" no hay verdaderos
   * negativos, y sin ellos la precisión del modelo no se puede calcular.
   */
  const etiquetar = async (fraudLogId: string, fueFraude: boolean) => {
    if (
      fueFraude &&
      !window.confirm(
        "¿Confirmas que este pedido terminó en un contracargo? Se usará para medir y reentrenar el modelo."
      )
    ) {
      return;
    }
    try {
      await api.fraud.label(fraudLogId, fueFraude);
      avisar(fueFraude ? "Registrado como fraude real" : "Registrado como compra legítima");
    } catch (error: unknown) {
      avisar(
        error instanceof Error ? error.message : "No se pudo registrar la etiqueta",
        "error"
      );
    }
  };

  return (
    <>
      <Stack
        direction={{ xs: "column", sm: "row" }}
        spacing={2}
        sx={{ justifyContent: "space-between", alignItems: { sm: "center" }, mb: 4 }}
      >
        <Box>
          <Typography variant="h5" sx={{ fontWeight: 800 }}>
            Antifraude · Revisión
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            Las compras que el modelo no dejó pasar y esperan una decisión.
          </Typography>
        </Box>
        <Button
          component={Link}
          href="/admin/fraud/modelo"
          variant="outlined"
          startIcon={<InsightsOutlinedIcon />}
          sx={{ textTransform: "none", fontWeight: 700, borderRadius: 2, whiteSpace: "nowrap" }}
        >
          Modelo e indicadores
        </Button>
      </Stack>

      {fallo && (
        <Alert severity="error" sx={{ mb: 3, borderRadius: 2 }}>
          No se pudo cargar la cola de revisión. Vuelve a cargar la página para reintentarlo.
        </Alert>
      )}

      <ColaDeRevision
        pedidos={retenidos}
        cargando={cargando}
        onDecidir={decidir}
        onEtiquetar={etiquetar}
      />

      <Snackbar
        open={!!aviso}
        autoHideDuration={3000}
        onClose={() => setAviso(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
      >
        <Alert
          severity={aviso?.tipo}
          variant="filled"
          onClose={() => setAviso(null)}
          sx={{ width: "100%" }}
        >
          {aviso?.texto}
        </Alert>
      </Snackbar>
    </>
  );
}
