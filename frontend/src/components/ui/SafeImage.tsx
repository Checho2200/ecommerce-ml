"use client";

/**
 * Imagen con respaldo automático.
 *
 * Si el archivo no carga (404, red caída, disco efímero de Render en el caso de
 * las subidas del panel admin), muestra el placeholder de marca en lugar del
 * ícono de imagen rota del navegador. Nunca debe verse una imagen rota en vivo.
 */

import { useState } from "react";
import { Box, SxProps, Theme } from "@mui/material";

const FALLBACK = "/products/_placeholder.svg";

export default function SafeImage({
  src,
  alt,
  className,
  sx,
  objectFit = "contain",
  eager = false,
}: {
  src?: string | null;
  alt: string;
  className?: string;
  sx?: SxProps<Theme>;
  objectFit?: "contain" | "cover";
  /** Para la imagen visible al abrir la página: diferirla retrasa el pintado. */
  eager?: boolean;
}) {
  const [failed, setFailed] = useState(false);
  const resolved = !src || failed ? FALLBACK : src;

  return (
    <Box
      component="img"
      src={resolved}
      alt={alt}
      className={className}
      loading={eager ? "eager" : "lazy"}
      fetchPriority={eager ? "high" : undefined}
      decoding="async"
      onError={() => setFailed(true)}
      sx={{
        width: "100%",
        height: "100%",
        objectFit,
        display: "block",
        ...sx,
      }}
    />
  );
}
