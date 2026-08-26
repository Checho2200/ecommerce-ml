"use client";

/**
 * Botón flotante de WhatsApp.
 *
 * Es la vía de contacto que la empresa ya usa (el número está publicado en
 * gruposts.com.pe), y en un teléfono abre la aplicación directamente. Se
 * mantiene por encima del contenido pero por debajo de los diálogos de MUI.
 */

import { Box, Tooltip } from "@mui/material";

const NUMERO = "51924215320";
const MENSAJE = "Hola, vengo de la tienda en línea y quisiera más información.";

export default function WhatsAppFab() {
  return (
    <Tooltip title="Escríbenos por WhatsApp" placement="left">
      <Box
        component="a"
        href={`https://wa.me/${NUMERO}?text=${encodeURIComponent(MENSAJE)}`}
        target="_blank"
        rel="noopener noreferrer"
        aria-label="Escríbenos por WhatsApp"
        sx={{
          position: "fixed",
          right: { xs: 16, md: 24 },
          // Se apoya sobre el área segura: en iPhone con indicador de inicio,
          // un `bottom` fijo dejaría el botón medio tapado.
          bottom: {
            xs: 'calc(20px + env(safe-area-inset-bottom))',
            md: 'calc(24px + env(safe-area-inset-bottom))',
          },
          zIndex: (t) => t.zIndex.speedDial,
          width: { xs: 54, md: 58 },
          height: { xs: 54, md: 58 },
          borderRadius: "50%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          bgcolor: "#25D366",
          color: "white",
          boxShadow: "0 8px 24px -6px rgba(37,211,102,0.55)",
          transition: "transform 0.2s, box-shadow 0.2s",
          "@media (hover: hover)": {
            "&:hover": {
              transform: "scale(1.06)",
              boxShadow: "0 12px 28px -6px rgba(37,211,102,0.7)",
            },
          },
          "&:active": { transform: "scale(0.94)" },
        }}
      >
        {/* Icono oficial de WhatsApp (MUI no lo incluye) */}
        <Box
          component="svg"
          viewBox="0 0 24 24"
          fill="currentColor"
          sx={{ width: { xs: 28, md: 30 }, height: { xs: 28, md: 30 } }}
          aria-hidden
        >
          <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.174.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51l-.57-.01c-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.872.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884a9.82 9.82 0 016.988 2.896 9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z" />
        </Box>
      </Box>
    </Tooltip>
  );
}
