"use client";

import { useState } from "react";
import Link from "next/link";
import CampoDeContrasena from "@/components/ui/CampoDeContrasena";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";

import {
  Box,
  Typography,
  TextField,
  Button,
  Paper,
  Alert,
  CircularProgress,
  Stack,
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      // Antes esto mandaba a /admin siempre, así que un cliente terminaba en el
      // panel de administración. Ahora cada rol va donde corresponde.
      const me = await api.auth.me();
      router.push(me.role === "ADMIN" ? "/admin" : "/");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al iniciar sesión");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box
      sx={{
        minHeight: "100dvh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        bgcolor: "background.default",
        px: 2,
        py: 6,
      }}
    >
      <Box sx={{ width: "100%", maxWidth: 420 }}>
        <Button
          component={Link}
          href="/"
          startIcon={<ArrowBackIcon sx={{ fontSize: 16 }} />}
          size="small"
          sx={{ mb: 2, color: "text.secondary" }}
        >
          Volver a la tienda
        </Button>

        <Paper
          elevation={0}
          sx={{
            p: { xs: 3, sm: 4.5 },
            borderRadius: 4,
            border: "1px solid",
            borderColor: "divider",
          }}
        >
          <Stack sx={{ alignItems: "center", mb: 4 }}>
            <Box
              sx={{
                width: 60, height: 60, borderRadius: 3, mb: 2,
                display: "flex", alignItems: "center", justifyContent: "center",
                bgcolor: "#0c3a6e",
              }}
            >
              <Box
                component="img"
                src="/brand/isotipo-sts.png"
                alt="Grupo STS"
                sx={{ width: 36, height: "auto", display: "block" }}
              />
            </Box>
            <Typography variant="h5" sx={{ fontWeight: 800 }}>
              Iniciar sesión
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              Accede a tu cuenta de GRUPO STS
            </Typography>
          </Stack>

          {error && (
            <Alert severity="error" sx={{ mb: 3 }}>
              {error}
            </Alert>
          )}

          <Box component="form" onSubmit={handleSubmit}>
            <Stack spacing={2.5}>
              <TextField
                label="Correo electrónico"
                type="email"
                fullWidth
                required
                autoFocus
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />

              {/* Al entrar no se mide la fuerza: la contraseña ya está
                  elegida y juzgarla aquí solo estorba. Tampoco se aplica la
                  política nueva, para que quien tenga una clave anterior más
                  corta pueda entrar y cambiarla. */}
              <CampoDeContrasena
                label="Contraseña"
                fullWidth
                required
                autoComplete="current-password"
                valor={password}
                onCambio={setPassword}
              />

              <Button
                type="submit"
                variant="contained"
                fullWidth
                size="large"
                disabled={loading}
                sx={{ py: 1.4, fontWeight: 700 }}
              >
                {loading ? <CircularProgress size={22} color="inherit" /> : "Entrar"}
              </Button>
            </Stack>
          </Box>

          <Typography variant="body2" sx={{ textAlign: "center", mt: 2.5 }}>
            <Box
              component={Link}
              href="/forgot-password"
              sx={{ color: "text.secondary", textDecoration: "none" }}
            >
              ¿Olvidaste tu contraseña?
            </Box>
          </Typography>

          <Typography variant="body2" sx={{ textAlign: "center", mt: 1.5, color: "text.secondary" }}>
            ¿No tienes cuenta?{" "}
            <Box
              component={Link}
              href="/register"
              sx={{ color: "primary.main", fontWeight: 700, textDecoration: "none" }}
            >
              Créala aquí
            </Box>
          </Typography>
        </Paper>
      </Box>
    </Box>
  );
}
