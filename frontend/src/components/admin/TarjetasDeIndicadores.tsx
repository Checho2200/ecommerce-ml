"use client";

/**
 * Los tres indicadores que mide la tesis, con la dirección en la que conviene
 * que se muevan.
 *
 * Un porcentaje suelto no dice nada: "42 %" solo significa algo cuando al lado
 * está escrito si eso debería subir o bajar. Por eso cada tarjeta lleva su
 * flecha y su leyenda, y por eso la flecha es del color que corresponde al
 * sentido —no al signo del cambio—: la tasa de fraude no detectado bajando es
 * una buena noticia.
 *
 * El mismo componente sirve para el Antifraude, donde va con todo el detalle,
 * y para el Dashboard, donde va en `compacto` y solo enseña las tres cifras.
 */

import { Box, Card, CardContent, Grid, Skeleton, Stack, Tooltip, Typography } from "@mui/material";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import TrendingDownIcon from "@mui/icons-material/TrendingDown";
import ShieldOutlinedIcon from "@mui/icons-material/ShieldOutlined";
import ReportGmailerrorredOutlinedIcon from "@mui/icons-material/ReportGmailerrorredOutlined";
import BoltOutlinedIcon from "@mui/icons-material/BoltOutlined";
import type { SvgIconComponent } from "@mui/icons-material";
import type { FraudHistoryResponse } from "@/lib/api";

type Direccion = "subir" | "bajar";

interface Indicador {
  clave: string;
  titulo: string;
  valor: string;
  detalle: string;
  explicacion: string;
  direccion: Direccion;
  icono: SvgIconComponent;
  /** Sin fraudes confirmados en el rango, la tasa no se puede calcular. */
  medible: boolean;
}

const porcentaje = (v: number | null) => (v === null ? "—" : `${(v * 100).toFixed(1)} %`);

export function indicadoresDe(datos: FraudHistoryResponse | null): Indicador[] {
  const medible = (datos?.total_actual_frauds ?? 0) > 0;
  const confirmados = datos?.total_actual_frauds ?? 0;

  return [
    {
      clave: "detectados",
      titulo: "Tasa de fraudes detectados",
      valor: porcentaje(datos?.detection_rate ?? null),
      detalle: medible
        ? `${datos?.total_detected_frauds ?? 0} de ${confirmados} fraudes confirmados`
        : "Sin fraudes confirmados en el rango",
      explicacion:
        "De los fraudes confirmados, qué proporción frenó el modelo antes de cobrar.",
      direccion: "subir",
      icono: ShieldOutlinedIcon,
      medible,
    },
    {
      clave: "no-detectados",
      titulo: "Tasa de fraude no detectado",
      valor: porcentaje(datos?.undetected_rate ?? null),
      detalle: medible
        ? `${datos?.total_undetected_frauds ?? 0} de ${confirmados} se aprobaron igual`
        : "Sin fraudes confirmados en el rango",
      explicacion:
        "De los fraudes confirmados, qué proporción se aprobó igual y terminó en pérdida.",
      direccion: "bajar",
      icono: ReportGmailerrorredOutlinedIcon,
      medible,
    },
    {
      clave: "tiempo",
      titulo: "Tiempo de detección",
      valor: `${(datos?.average_detection_time_ms ?? 0).toFixed(1)} ms`,
      detalle: `Promedio sobre ${datos?.total_evaluations ?? 0} evaluaciones`,
      explicacion:
        "Cuánto tarda el modelo en evaluar una compra. Se le suma al cliente que espera en el checkout.",
      direccion: "bajar",
      icono: BoltOutlinedIcon,
      // El tiempo no necesita etiquetas: lo cronometra el propio servicio.
      medible: (datos?.total_evaluations ?? 0) > 0,
    },
  ];
}

function Flecha({ direccion }: { direccion: Direccion }) {
  const Icono = direccion === "subir" ? TrendingUpIcon : TrendingDownIcon;
  return (
    <Stack direction="row" spacing={0.5} sx={{ alignItems: "center" }}>
      <Icono sx={{ fontSize: 16, color: "text.secondary" }} />
      <Typography variant="caption" sx={{ color: "text.secondary", fontWeight: 700 }}>
        Debe {direccion}
      </Typography>
    </Stack>
  );
}

export default function TarjetasDeIndicadores({
  datos,
  cargando,
  compacto = false,
}: {
  datos: FraudHistoryResponse | null;
  cargando: boolean;
  /** Versión reducida para el Dashboard: solo las tres cifras. */
  compacto?: boolean;
}) {
  const indicadores = indicadoresDe(datos);

  if (compacto) {
    return (
      <Stack
        direction={{ xs: "column", sm: "row" }}
        spacing={{ xs: 1.5, sm: 3 }}
        sx={{ flexWrap: "wrap" }}
      >
        {indicadores.map((i) => (
          <Tooltip key={i.clave} title={`${i.explicacion} Debe ${i.direccion}.`}>
            <Stack direction="row" spacing={1.2} sx={{ alignItems: "center" }}>
              <i.icono sx={{ fontSize: 20, color: "acento.main" }} />
              <Box>
                <Typography variant="caption" sx={{ color: "text.secondary", display: "block", lineHeight: 1.2 }}>
                  {i.titulo}
                </Typography>
                {cargando ? (
                  <Skeleton width={54} height={22} />
                ) : (
                  <Typography sx={{ fontWeight: 900, fontSize: "1.05rem", lineHeight: 1.25 }}>
                    {i.valor}
                  </Typography>
                )}
              </Box>
            </Stack>
          </Tooltip>
        ))}
      </Stack>
    );
  }

  return (
    <Grid container spacing={3}>
      {indicadores.map((i) => (
        <Grid size={{ xs: 12, md: 4 }} key={i.clave}>
          <Card
            elevation={0}
            sx={{ borderRadius: 3, border: "1px solid", borderColor: "divider", height: "100%" }}
          >
            <CardContent sx={{ p: 3 }}>
              <Stack
                direction="row"
                sx={{ justifyContent: "space-between", alignItems: "flex-start", mb: 1.5, gap: 1 }}
              >
                <Typography
                  variant="body2"
                  sx={{
                    color: "text.secondary",
                    fontWeight: 700,
                    textTransform: "uppercase",
                    fontSize: "0.7rem",
                    lineHeight: 1.4,
                  }}
                >
                  {i.titulo}
                </Typography>
                <i.icono sx={{ fontSize: 21, color: "acento.main", flexShrink: 0 }} />
              </Stack>

              {cargando ? (
                <Skeleton width={110} height={46} />
              ) : (
                <Typography
                  variant="h4"
                  sx={{ fontWeight: 900, color: i.medible ? "text.primary" : "text.disabled" }}
                >
                  {i.valor}
                </Typography>
              )}

              <Typography variant="caption" sx={{ color: "text.secondary", display: "block", mt: 0.8 }}>
                {i.detalle}
              </Typography>

              <Box sx={{ mt: 2, pt: 1.5, borderTop: "1px solid", borderColor: "divider" }}>
                <Flecha direccion={i.direccion} />
                <Typography
                  variant="caption"
                  sx={{ color: "text.secondary", display: "block", mt: 0.8, lineHeight: 1.6 }}
                >
                  {i.explicacion}
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      ))}
    </Grid>
  );
}
