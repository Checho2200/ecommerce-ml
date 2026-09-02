"use client";

import { useState } from "react";
import Link from "next/link";
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
import MarkEmailReadOutlinedIcon from "@mui/icons-material/MarkEmailReadOutlined";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [enviado, setEnviado] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await api.auth.forgotPassword(email);
      // El backend responde lo mismo exista o no la cuenta, para no delatar
      // qué correos están registrados. La pantalla dice lo mismo.
      setEnviado(true);
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? err.message
          : "No pudimos procesar la solicitud. Inténtalo de nuevo."
      );
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
          {enviado ? (
            <Stack spacing={2.5} sx={{ alignItems: "center", textAlign: "center" }}>
              <MarkEmailReadOutlinedIcon sx={{ fontSize: 56, color: "primary.main" }} />
              <Typography variant="h6" sx={{ fontWeight: 800 }}>
                Revisa tu correo
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Si <strong>{email}</strong> corresponde a una cuenta, te enviamos
                un enlace para elegir una contraseña nueva. Vence en 30 minutos y
                sirve una sola vez.
              </Typography>
              <Button component={Link} href="/login" variant="contained" fullWidth>
                Volver a iniciar sesión
              </Button>
            </Stack>
          ) : (
            <>
              <Stack sx={{ alignItems: "center", mb: 4 }}>
                <Typography variant="h5" sx={{ fontWeight: 800 }}>
                  ¿Olvidaste tu contraseña?
                </Typography>
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{ mt: 0.5, textAlign: "center" }}
                >
                  Escribe el correo de tu cuenta y te mandamos un enlace para
                  crear una nueva.
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

                  <Button
                    type="submit"
                    variant="contained"
                    fullWidth
                    size="large"
                    disabled={loading}
                    sx={{ py: 1.4, fontWeight: 700 }}
                  >
                    {loading ? (
                      <CircularProgress size={22} color="inherit" />
                    ) : (
                      "Enviar enlace"
                    )}
                  </Button>
                </Stack>
              </Box>
            </>
          )}
        </Paper>
      </Box>
    </Box>
  );
}
