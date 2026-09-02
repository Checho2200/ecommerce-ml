"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";

import {
  Box,
  Typography,
  TextField,
  Button,
  Paper,
  Alert,
  CircularProgress,
  InputAdornment,
  IconButton,
  Stack,
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import Visibility from "@mui/icons-material/Visibility";
import VisibilityOff from "@mui/icons-material/VisibilityOff";

const MINIMO = 6;

function ResetPasswordForm() {
  const parametros = useSearchParams();
  const router = useRouter();

  // El token viaja en el enlace del correo. Se lee durante el render, no en un
  // efecto: ya está disponible en la primera pasada.
  const token = parametros.get("token") ?? "";

  const [password, setPassword] = useState("");
  const [repetida, setRepetida] = useState("");
  const [verClave, setVerClave] = useState(false);
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
          <TextField
            label="Contraseña nueva"
            type={verClave ? "text" : "password"}
            fullWidth
            required
            autoFocus
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            helperText={`Mínimo ${MINIMO} caracteres`}
            slotProps={{
              input: {
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton
                      onClick={() => setVerClave(!verClave)}
                      edge="end"
                      size="small"
                      tabIndex={-1}
                      aria-label={verClave ? "Ocultar contraseña" : "Mostrar contraseña"}
                    >
                      {verClave ? (
                        <VisibilityOff fontSize="small" />
                      ) : (
                        <Visibility fontSize="small" />
                      )}
                    </IconButton>
                  </InputAdornment>
                ),
              },
            }}
          />

          <TextField
            label="Repite la contraseña"
            type={verClave ? "text" : "password"}
            fullWidth
            required
            autoComplete="new-password"
            value={repetida}
            onChange={(e) => setRepetida(e.target.value)}
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
