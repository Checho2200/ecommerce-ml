"use client";

/**
 * Sección pública que explica la detección de fraude.
 *
 * Es intencionalmente estática: los datos que muestra (las cuatro variables y
 * los umbrales) están tomados del modelo real que corre en producción, pero no
 * se consultan en vivo. Así la sección se pinta al instante y no depende de que
 * el backend esté despierto, que es justo lo que no puede fallar en una demo.
 *
 * Fuente de los valores: backend/app/services/fraud_service.py
 */

import { Box, Container, Grid, Typography, Stack, Chip } from "@mui/material";
import PaymentsOutlinedIcon from "@mui/icons-material/PaymentsOutlined";
import WarningAmberOutlinedIcon from "@mui/icons-material/WarningAmberOutlined";
import TimerOutlinedIcon from "@mui/icons-material/TimerOutlined";
import WrongLocationOutlinedIcon from "@mui/icons-material/WrongLocationOutlined";
import ShoppingCartCheckoutIcon from "@mui/icons-material/ShoppingCartCheckout";
import TuneIcon from "@mui/icons-material/Tune";
import PsychologyOutlinedIcon from "@mui/icons-material/PsychologyOutlined";
import SpeedOutlinedIcon from "@mui/icons-material/SpeedOutlined";
import GavelOutlinedIcon from "@mui/icons-material/GavelOutlined";

const SURFACE = "rgba(255,255,255,0.04)";
const BORDER = "rgba(255,255,255,0.12)";
const MONO = "ui-monospace, SFMono-Regular, Menlo, monospace";

const PIPELINE = [
  { icon: ShoppingCartCheckoutIcon, title: "Pedido creado", desc: "El cliente confirma su compra" },
  { icon: TuneIcon, title: "Extracción de variables", desc: "Se calculan 4 señales de riesgo" },
  { icon: PsychologyOutlinedIcon, title: "Modelo LightGBM", desc: "Evalúa la probabilidad de fraude" },
  { icon: SpeedOutlinedIcon, title: "Puntaje de riesgo", desc: "Un valor entre 0.00 y 1.00" },
  { icon: GavelOutlinedIcon, title: "Decisión automática", desc: "Aprobar, revisar o bloquear" },
];

const FEATURES = [
  {
    icon: PaymentsOutlinedIcon,
    field: "total_amount",
    title: "Monto del pedido",
    desc: "El fraude se concentra en tickets altos, donde la pérdida por contracargo es mayor.",
  },
  {
    icon: WarningAmberOutlinedIcon,
    field: "high_risk_items_count",
    title: "Productos de alto riesgo",
    desc: "Tarjetas de video, procesadores, placas madre y monitores son de reventa fácil.",
  },
  {
    icon: TimerOutlinedIcon,
    field: "checkout_duration_seconds",
    title: "Duración del checkout",
    desc: "Una compra completada en segundos sugiere datos de tarjeta ya cargados.",
  },
  {
    icon: WrongLocationOutlinedIcon,
    field: "is_new_shipping_address",
    title: "Dirección nueva",
    desc: "Primer envío a una dirección que el cliente nunca había usado antes.",
  },
];

const THRESHOLDS = [
  {
    range: "0.00 – 0.30",
    decision: "APPROVED",
    label: "Se aprueba",
    desc: "El pedido continúa al pago con normalidad.",
    color: "#22c55e",
  },
  {
    range: "0.30 – 0.70",
    decision: "REVIEW",
    label: "Queda en revisión",
    desc: "Se marca para que un administrador lo revise antes de despacharlo.",
    color: "#f59e0b",
  },
  {
    range: "0.70 – 1.00",
    decision: "BLOCKED",
    label: "Se bloquea",
    desc: "El pedido se rechaza y el stock reservado vuelve al inventario.",
    color: "#ef4444",
  },
];

const TICKS = [
  { pos: "0%", label: "0.00", shift: "none" },
  { pos: "30%", label: "0.30", shift: "translateX(-50%)" },
  { pos: "70%", label: "0.70", shift: "translateX(-50%)" },
  { pos: "100%", label: "1.00", shift: "translateX(-100%)" },
];

export default function FraudSection() {
  return (
    <Box
      id="seguridad"
      sx={{
        position: "relative",
        bgcolor: "#0b1220",
        color: "#e2e8f0",
        py: { xs: 7, md: 11 },
        overflow: "hidden",
      }}
    >
      <Box
        aria-hidden
        sx={{
          position: "absolute", top: -140, right: -120, width: 460, height: 460,
          borderRadius: "50%", pointerEvents: "none",
          background: "radial-gradient(circle, rgba(37,99,235,0.28) 0%, rgba(37,99,235,0) 70%)",
        }}
      />

      <Container maxWidth="lg" sx={{ position: "relative" }}>
        <Box sx={{ textAlign: "center", maxWidth: 780, mx: "auto", mb: { xs: 5, md: 7 } }}>
          <Chip
            label="MACHINE LEARNING · LightGBM"
            size="small"
            sx={{
              bgcolor: "rgba(37,99,235,0.18)", color: "#93c5fd",
              border: "1px solid rgba(147,197,253,0.35)",
              fontWeight: 700, letterSpacing: 0.8, mb: 2.5,
            }}
          />
          <Typography
            variant="h3"
            sx={{ fontWeight: 900, fontSize: { xs: "1.9rem", md: "2.6rem" }, lineHeight: 1.2 }}
          >
            Cada pedido pasa por un modelo de detección de fraude
          </Typography>
          <Typography
            sx={{ mt: 2, color: "#94a3b8", fontSize: { xs: "1rem", md: "1.1rem" }, lineHeight: 1.75 }}
          >
            Antes de confirmar una compra, el sistema calcula un puntaje de riesgo en
            milisegundos y decide automáticamente si se aprueba, se envía a revisión o
            se bloquea. Sin intervención manual.
          </Typography>
        </Box>

        <Grid container spacing={2} sx={{ mb: { xs: 6, md: 8 } }}>
          {PIPELINE.map((step, i) => (
            <Grid size={{ xs: 12, sm: 6, md: 2.4 }} key={step.title}>
              <Box
                sx={{
                  height: "100%", p: 2.5, borderRadius: 3,
                  bgcolor: SURFACE, border: "1px solid", borderColor: BORDER,
                  textAlign: { xs: "left", md: "center" },
                }}
              >
                <Box
                  sx={{
                    width: 44, height: 44, borderRadius: 2,
                    display: "inline-flex", alignItems: "center", justifyContent: "center",
                    bgcolor: "rgba(37,99,235,0.22)", color: "#93c5fd", mb: 1.5,
                  }}
                >
                  <step.icon fontSize="small" />
                </Box>
                <Typography variant="caption" sx={{ display: "block", color: "#64748b", fontWeight: 700 }}>
                  PASO {i + 1}
                </Typography>
                <Typography variant="subtitle2" sx={{ fontWeight: 800, color: "#f1f5f9", mt: 0.3 }}>
                  {step.title}
                </Typography>
                <Typography variant="caption" sx={{ color: "#94a3b8", display: "block", mt: 0.5, lineHeight: 1.5 }}>
                  {step.desc}
                </Typography>
              </Box>
            </Grid>
          ))}
        </Grid>

        <Typography variant="h5" sx={{ fontWeight: 800, mb: 0.8, color: "#f1f5f9" }}>
          Las cuatro señales que analiza
        </Typography>
        <Typography sx={{ color: "#94a3b8", mb: 3.5 }}>
          Se calculan en el servidor al momento de crear el pedido, no en el navegador.
        </Typography>

        <Grid container spacing={2.5} sx={{ mb: { xs: 6, md: 8 } }}>
          {FEATURES.map((f) => (
            <Grid size={{ xs: 12, sm: 6, md: 3 }} key={f.field}>
              <Box
                sx={{
                  height: "100%", p: 3, borderRadius: 3,
                  bgcolor: SURFACE, border: "1px solid", borderColor: BORDER,
                  transition: "all 0.3s",
                  "&:hover": { borderColor: "rgba(147,197,253,0.5)", transform: "translateY(-4px)" },
                }}
              >
                <Box sx={{ color: "#facc15", mb: 1.5 }}>
                  <f.icon />
                </Box>
                <Typography variant="subtitle1" sx={{ fontWeight: 800, color: "#f1f5f9" }}>
                  {f.title}
                </Typography>
                <Typography
                  component="code"
                  sx={{
                    display: "inline-block", mt: 0.8, mb: 1.5,
                    fontFamily: MONO, fontSize: "0.72rem", color: "#93c5fd",
                    bgcolor: "rgba(37,99,235,0.16)", px: 1, py: 0.4, borderRadius: 1,
                  }}
                >
                  {f.field}
                </Typography>
                <Typography variant="body2" sx={{ color: "#94a3b8", lineHeight: 1.65 }}>
                  {f.desc}
                </Typography>
              </Box>
            </Grid>
          ))}
        </Grid>

        <Typography variant="h5" sx={{ fontWeight: 800, mb: 0.8, color: "#f1f5f9" }}>
          Cómo se decide
        </Typography>
        <Typography sx={{ color: "#94a3b8", mb: 3.5 }}>
          El puntaje cae en uno de tres tramos, y cada tramo dispara una acción distinta.
        </Typography>

        <Box sx={{ mb: 3 }}>
          <Box
            sx={{
              height: 14, borderRadius: 99, overflow: "hidden", display: "flex",
              border: "1px solid", borderColor: BORDER,
            }}
          >
            <Box sx={{ flex: 30, bgcolor: "#22c55e" }} />
            <Box sx={{ flex: 40, bgcolor: "#f59e0b" }} />
            <Box sx={{ flex: 30, bgcolor: "#ef4444" }} />
          </Box>
          <Box sx={{ position: "relative", height: 22, mt: 0.8 }}>
            {TICKS.map((t) => (
              <Typography
                key={t.label}
                variant="caption"
                sx={{
                  position: "absolute", left: t.pos, color: "#64748b",
                  fontFamily: MONO, transform: t.shift,
                }}
              >
                {t.label}
              </Typography>
            ))}
          </Box>
        </Box>

        <Grid container spacing={2.5}>
          {THRESHOLDS.map((t) => (
            <Grid size={{ xs: 12, md: 4 }} key={t.decision}>
              <Box
                sx={{
                  height: "100%", p: 3, borderRadius: 3,
                  bgcolor: SURFACE, border: "1px solid", borderColor: BORDER,
                  borderLeft: "4px solid", borderLeftColor: t.color,
                }}
              >
                <Stack direction="row" spacing={1} sx={{ alignItems: "center", mb: 1 }}>
                  <Box sx={{ width: 9, height: 9, borderRadius: "50%", bgcolor: t.color }} />
                  <Typography
                    component="code"
                    sx={{ fontFamily: MONO, fontSize: "0.75rem", fontWeight: 700, color: t.color, letterSpacing: 0.5 }}
                  >
                    {t.decision}
                  </Typography>
                  <Typography variant="caption" sx={{ ml: "auto", color: "#64748b", fontFamily: MONO }}>
                    {t.range}
                  </Typography>
                </Stack>
                <Typography variant="subtitle1" sx={{ fontWeight: 800, color: "#f1f5f9" }}>
                  {t.label}
                </Typography>
                <Typography variant="body2" sx={{ color: "#94a3b8", mt: 0.5, lineHeight: 1.65 }}>
                  {t.desc}
                </Typography>
              </Box>
            </Grid>
          ))}
        </Grid>

        <Typography
          variant="caption"
          sx={{ display: "block", textAlign: "center", color: "#475569", mt: 5, lineHeight: 1.8 }}
        >
          Modelo LightGBM con hiperparámetros optimizados por GridSearchCV y validación cruzada.
          <br />
          El sistema registra cada evaluación y puede reentrenarse con las transacciones reales de la tienda.
        </Typography>
      </Container>
    </Box>
  );
}
