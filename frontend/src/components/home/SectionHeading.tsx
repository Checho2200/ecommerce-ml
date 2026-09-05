"use client";

/**
 * Encabezado de sección de la portada.
 *
 * Existe para que todas las secciones se presenten igual: mismo tamaño, misma
 * regla dorada y el mismo enlace de salida a la derecha. Antes cada bloque
 * inventaba su propio título con tamaños sueltos, y la página parecía armada
 * por partes.
 */

import Link from "next/link";
import { Box, Stack, Typography } from "@mui/material";
import { DISPLAY_FONT } from "@/components/ThemeProvider";

export default function SectionHeading({
  title,
  action,
  id,
}: {
  title: string;
  /** Enlace opcional al final de la fila: "Ver todo →". */
  action?: { label: string; href: string };
  id?: string;
}) {
  return (
    <Stack
      direction="row"
      spacing={{ xs: 1.5, md: 2.5 }}
      sx={{ alignItems: "center", mb: { xs: 3, md: 3.5 } }}
    >
      <Typography
        id={id}
        component="h2"
        sx={{
          fontFamily: DISPLAY_FONT,
          color: "acento.main",
          fontSize: { xs: "1.3rem", md: "1.6rem" },
          lineHeight: 1.15,
          whiteSpace: "nowrap",
        }}
      >
        {title}
      </Typography>

      {/* La regla ocupa lo que sobra: alinea todos los encabezados aunque los
          títulos midan distinto. */}
      <Box aria-hidden sx={{ flexGrow: 1, height: 2, bgcolor: "secondary.main" }} />

      {action && (
        <Typography
          component={Link}
          href={action.href}
          sx={{
            fontSize: "0.82rem",
            fontWeight: 700,
            color: "acento.main",
            textDecoration: "none",
            whiteSpace: "nowrap",
            transition: "opacity 0.2s",
            "@media (hover: hover)": { "&:hover": { opacity: 0.7 } },
          }}
        >
          {action.label} →
        </Typography>
      )}
    </Stack>
  );
}
