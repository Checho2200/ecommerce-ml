"use client";

/**
 * Pie de página del sitio.
 *
 * Antes existía únicamente incrustado dentro de la portada, así que el resto de
 * las páginas terminaban de golpe. Ahora se monta desde el layout raíz.
 */

import Link from "next/link";
import { Box, Container, Grid, Typography, Divider, Stack } from "@mui/material";
import ShieldIcon from "@mui/icons-material/Shield";
import LocationOnOutlinedIcon from "@mui/icons-material/LocationOnOutlined";
import MailOutlineIcon from "@mui/icons-material/EmailOutlined";
import PhoneOutlinedIcon from "@mui/icons-material/PhoneOutlined";
import ScheduleOutlinedIcon from "@mui/icons-material/ScheduleOutlined";

const TIENDA = [
  { label: "Catálogo", href: "/catalog" },
  { label: "Servicio técnico", href: "/services" },
  { label: "Mi carrito", href: "/cart" },
];

const CUENTA = [
  { label: "Iniciar sesión", href: "/login" },
  { label: "Crear cuenta", href: "/register" },
  { label: "Mis pedidos", href: "/orders" },
];

function FooterLink({ href, label }: { href: string; label: string }) {
  return (
    <Typography
      component={Link}
      href={href}
      variant="body2"
      sx={{
        color: "text.secondary",
        textDecoration: "none",
        transition: "color 0.2s",
        "&:hover": { color: "primary.main" },
      }}
    >
      {label}
    </Typography>
  );
}

export default function Footer() {
  const year = new Date().getFullYear();

  return (
    <Box
      component="footer"
      sx={{
        mt: "auto",
        borderTop: "1px solid",
        borderColor: "divider",
        bgcolor: "background.paper",
        pt: { xs: 5, md: 7 },
        pb: 3,
      }}
    >
      <Container maxWidth="lg">
        <Grid container spacing={{ xs: 4, md: 5 }}>
          {/* Marca */}
          <Grid size={{ xs: 12, md: 4 }}>
            <Stack direction="row" spacing={1} sx={{ alignItems: "center", mb: 1.5 }}>
              <ShieldIcon sx={{ color: "primary.main" }} />
              <Typography variant="subtitle1" sx={{ fontWeight: 800, letterSpacing: 0.3 }}>
                GRUPO STS SAC
              </Typography>
            </Stack>
            <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 340, lineHeight: 1.7 }}>
              Tienda especializada en componentes de cómputo, periféricos y servicio
              técnico. Cada pedido se valida con un modelo de detección de fraude
              antes de confirmarse.
            </Typography>
          </Grid>

          {/* Tienda */}
          <Grid size={{ xs: 6, sm: 4, md: 2 }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 800, mb: 1.5 }}>
              Tienda
            </Typography>
            <Stack spacing={1}>
              {TIENDA.map((l) => (
                <FooterLink key={l.href} {...l} />
              ))}
            </Stack>
          </Grid>

          {/* Cuenta */}
          <Grid size={{ xs: 6, sm: 4, md: 2 }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 800, mb: 1.5 }}>
              Mi cuenta
            </Typography>
            <Stack spacing={1}>
              {CUENTA.map((l) => (
                <FooterLink key={l.href} {...l} />
              ))}
            </Stack>
          </Grid>

          {/* Contacto */}
          <Grid size={{ xs: 12, sm: 4, md: 4 }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 800, mb: 1.5 }}>
              Contacto
            </Typography>
            <Stack spacing={1.2}>
              {[
                { icon: <LocationOnOutlinedIcon fontSize="small" />, text: "Trujillo, La Libertad — Perú" },
                { icon: <PhoneOutlinedIcon fontSize="small" />, text: "(044) 000 000" },
                { icon: <MailOutlineIcon fontSize="small" />, text: "contacto@sanchezstore.pe" },
                { icon: <ScheduleOutlinedIcon fontSize="small" />, text: "Lun a Sáb · 9:00 – 19:00" },
              ].map((item, i) => (
                <Stack key={i} direction="row" spacing={1.2} sx={{ alignItems: "center" }}>
                  <Box sx={{ color: "primary.main", display: "flex" }}>{item.icon}</Box>
                  <Typography variant="body2" color="text.secondary">
                    {item.text}
                  </Typography>
                </Stack>
              ))}
            </Stack>
          </Grid>
        </Grid>

        <Divider sx={{ my: 3 }} />

        <Stack
          direction={{ xs: "column", sm: "row" }}
          spacing={1} sx={{ alignItems: { xs: "flex-start", sm: "center" }, justifyContent: "space-between" }}>
          <Typography variant="caption" color="text.secondary">
            © {year} Grupo STS SAC. Todos los derechos reservados.
          </Typography>
          <Typography variant="caption" color="text.disabled">
            Detección de fraude con LightGBM · Proyecto de tesis
          </Typography>
        </Stack>
      </Container>
    </Box>
  );
}
