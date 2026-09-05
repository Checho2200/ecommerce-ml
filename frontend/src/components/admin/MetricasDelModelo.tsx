"use client";

/**
 * Rendimiento del modelo: aciertos, errores y lo que cuesta cada uno.
 *
 * Vivía en el Dashboard, donde ocupaba dos tercios de la pantalla y empujaba
 * hacia abajo las cifras de la tienda. Un panel general no es el sitio para el
 * detalle de un subsistema: aquí, junto al historial y a la cola de revisión,
 * las tres cosas se leen como una sola.
 */

import {
  Box,
  Card,
  CardContent,
  Grid,
  Skeleton,
  Stack,
  Typography,
} from "@mui/material";
import DoneAllIcon from "@mui/icons-material/DoneAll";
import RuleIcon from "@mui/icons-material/Rule";
import PsychologyIcon from "@mui/icons-material/Psychology";
import PaidOutlinedIcon from "@mui/icons-material/PaidOutlined";
import type { FraudMetricsResponse } from "@/lib/api";

const soles = (monto: number) =>
  `S/ ${monto.toLocaleString("es-PE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

function Tarjeta({
  titulo,
  valor,
  pie,
  icono,
  cargando,
}: {
  titulo: string;
  valor: string;
  pie: string;
  icono: React.ReactNode;
  cargando: boolean;
}) {
  return (
    <Card
      elevation={0}
      sx={{ borderRadius: 3, border: "1px solid", borderColor: "divider", height: "100%" }}
    >
      <CardContent sx={{ p: 3 }}>
        <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "center", mb: 2 }}>
          <Typography
            variant="body2"
            sx={{
              color: "text.secondary",
              fontWeight: 600,
              textTransform: "uppercase",
              fontSize: "0.72rem",
            }}
          >
            {titulo}
          </Typography>
          {icono}
        </Stack>
        {cargando ? (
          <Skeleton width={80} height={40} />
        ) : (
          <Typography variant="h4" sx={{ fontWeight: 900 }}>
            {valor}
          </Typography>
        )}
        <Typography variant="caption" sx={{ color: "text.secondary", display: "block", mt: 1 }}>
          {pie}
        </Typography>
      </CardContent>
    </Card>
  );
}

function Lista({
  titulo,
  icono,
  filas,
  nota,
}: {
  titulo: string;
  icono?: React.ReactNode;
  filas: { etiqueta: string; valor: string | number; color?: string }[];
  nota?: string;
}) {
  return (
    <Card
      elevation={0}
      sx={{ borderRadius: 3, border: "1px solid", borderColor: "divider", height: "100%" }}
    >
      <CardContent sx={{ p: 3 }}>
        <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "center", mb: 2 }}>
          <Typography
            variant="body2"
            sx={{
              color: "text.secondary",
              fontWeight: 600,
              textTransform: "uppercase",
              fontSize: "0.72rem",
            }}
          >
            {titulo}
          </Typography>
          {icono}
        </Stack>
        {filas.map((fila) => (
          <Stack
            key={fila.etiqueta}
            direction="row"
            sx={{ justifyContent: "space-between", py: 0.75, gap: 2 }}
          >
            <Typography variant="body2" sx={{ color: "text.secondary" }}>
              {fila.etiqueta}
            </Typography>
            <Typography
              variant="body2"
              sx={{ fontWeight: 800, color: fila.color ?? "text.primary", whiteSpace: "nowrap" }}
            >
              {fila.valor}
            </Typography>
          </Stack>
        ))}
        {nota && (
          <Typography variant="caption" sx={{ color: "text.secondary", display: "block", mt: 1.5 }}>
            {nota}
          </Typography>
        )}
      </CardContent>
    </Card>
  );
}

export default function MetricasDelModelo({
  metricas,
  cargando,
}: {
  metricas: FraudMetricsResponse | null;
  cargando: boolean;
}) {
  return (
    <Box>
      <Typography variant="subtitle1" sx={{ fontWeight: 800, mb: 0.5 }}>
        Rendimiento del modelo
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ display: "block", mb: 2.5, maxWidth: 820 }}>
        Calculado sobre los {metricas?.reviewed_count ?? 0} pedidos ya revisados y
        etiquetados, de {metricas?.total_evaluations ?? 0} evaluados. Un pedido bloqueado
        nunca llega a cobrarse, así que nunca tendrá un contracargo que lo confirme: los
        aciertos más valiosos del modelo son también los más difíciles de etiquetar, y estas
        cifras los subestiman.
      </Typography>

      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid size={{ xs: 12, md: 4 }}>
          <Tarjeta
            titulo="Precisión"
            valor={`${metricas?.precision ?? 0}%`}
            pie="De cada alerta, cuántas eran fraude de verdad"
            icono={<DoneAllIcon color="success" />}
            cargando={cargando}
          />
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <Tarjeta
            titulo="Exhaustividad (recall)"
            valor={`${metricas?.recall ?? 0}%`}
            pie="De los fraudes reales, cuántos alcanzó a detectar"
            icono={<RuleIcon color="primary" />}
            cargando={cargando}
          />
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <Tarjeta
            titulo="F1"
            valor={`${metricas?.f1_score ?? 0}%`}
            pie="El equilibrio entre las dos anteriores"
            icono={<PsychologyIcon color="secondary" />}
            cargando={cargando}
          />
        </Grid>
      </Grid>

      <Grid container spacing={3}>
        <Grid size={{ xs: 12, md: 6 }}>
          <Lista
            titulo="Matriz de confusión"
            filas={[
              { etiqueta: "Fraudes detectados", valor: metricas?.true_positives ?? 0, color: "success.main" },
              { etiqueta: "Fraudes que se escaparon", valor: metricas?.false_negatives ?? 0, color: "error.main" },
              { etiqueta: "Falsas alarmas", valor: metricas?.false_positives ?? 0, color: "warning.main" },
              { etiqueta: "Compras buenas bien aprobadas", valor: metricas?.true_negatives ?? 0 },
            ]}
          />
        </Grid>

        <Grid size={{ xs: 12, md: 6 }}>
          <Lista
            titulo="Impacto en dinero"
            icono={<PaidOutlinedIcon color="success" />}
            filas={[
              { etiqueta: "Pérdida evitada", valor: soles(metricas?.loss_prevented ?? 0), color: "success.main" },
              { etiqueta: "Pérdida asumida", valor: soles(metricas?.loss_absorbed ?? 0), color: "error.main" },
              { etiqueta: "Ganancia no realizada", valor: soles(metricas?.revenue_lost ?? 0), color: "warning.main" },
            ]}
            nota="Frenar una compra buena no cuesta el pedido entero: cuesta el margen de esa venta."
          />
        </Grid>
      </Grid>
    </Box>
  );
}
