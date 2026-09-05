"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import CampoDeContrasena, { LONGITUD_MINIMA } from "@/components/ui/CampoDeContrasena";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";

import {
  Box,
  Typography,
  Button,
  Paper,
  Alert,
  CircularProgress,
  Stack,
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";

// Igual que en el registro: el mínimo real lo impone el backend.
const MINIMO = LONGITUD_MINIMA;

function ResetPasswordForm() {
  const parametros = useSearchParams();
  const router = useRouter();

  // El token viaja en el enlace del correo. Se lee durante el render, no en un
  // efecto: ya está disponible en la primera pasada.
  const token = parametros.get("token") ?? "";

  const [password, setPassword] = useState("");
  const [repetida, setRepetida] = useState("");
  const [error, setError] = useState("");
  const [listo, setListo] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (password.length < MINIMO) {
      setError(`La contraseña debe tener al menos ${MINIMO} caracteres.`);
      return;
    }
    if (password !== repetida) {
      setError("Las dos contraseñas no coinciden.");
      return;
    }

    setLoading(true);
    try {
      await api.auth.resetPassword(token, password);
      setListo(true);
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? err.message
          : "El enlace no es válido o ya venció. Solicita uno nuevo."
      );
    } finally {
      setLoading(false);
    }
  };

  if (!token) {
    return (
      <Stack spacing={2.5} sx={{ alignItems: "center", textAlign: "center" }}>
        <Typography variant="h6" sx={{ fontWeight: 800 }}>
          Enlace incompleto
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Este enlace no trae el código de verificación. Pide uno nuevo desde la
          pantalla de recuperación.
        </Typography>
        <Button component={Link} href="/forgot-password" variant="contained" fullWidth>
          Pedir un enlace nuevo
        </Button>
      </Stack>
    );
  }

  if (listo) {
    return (
      <Stack spacing={2.5} sx={{ alignItems: "center", textAlign: "center" }}>
        <CheckCircleIcon sx={{ fontSize: 56, color: "success.main" }} />
        <Typography variant="h6" sx={{ fontWeight: 800 }}>
          Contraseña actualizada
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Ya puedes entrar a tu cuenta con la contraseña nueva.
        </Typography>
        <Button variant="contained" fullWidth onClick={() => router.push("/login")}>
          Iniciar sesión
        </Button>
      </Stack>
    );
  }

  return (
    <>
      <Stack sx={{ alignItems: "center", mb: 4 }}>
        <Typography variant="h5" sx={{ fontWeight: 800 }}>
          Elige una contraseña nueva
        </Typography>
        <Typography
          variant="body2"
          color="text.secondary"
          sx={{ mt: 0.5, textAlign: "center" }}
        >
          Escríbela dos veces para confirmar que no hubo un error de tipeo.
        </Typography>
      </Stack>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      <Box component="form" onSubmit={handleSubmit}>
        <Stack spacing={2.5}>
          <CampoDeContrasena
            label="Contraseña nueva"
            fullWidth
            required
            autoFocus
            autoComplete="new-password"
            valor={password}
            onCambio={setPassword}
            medirFuerza
            helperText={`Al menos ${MINIMO} caracteres. Una frase larga es mejor que una palabra con símbolos.`}
          />

          <CampoDeContrasena
            label="Repite la contraseña"
            fullWidth
            required
            autoComplete="new-password"
            valor={repetida}
            onCambio={setRepetida}
          />

          <Button
            type="submit"
            variant="contained"
            fullWidth
            size="large"
            disabled={loading}
            sx={{ py: 1.4, fontWeight: 700 }}
          >
            {loading ? <CircularProgress size={22} color="inherit" /> : "Guardar"}
          </Button>
        </Stack>
      </Box>
    </>
  );
}

export default function ResetPasswordPage() {
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
          href="/login"
          startIcon={<ArrowBackIcon sx={{ fontSize: 16 }} />}
          size="small"
          sx={{ mb: 2, color: "text.secondary" }}
        >
          Volver a iniciar sesión
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
          {/* useSearchParams obliga a un límite de Suspense: sin él, Next no
              puede prerenderizar la página en el build. */}
          <Suspense
            fallback={
              <Stack sx={{ alignItems: "center", py: 4 }}>
                <CircularProgress size={28} />
              </Stack>
            }
          >
            <ResetPasswordForm />
          </Suspense>
        </Paper>
      </Box>
    </Box>
  );
}
