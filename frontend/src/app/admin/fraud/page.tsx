"use client";

/**
 * Antifraude: todo lo que tiene que ver con el modelo, en un solo sitio.
 *
 * Antes estaba repartido en tres pantallas que no se hablaban: las métricas
 * ocupaban dos tercios del Dashboard, la cola de revisión había que armarla a
 * mano filtrando en Órdenes, y en ninguna parte se decía en qué momento del
 * checkout corre el modelo. El orden de esta página sigue el de las preguntas
 * que se hacen sobre él: cuándo actúa, qué está esperando decisión, qué tan
 * bien lo hace, y cómo ha ido en el tiempo.
 */

import { useCallback, useEffect, useState } from "react";
import {
  Alert,
  Box,
  Snackbar,
  Stack,
  Typography,
} from "@mui/material";

import CuandoActuaElModelo from "@/components/admin/CuandoActuaElModelo";
import ColaDeRevision from "@/components/admin/ColaDeRevision";
import MetricasDelModelo from "@/components/admin/MetricasDelModelo";
import HistorialAntifraude, { type Granularidad } from "@/components/admin/HistorialAntifraude";
import {
  api,
  type FraudHistoryResponse,
  type FraudMetricsResponse,
  type OrderResponse,
} from "@/lib/api";

export default function AdminFraudPage() {
  const [metricas, setMetricas] = useState<FraudMetricsResponse | null>(null);
  const [retenidos, setRetenidos] = useState<OrderResponse[]>([]);
  const [granularidad, setGranularidad] = useState<Granularidad>("day");
  const [cargando, setCargando] = useState(true);
  const [aviso, setAviso] = useState<{ texto: string; tipo: "success" | "error" } | null>(null);

  // El historial se guarda junto a la escala con la que se pidió. Así "está
  // cargando" es algo que se deduce —lo que hay en pantalla todavía no es de
  // la escala elegida— en lugar de un estado aparte que hay que encender a
  // mano dentro del efecto, que es lo que encadena un render de más en cada
  // cambio de "Diario" a "Semanal".
  const [historial, setHistorial] = useState<{
    datos: FraudHistoryResponse | null;
    escala: Granularidad | null;
    fallo: boolean;
  }>({ datos: null, escala: null, fallo: false });

  const cargandoHistorial = historial.escala !== granularidad;

  const avisar = (texto: string, tipo: "success" | "error" = "success") =>
    setAviso({ texto, tipo });

  // Devuelve la cola en vez de guardarla: quien la pide decide cuándo tocar el
  // estado, y el efecto de abajo puede pedirla junto a las métricas sin
  // provocar dos repintados encadenados.
  const traerCola = useCallback(
    () => api.orders.list({ status: "FRAUD_REVIEW", per_page: 50 }).then((r) => r.items),
    []
  );

  // Las métricas y la cola no dependen de la escala elegida; el historial sí.
  // Separarlos evita volver a pedirlo todo cada vez que se toca "Semanal".
  useEffect(() => {
    let vigente = true;
    Promise.all([api.fraud.getMetrics(), traerCola()])
      .then(([m, cola]) => {
        if (!vigente) return;
        setMetricas(m);
        setRetenidos(cola);
      })
      .catch(() => {
        if (vigente) avisar("No se pudieron cargar los datos del modelo", "error");
      })
      .finally(() => {
        if (vigente) setCargando(false);
      });
    return () => {
      vigente = false;
    };
  }, [traerCola]);

  useEffect(() => {
    let vigente = true;
    api.fraud
      .history({ granularity: granularidad })
      .then((datos) => {
        if (vigente) setHistorial({ datos, escala: granularidad, fallo: false });
      })
      .catch(() => {
        // La escala se anota igual: si no, la pantalla se quedaría cargando
        // para siempre después de un fallo.
        if (vigente) setHistorial({ datos: null, escala: granularidad, fallo: true });
      });
    return () => {
      vigente = false;
    };
  }, [granularidad]);

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
   * negativos y la precisión no se puede calcular.
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
      setMetricas(await api.fraud.getMetrics());
    } catch (error: unknown) {
      avisar(
        error instanceof Error ? error.message : "No se pudo registrar la etiqueta",
        "error"
      );
    }
  };

  return (
    <>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h5" sx={{ fontWeight: 800 }}>
          Antifraude
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
          El modelo que revisa cada compra: cuándo decide, qué decidió y qué tan bien lo hace.
        </Typography>
      </Box>

      <Stack spacing={3}>
        <CuandoActuaElModelo milisegundos={metricas?.average_detection_time_ms} />

        <ColaDeRevision
          pedidos={retenidos}
          cargando={cargando}
          onDecidir={decidir}
          onEtiquetar={etiquetar}
        />

        <MetricasDelModelo metricas={metricas} cargando={cargando} />

        {historial.fallo && (
          <Alert severity="error" sx={{ borderRadius: 2 }}>
            No se pudo cargar el historial. Vuelve a elegir una escala para reintentarlo.
          </Alert>
        )}

        <HistorialAntifraude
          datos={historial.datos}
          cargando={cargandoHistorial}
          granularidad={granularidad}
          onGranularidad={setGranularidad}
        />
      </Stack>

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
