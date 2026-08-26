"use client";

import { useEffect, useMemo, useState, ReactNode } from "react";
import { ThemeProvider as MuiThemeProvider, createTheme, CssBaseline } from "@mui/material";
import { useThemeStore } from "@/lib/stores/theme";

export { useThemeStore as useThemeMode };

export default function AppThemeProvider({ children }: { children: ReactNode }) {
  const { mode } = useThemeStore();
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    setHydrated(true);
  }, []);

  // Antes de hidratar, el store todavía no leyó localStorage, así que `mode`
  // vale siempre "light". Renderizamos igual (ocultar la página entera se veía
  // como un parpadeo en blanco); el script inline del layout ya pintó el color
  // de fondo correcto, así que la transición no se nota.
  const theme = useMemo(
    () =>
      createTheme({
        palette: {
          mode,
          primary: { main: "#2563eb", light: "#60a5fa", dark: "#1d4ed8" },
          secondary: { main: "#facc15", light: "#fde047", dark: "#eab308" },
          background: {
            default: mode === "light" ? "#f8fafc" : "#0f172a",
            paper: mode === "light" ? "#ffffff" : "#1e293b",
          },
          divider: mode === "light" ? "rgba(0, 0, 0, 0.08)" : "rgba(255, 255, 255, 0.12)",
        },
        typography: {
          fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
          button: { textTransform: "none", fontWeight: 600 },
        },
        shape: { borderRadius: 12 },
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
