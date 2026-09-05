"use client";

/**
 * Portada: bloque de apertura.
 *
 * Una sola promesa, una sola acción principal y la foto real de la tienda. La
 * versión anterior repartía el mensaje entre tres tarjetas de colores distintos
 * —azul, oro y blanca— que competían entre sí; aquí los datos de apoyo bajan a
 * una línea discreta al pie del bloque, que es donde el cliente los busca
 * después de decidir, no antes.
 */

import Link from "next/link";
import { Box, Button, Container, Grid, Stack, Typography } from "@mui/material";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import LocalShippingOutlinedIcon from "@mui/icons-material/LocalShippingOutlined";
import VerifiedUserOutlinedIcon from "@mui/icons-material/VerifiedUserOutlined";
import StorefrontOutlinedIcon from "@mui/icons-material/StorefrontOutlined";
import SafeImage from "@/components/ui/SafeImage";
import type { SvgIconComponent } from "@mui/icons-material";

const DATOS: { icon: SvgIconComponent; texto: string }[] = [
  { icon: LocalShippingOutlinedIcon, texto: "Envíos a todo el Perú en 24 a 48 h" },
  { icon: VerifiedUserOutlinedIcon, texto: "Garantía de 12 meses" },
  { icon: StorefrontOutlinedIcon, texto: "Tienda física en el centro de Trujillo" },
];

export default function Hero() {
  return (
    <Box component="section" sx={{ bgcolor: "primary.main", color: "#FFFFFF" }}>
      <Container maxWidth="lg" sx={{ py: { xs: 6, md: 9 } }}>
        <Grid container spacing={{ xs: 4, md: 7 }} sx={{ alignItems: "center" }}>
          <Grid size={{ xs: 12, md: 7 }}>
            <Typography
              component="p"
              sx={{
                color: "secondary.main",
                fontSize: { xs: 11, md: 12 },
                fontWeight: 800,
                letterSpacing: "0.16em",
                textTransform: "uppercase",
              }}
            >
              Grupo STS · Trujillo
            </Typography>

            <Typography
              variant="h1"
              sx={{
                mt: 2,
                color: "#FFFFFF",
                fontSize: { xs: "2.1rem", sm: "2.8rem", md: "3.4rem" },
                lineHeight: 1.04,
              }}
            >
              Todo para tu equipo,
              <br />
              con{" "}
              <Box component="span" sx={{ color: "secondary.main" }}>
                garantía real.
              </Box>
            </Typography>

            <Typography
              sx={{
                mt: 2.5,
                maxWidth: 480,
                color: "rgba(255,255,255,0.82)",
                fontSize: { xs: "1rem", md: "1.06rem" },
                lineHeight: 1.6,
              }}
            >
              Procesadores, tarjetas de video, memorias y periféricos originales,
              con el respaldo del taller que lleva más de 30 años armando y
              reparando equipos en la ciudad.
            </Typography>

            <Stack
              direction={{ xs: "column", sm: "row" }}
              spacing={1.5}
              sx={{ mt: 4, alignItems: { sm: "center" } }}
            >
              <Button
                component={Link}
                href="/catalog"
                variant="contained"
                color="secondary"
                endIcon={<ArrowForwardIcon />}
                sx={{
                  px: 3.5,
                  py: 1.35,
                  fontWeight: 800,
                  fontSize: "0.95rem",
                  "&:active": { transform: "scale(0.98)" },
                }}
              >
                Ver catálogo
              </Button>
              <Button
                component={Link}
                href="/services"
                variant="outlined"
                sx={{
                  px: 3.5,
                  py: 1.35,
                  fontWeight: 700,
                  fontSize: "0.95rem",
                  color: "#FFFFFF",
                  borderColor: "rgba(255,255,255,0.45)",
                  "@media (hover: hover)": {
                    "&:hover": { borderColor: "#FFFFFF", bgcolor: "rgba(255,255,255,0.08)" },
                  },
                  "&:active": { transform: "scale(0.98)" },
                }}
              >
                Servicio técnico
              </Button>
            </Stack>

            {/* Los tres datos que deciden una compra, en letra pequeña: apoyan
                el titular sin disputarle la atención. */}
            <Stack
              direction={{ xs: "column", sm: "row" }}
              spacing={{ xs: 1.2, sm: 3 }}
              sx={{
                mt: { xs: 4, md: 5 },
                pt: { xs: 3, md: 3.5 },
                borderTop: "1px solid rgba(255,255,255,0.18)",
                flexWrap: "wrap",
              }}
            >
              {DATOS.map(({ icon: Icon, texto }) => (
                <Stack key={texto} direction="row" spacing={1} sx={{ alignItems: "center" }}>
                  <Icon sx={{ fontSize: 18, color: "secondary.main" }} />
                  <Typography
                    sx={{ fontSize: { xs: "0.82rem", md: "0.85rem" }, color: "rgba(255,255,255,0.8)" }}
                  >
                    {texto}
                  </Typography>
                </Stack>
              ))}
            </Stack>
          </Grid>

          {/* La foto es de la tienda real; en un teléfono estorba más de lo que
              aporta, así que solo aparece cuando hay ancho para ponerla al lado
              del texto. */}
          <Grid size={{ xs: 12, md: 5 }} sx={{ display: { xs: "none", md: "block" } }}>
            <Box sx={{ position: "relative", aspectRatio: "4/3", overflow: "hidden" }}>
              <SafeImage
                src="/brand/tienda.webp"
                alt="Local de Grupo STS en el centro de Trujillo"
                objectFit="cover"
                eager
                sx={{ filter: "saturate(0.9)" }}
              />
              <Box
                aria-hidden
                sx={{
                  position: "absolute",
                  inset: 0,
                  background:
                    "linear-gradient(to top, rgba(8,42,82,0.85) 0%, rgba(8,42,82,0) 55%)",
                }}
              />
              <Typography
                sx={{
                  position: "absolute",
                  left: 16,
                  bottom: 14,
                  fontSize: "0.78rem",
                  fontWeight: 600,
                  color: "rgba(255,255,255,0.92)",
                }}
              >
                Jr. Alfonso Ugarte 493 · Lun a Sáb, 9:00 – 21:00
              </Typography>
            </Box>
          </Grid>
        </Grid>
      </Container>
    </Box>
  );
}
