"use client";

import { useMemo, useSyncExternalStore, ReactNode } from "react";
import { ThemeProvider as MuiThemeProvider, createTheme, CssBaseline } from "@mui/material";
import { useThemeStore } from "@/lib/stores/theme";

export { useThemeStore as useThemeMode };

/**
 * Paleta de Grupo STS.
 *
 * Antes el sitio usaba el azul #2563eb y la tipografía Inter, que son los
 * valores por defecto de MUI: por eso se veía genérico. El azul marino y el
 * oro salen del logotipo de la empresa; las esquinas rectas y la tipografía
 * de peso alto son parte de la dirección comercial elegida.
 */
export const BRAND = {
  navy: "#0C3A6E",
  navyLight: "#12529C",
  navyDark: "#082A52",
  gold: "#FFCE00",
  goldDark: "#E6B800",
  offer: "#E11D2E",
  ink: "#16202E",
} as const;

/** Tipografía de titulares. Se usa desde `sx` donde hace falta peso visual. */
export const DISPLAY_FONT = "var(--font-display), 'Archivo Black', system-ui, sans-serif";

export default function AppThemeProvider({ children }: { children: ReactNode }) {
  const { mode } = useThemeStore();

  // "¿Ya hidrató?" se pregunta sin efecto ni estado: useSyncExternalStore
  // devuelve false en el render del servidor y true en el del navegador, que
  // es justo la distinción que hace falta. Antes esto era un setState dentro
  // de un efecto, que provoca un render encadenado en cada montaje.
  const hydrated = useSyncExternalStore(
    () => () => {},
    () => true,
    () => false
  );

  // Antes de hidratar, el store todavía no leyó localStorage, así que `mode`
  // vale siempre "light". Renderizamos igual (ocultar la página entera se veía
  // como un parpadeo en blanco); el script inline del layout ya pintó el color
  // de fondo correcto, así que la transición no se nota.
  const theme = useMemo(
    () =>
      createTheme({
        palette: {
          mode,
          primary: {
            main: BRAND.navy,
            light: BRAND.navyLight,
            dark: BRAND.navyDark,
            contrastText: "#FFFFFF",
          },
          secondary: {
            main: BRAND.gold,
            dark: BRAND.goldDark,
            light: "#FFDC4D",
            // Sobre el oro el texto va en azul marino: el blanco no contrasta.
            contrastText: BRAND.navy,
          },
          error: { main: BRAND.offer },
          background: {
            default: mode === "light" ? "#F2F4F7" : "#0B1520",
            paper: mode === "light" ? "#FFFFFF" : "#16202E",
          },
          text: {
            primary: mode === "light" ? BRAND.ink : "#E8EDF3",
            secondary: mode === "light" ? "#5A6878" : "#93A2B4",
          },
          divider: mode === "light" ? "#E2E7ED" : "rgba(255,255,255,0.12)",
        },
        typography: {
          fontFamily: "var(--font-body), system-ui, -apple-system, sans-serif",
          h1: { fontFamily: DISPLAY_FONT, letterSpacing: "-0.02em" },
          h2: { fontFamily: DISPLAY_FONT, letterSpacing: "-0.02em" },
          h3: { fontFamily: DISPLAY_FONT, letterSpacing: "-0.015em" },
          h4: { fontFamily: DISPLAY_FONT, letterSpacing: "-0.01em" },
          button: { textTransform: "none", fontWeight: 700 },
        },
        // La dirección comercial es de esquinas rectas: los bordes redondeados
        // eran parte de lo que hacía que el sitio pareciera una plantilla.
        shape: { borderRadius: 0 },
        components: {
          MuiButton: {
            styleOverrides: {
              root: { boxShadow: "none", "&:hover": { boxShadow: "none" } },
            },
          },
          MuiCard: { styleOverrides: { root: { backgroundImage: "none" } } },
          MuiPaper: { styleOverrides: { root: { backgroundImage: "none" } } },
        },
      }),
    [mode]
  );

  return (
    <MuiThemeProvider theme={theme}>
      <CssBaseline />
      {/* Evita que el contenido "salte" de claro a oscuro de golpe al hidratar */}
      <div style={{ transition: hydrated ? "none" : undefined }}>{children}</div>
    </MuiThemeProvider>
  );
}
