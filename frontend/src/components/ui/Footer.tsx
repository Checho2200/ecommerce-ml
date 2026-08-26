"use client";

/**
 * Pie de página del sitio.
 *
 * Antes existía únicamente incrustado dentro de la portada, así que el resto de
 * las páginas terminaban de golpe. Ahora se monta desde el layout raíz.
 */

import Link from "next/link";
import { Box, Container, Grid, Typography, Divider, Stack } from "@mui/material";
import LocationOnOutlinedIcon from "@mui/icons-material/LocationOnOutlined";
import MailOutlineIcon from "@mui/icons-material/EmailOutlined";
import PhoneOutlinedIcon from "@mui/icons-material/PhoneOutlined";
import ScheduleOutlinedIcon from "@mui/icons-material/ScheduleOutlined";

const TIENDA = [
  { label: "Catálogo", href: "/catalog" },
  { label: "Servicio técnico", href: "/services" },
  { label: "Mi carrito", href: "/cart" },
];

const SOCIAL = [
  { label: "Facebook", href: "https://www.facebook.com/grupostssac" },
  { label: "Instagram", href: "https://www.instagram.com/grupo_sts_sac" },
  { label: "gruposts.com.pe", href: "https://gruposts.com.pe" },
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
            <Box
              component="img"
              src="/brand/logo-sts.png"
              alt="Grupo STS SAC"
              sx={{ height: 44, width: "auto", mb: 1.8, display: "block" }}
            />
            <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 340, lineHeight: 1.7 }}>
              Más de 30 años en el mercado tecnológico, con presencia en La Libertad
              y Piura. Soporte técnico de equipos informáticos, servidores de datos,
              redes y comunicaciones.
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
                { icon: <LocationOnOutlinedIcon fontSize="small" />, text: "Jr. Alfonso Ugarte 493 — Centro Histórico, Trujillo" },
                { icon: <PhoneOutlinedIcon fontSize="small" />, text: "WhatsApp 924 215 320", href: "https://wa.me/51924215320" },
                { icon: <MailOutlineIcon fontSize="small" />, text: "soporte@gruposts.com.pe", href: "mailto:soporte@gruposts.com.pe" },
                { icon: <ScheduleOutlinedIcon fontSize="small" />, text: "Lun a Sáb · 9:00 – 21:00" },
              ].map((item, i) => (
                <Stack key={i} direction="row" spacing={1.2} sx={{ alignItems: "center" }}>
                  <Box sx={{ color: "primary.main", display: "flex" }}>{item.icon}</Box>
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    {...(item.href
                      ? {
                          component: "a",
                          href: item.href,
                          target: "_blank",
                          rel: "noopener noreferrer",
                          sx: { textDecoration: "none", "&:hover": { color: "primary.main" } },
                        }
                      : {})}
                  >
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
          <Stack direction="row" spacing={2}>
            {SOCIAL.map((r) => (
              <Typography
                key={r.label}
                component="a"
                href={r.href}
                target="_blank"
                rel="noopener noreferrer"
                variant="caption"
                sx={{
                  color: "text.disabled", textDecoration: "none",
                  "&:hover": { color: "primary.main" },
                }}
              >
                {r.label}
              </Typography>
            ))}
          </Stack>
        </Stack>
      </Container>
    </Box>
  );
}
