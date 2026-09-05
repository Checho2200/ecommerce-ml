"use client";

/**
 * Portada: por qué se puede comprar tranquilo.
 *
 * Está escrita para el cliente, no para explicar la implementación: dice qué lo
 * protege y por qué puede comprar tranquilo. El detalle técnico del modelo de
 * detección de fraude vive en el panel de administración.
 *
 * Los colores salen del tema (antes eran grises de Tailwind escritos a mano,
 * que no seguían el modo oscuro) y las esquinas son rectas, como en el resto
 * del sitio.
 */

import { Box, Container, Grid, Stack, Typography } from "@mui/material";
import { DISPLAY_FONT } from "@/components/ThemeProvider";
import ShieldOutlinedIcon from "@mui/icons-material/ShieldOutlined";
import LockOutlinedIcon from "@mui/icons-material/LockOutlined";
import AutorenewOutlinedIcon from "@mui/icons-material/AutorenewOutlined";

const PILARES = [
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
    title: "Cambios y garantía",
    desc: "Tienes siete días para solicitar un cambio, además de los doce meses de garantía del producto.",
  },
];

export default function FraudSection() {
  return (
    <Box
      component="section"
      id="seguridad"
      sx={{
        bgcolor: "primary.dark",
        color: "#FFFFFF",
        borderTop: "1px solid rgba(255,206,0,0.35)",
      }}
    >
      <Container maxWidth="lg" sx={{ py: { xs: 6, md: 9 } }}>
        <Box sx={{ maxWidth: 560, mb: { xs: 4.5, md: 6 } }}>
          <Typography
            component="h2"
            sx={{
              fontFamily: DISPLAY_FONT,
              fontSize: { xs: "1.6rem", md: "2.1rem" },
              lineHeight: 1.15,
              color: "#FFFFFF",
            }}
          >
            Compra con confianza
          </Typography>
          <Typography
            sx={{
              mt: 2,
              color: "rgba(255,255,255,0.72)",
              fontSize: { xs: "0.98rem", md: "1.04rem" },
              lineHeight: 1.7,
            }}
          >
            Protegemos cada compra de principio a fin, para que lo único que
            tengas que decidir sea qué componente llevarte.
          </Typography>
        </Box>

        <Grid container spacing={{ xs: 3.5, md: 5 }}>
          {PILARES.map((p) => (
            <Grid size={{ xs: 12, sm: 6, md: 4 }} key={p.title}>
              <Stack spacing={1.6} sx={{ alignItems: "flex-start" }}>
                <Box
                  sx={{
                    width: 46,
                    height: 46,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    border: "1px solid rgba(255,206,0,0.45)",
                    color: "secondary.main",
                  }}
                >
                  <p.icon sx={{ fontSize: 22 }} />
                </Box>
                <Typography sx={{ fontWeight: 700, fontSize: "1.02rem", color: "#FFFFFF" }}>
                  {p.title}
                </Typography>
                <Typography
                  sx={{
                    fontSize: "0.9rem",
                    color: "rgba(255,255,255,0.7)",
                    lineHeight: 1.75,
                    maxWidth: 330,
                  }}
                >
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
