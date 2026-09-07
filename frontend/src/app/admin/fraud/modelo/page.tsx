"use client";

/**
 * Antifraude · Modelo e indicadores: cómo decide y qué tan bien le va.
 *
 * Es la mitad analítica de lo que antes era una sola pantalla larguísima. Se
 * separó de la cola de revisión porque son dos usos distintos: la cola se
 * atiende hoy, y esto se consulta cuando alguien pregunta —un jurado, un
 * gerente— por qué el sistema bloqueó una compra o cuánto fraude está
 * frenando de verdad.
 *
 * El orden sigue el de esas preguntas: primero cómo llega el modelo a una
 * decisión, luego qué prometió medir, después cómo le está yendo, y al final
 * cómo ha ido en el tiempo.
 */

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Alert,
  Box,
  Button,
  Snackbar,
  Stack,
  Typography,
} from "@mui/material";
import FactCheckOutlinedIcon from "@mui/icons-material/FactCheckOutlined";

import ComoDecideElModelo from "@/components/admin/ComoDecideElModelo";
import PorQueLightGBM from "@/components/admin/PorQueLightGBM";
import MetricasDelModelo from "@/components/admin/MetricasDelModelo";
import TarjetasDeIndicadores from "@/components/admin/TarjetasDeIndicadores";
import HistorialAntifraude, { type Granularidad } from "@/components/admin/HistorialAntifraude";
import {
  api,
  type FraudHistoryResponse,
  type FraudLogResponse,
  type FraudMetricsResponse,
  type FraudModelInfo,
  type ModelComparisonResponse,
} from "@/lib/api";

export default function AdminFraudModelPage() {
  const [metricas, setMetricas] = useState<FraudMetricsResponse | null>(null);
  const [modelo, setModelo] = useState<FraudModelInfo | null>(null);
  // Una evaluación reciente con la que enseñar la aritmética de una decisión.
  // Se prefiere una que el modelo no haya aprobado: en un pedido bloqueado los
  // aportes son grandes y el reparto se lee de un vistazo, mientras que en uno
  // aprobado son todos pequeños y negativos.
  const [ejemplo, setEjemplo] = useState<FraudLogResponse | null>(null);
  const [comparacion, setComparacion] = useState<ModelComparisonResponse | null>(null);
  const [granularidad, setGranularidad] = useState<Granularidad>("month");
  const [cargando, setCargando] = useState(true);
  const [aviso, setAviso] = useState<{ texto: string; tipo: "success" | "error" } | null>(null);
  const [exportando, setExportando] = useState(false);

  // El historial se guarda junto a la escala con la que se pidió. Así "está
  // cargando" es algo que se deduce —lo que hay en pantalla todavía no es de
  // la escala elegida— en lugar de un estado aparte que hay que encender a
  // mano dentro del efecto, que es lo que encadena un render de más en cada
  // cambio de escala.
  const [historial, setHistorial] = useState<{
    datos: FraudHistoryResponse | null;
    escala: Granularidad | null;
    fallo: boolean;
  }>({ datos: null, escala: null, fallo: false });

  const cargandoHistorial = historial.escala !== granularidad;

  const avisar = (texto: string, tipo: "success" | "error" = "success") =>
    setAviso({ texto, tipo });

  // Las métricas y la ficha del modelo no dependen de la escala elegida; el
  // historial sí. Separarlos evita volver a pedirlo todo al cambiar de escala.
  useEffect(() => {
    let vigente = true;
    Promise.all([
      api.fraud.getMetrics(),
      api.fraud.model(),
      api.fraud.getLogs(),
      api.fraud.comparison(),
    ])
      .then(([m, info, registros, tabla]) => {
        if (!vigente) return;
        setMetricas(m);
        setModelo(info);
        setComparacion(tabla);
        const conCuenta = registros.filter((r) => r.contributions);
        setEjemplo(
          conCuenta.find((r) => r.decision !== "APPROVED") ?? conCuenta[0] ?? null
        );
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
  }, []);

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
   * Descarga el reporte de indicadores.
   *
   * Lo arma el backend a partir de los mismos números que se ven en pantalla,
   * y en la escala que esté seleccionada: el archivo y el panel no pueden
   * decir cosas distintas.
   */
  const exportar = async () => {
    setExportando(true);
    try {
      await api.fraud.downloadReport({ granularity: granularidad });
      avisar("Reporte descargado");
    } catch (error: unknown) {
      avisar(
        error instanceof Error ? error.message : "No se pudo generar el reporte",
        "error"
      );
    } finally {
      setExportando(false);
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
            Modelo e indicadores
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            Cómo decide el modelo cada compra, y qué tan bien lo está haciendo.
          </Typography>
        </Box>
        <Button
          component={Link}
          href="/admin/fraud"
          variant="outlined"
          startIcon={<FactCheckOutlinedIcon />}
          sx={{ textTransform: "none", fontWeight: 700, borderRadius: 2, whiteSpace: "nowrap" }}
        >
          Ir a la revisión
        </Button>
      </Stack>

      <Stack spacing={3}>
        <PorQueLightGBM datos={comparacion} cargando={cargando} />

        <ComoDecideElModelo modelo={modelo} ejemplo={ejemplo} cargando={cargando} />

        {/* Los tres indicadores de la tesis van antes que el detalle: son lo
            que el sistema promete mover, y el resto explica cómo lo consigue. */}
        <Box>
          <Typography variant="subtitle1" sx={{ fontWeight: 800, mb: 0.5 }}>
            Indicadores del sistema
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2.5, maxWidth: 820 }}>
            Medidos sobre el rango que está seleccionado abajo. El modelo se entrena
            persiguiéndolos: al elegir sus umbrales descarta los que no detectan al
            menos el 80 % del fraude, y un modelo reentrenado no se publica si detecta
            menos que el que ya está sirviendo.
          </Typography>
          <TarjetasDeIndicadores
            datos={historial.datos}
            cargando={cargandoHistorial}
            modelo={modelo}
          />
        </Box>

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
          onExportar={exportar}
          exportando={exportando}
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
