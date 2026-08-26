"use client";

/**
 * Sección de confianza de la portada.
 *
 * Está escrita para el cliente, no para explicar la implementación: dice qué
 * lo protege y por qué puede comprar tranquilo. El detalle técnico del modelo
 * de detección de fraude vive en el panel de administración.
 */

import { Box, Container, Grid, Typography, Stack } from "@mui/material";
import { DISPLAY_FONT } from "@/components/ThemeProvider";
import ShieldOutlinedIcon from "@mui/icons-material/ShieldOutlined";
import LockOutlinedIcon from "@mui/icons-material/LockOutlined";
import AutorenewOutlinedIcon from "@mui/icons-material/AutorenewOutlined";

const PILLARS = [
  {
    icon: ShieldOutlinedIcon,
    title: "Cada pedido se revisa",
    desc: "Un sistema inteligente analiza cada compra y detiene las operaciones sospechosas antes de procesarlas.",
  },
  {
    icon: LockOutlinedIcon,
    title: "Pago protegido",
    desc: "Tus datos de tarjeta se procesan en la pasarela de pago. La tienda nunca los almacena.",
  },
  {
    icon: AutorenewOutlinedIcon,
    title: "Garantía y cambios",
    desc: "12 meses de garantía en todos los productos y 7 días para solicitar un cambio.",
  },
];

export default function FraudSection() {
  return (
    <Box
      id="seguridad"
      sx={{
        position: "relative",
        bgcolor: "primary.dark",
        color: "#e2e8f0",
        py: { xs: 6, md: 8 },
        overflow: "hidden",
      }}
    >
      <Box
        aria-hidden
        sx={{
          position: "absolute", top: -160, right: -120, width: 440, height: 440,
          borderRadius: "50%", pointerEvents: "none",
          background: "radial-gradient(circle, rgba(255,206,0,0.16) 0%, rgba(255,206,0,0) 70%)",
        }}
      />

      <Container maxWidth="lg" sx={{ position: "relative" }}>
        <Box sx={{ textAlign: "center", maxWidth: 620, mx: "auto", mb: { xs: 4.5, md: 6 } }}>
          <Typography
            variant="h3"
            sx={{ fontFamily: DISPLAY_FONT, fontSize: { xs: "1.7rem", md: "2.3rem" }, lineHeight: 1.2, color: "#FFFFFF" }}
          >
            Compra con confianza
          </Typography>
          <Typography
            sx={{ mt: 1.8, color: "#94a3b8", fontSize: { xs: "1rem", md: "1.08rem" }, lineHeight: 1.7 }}
          >
            Protegemos cada compra de principio a fin, para que lo único que tengas
            que decidir sea qué componente llevarte.
          </Typography>
        </Box>

        <Grid container spacing={{ xs: 3, md: 4 }}>
          {PILLARS.map((p) => (
            <Grid size={{ xs: 12, md: 4 }} key={p.title}>
              <Stack
                spacing={1.5}
                sx={{
                  alignItems: { xs: "flex-start", md: "center" },
                  textAlign: { xs: "left", md: "center" },
                }}
              >
                <Box
                  sx={{
                    width: 52, height: 52, borderRadius: 2.5,
                    display: "flex", alignItems: "center", justifyContent: "center",
                    bgcolor: "rgba(255,206,0,0.16)", color: "secondary.main",
                  }}
                >
                  <p.icon />
                </Box>
                <Typography variant="h6" sx={{ fontWeight: 700, color: "#FFFFFF" }}>
                  {p.title}
                </Typography>
                <Typography variant="body2" sx={{ color: "#94a3b8", lineHeight: 1.75, maxWidth: 320 }}>
                  {p.desc}
                </Typography>
              </Stack>
            </Grid>
          ))}
        </Grid>
      </Container>
    </Box>
  );
}
