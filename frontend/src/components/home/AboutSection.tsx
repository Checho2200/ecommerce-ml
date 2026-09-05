"use client";

/**
 * Portada: quiénes somos y cómo contactarnos.
 *
 * Cierra la página: es a la vez la presentación de la empresa y la última
 * llamada a la acción. Antes eran dos bloques —éste y una franja azul de
 * "¿No encuentras lo que buscas?"— que repetían los mismos dos botones y el
 * mismo WhatsApp que ya ofrecen el botón flotante y el pie de página.
 *
 * Los datos de la empresa son reales (gruposts.com.pe); no se inventan cifras
 * ni servicios que no presta.
 */

import Link from "next/link";
import { Box, Button, Container, Grid, Stack, Typography } from "@mui/material";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import LocationOnOutlinedIcon from "@mui/icons-material/LocationOnOutlined";
import SafeImage from "@/components/ui/SafeImage";
import { DISPLAY_FONT } from "@/components/ThemeProvider";

const WHATSAPP =
  "https://wa.me/51975021947?text=" +
  encodeURIComponent("Hola, vengo de la tienda en línea y quisiera una cotización.");

const CIFRAS = [
  { valor: "+30", detalle: "años en el mercado tecnológico" },
  { valor: "2", detalle: "regiones: La Libertad y Piura" },
  { valor: "6", detalle: "días de atención, de lunes a sábado" },
];

export default function AboutSection() {
  return (
    <Container component="section" maxWidth="lg" sx={{ py: { xs: 6, md: 9 } }}>
      <Grid container spacing={{ xs: 4, md: 7 }} sx={{ alignItems: "center" }}>
        <Grid size={{ xs: 12, md: 6 }} sx={{ order: { xs: 1, md: 2 } }}>
          <Box sx={{ aspectRatio: "16/10", overflow: "hidden" }}>
            <SafeImage
              src="/brand/equipo.webp"
              alt="Equipo de Grupo STS SAC"
              objectFit="cover"
            />
          </Box>
        </Grid>

        <Grid size={{ xs: 12, md: 6 }} sx={{ order: { xs: 2, md: 1 } }}>
          <Typography
            component="h2"
            sx={{
              fontFamily: DISPLAY_FONT,
              color: "acento.main",
              fontSize: { xs: "1.5rem", md: "2rem" },
              lineHeight: 1.15,
            }}
          >
            Detrás de la tienda hay un taller
          </Typography>

          <Typography color="text.secondary" sx={{ mt: 2, lineHeight: 1.8 }}>
            Somos una empresa trujillana con más de treinta años en el mercado
            tecnológico y presencia en La Libertad y Piura. Además de vender
            componentes, atendemos soporte técnico de equipos informáticos,
            servidores de datos y administración de redes y comunicaciones: lo
            que compras aquí lo respalda gente que repara estos equipos todos
            los días.
          </Typography>

          <Stack
            direction="row"
            spacing={{ xs: 2.5, md: 4 }}
            sx={{ mt: 3.5, flexWrap: "wrap", rowGap: 2 }}
          >
            {CIFRAS.map((c) => (
              <Box key={c.valor} sx={{ maxWidth: 140 }}>
                {/* El oro se queda en la regla, no en el número: sobre fondo
                    claro no llega al contraste mínimo ni en tamaño grande. */}
                <Box aria-hidden sx={{ width: 26, height: 3, bgcolor: "secondary.main", mb: 1.2 }} />
                <Typography
                  sx={{
                    fontFamily: DISPLAY_FONT,
                    fontSize: "1.9rem",
                    lineHeight: 1,
                    color: "acento.main",
                  }}
                >
                  {c.valor}
                </Typography>
                <Typography
                  sx={{ mt: 0.6, fontSize: "0.78rem", color: "text.secondary", lineHeight: 1.4 }}
                >
                  {c.detalle}
                </Typography>
              </Box>
            ))}
          </Stack>

          <Stack direction="row" spacing={1} sx={{ mt: 3.5, alignItems: "flex-start" }}>
            <LocationOnOutlinedIcon
              sx={{ color: "acento.main", fontSize: 19, mt: 0.2, flexShrink: 0 }}
            />
            <Typography variant="body2" color="text.secondary">
              Jr. Alfonso Ugarte 493 — Centro Histórico de Trujillo
            </Typography>
          </Stack>

          <Stack
            direction={{ xs: "column", sm: "row" }}
            spacing={1.5}
            sx={{ mt: 3.5 }}
          >
            {/* Los dos botones se pintan con `acento` y no con `primary`: en
                modo oscuro el navy se confunde con el fondo de la página. */}
            <Button
              component={Link}
              href="/services"
              variant="contained"
              endIcon={<ArrowForwardIcon />}
              sx={{
                px: 3,
                py: 1.25,
                fontWeight: 700,
                bgcolor: "acento.main",
                color: "acento.contrastText",
                "&:hover": { bgcolor: "acento.dark" },
              }}
            >
              Solicitar servicio técnico
            </Button>
            <Button
              component="a"
              href={WHATSAPP}
              target="_blank"
              rel="noopener noreferrer"
              variant="outlined"
              sx={{
                px: 3,
                py: 1.25,
                fontWeight: 700,
                color: "acento.main",
                borderColor: "acento.main",
                "&:hover": { borderColor: "acento.dark", bgcolor: "action.hover" },
              }}
            >
              Cotizar por WhatsApp
            </Button>
          </Stack>
        </Grid>
      </Grid>
    </Container>
  );
}
