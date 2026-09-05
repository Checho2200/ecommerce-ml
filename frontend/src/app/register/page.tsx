"use client";

import { useState } from "react";
import Link from "next/link";
import CampoDeContrasena, { LONGITUD_MINIMA } from "@/components/ui/CampoDeContrasena";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";

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

// El backend exige al menos 6 caracteres (backend/app/schemas/user.py)
// El mínimo lo define el backend (app/core/passwords.py); aquí se reexporta
// desde el campo compartido para que las dos mitades no se separen.
const MIN_PASSWORD = LONGITUD_MINIMA;

export default function RegisterPage() {
  const [form, setForm] = useState({
    email: "",
    password: "",
    confirmPassword: "",
    full_name: "",
    phone: "",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();
  const router = useRouter();

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [e.target.name]: e.target.value });

  // Validación en vivo: se muestra bajo el campo, no como alerta al enviar.
  const passwordTooShort = form.password.length > 0 && form.password.length < MIN_PASSWORD;
  const mismatch = form.confirmPassword.length > 0 && form.password !== form.confirmPassword;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (form.password.length < MIN_PASSWORD) {
      setError(`La contraseña debe tener al menos ${MIN_PASSWORD} caracteres`);
      return;
    }
    if (form.password !== form.confirmPassword) {
      setError("Las contraseñas no coinciden");
      return;
    }

    setLoading(true);
    try {
      await register({
        email: form.email,
        password: form.password,
        full_name: form.full_name,
        phone: form.phone || undefined,
      });
      // Antes esto mandaba a /admin: una cuenta recién creada es siempre de
      // cliente, así que el panel de administración no le sirve de nada.
      router.push("/");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al registrarse");
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
      <Box sx={{ width: "100%", maxWidth: 460 }}>
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
              Crear cuenta
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              Guarda tus pedidos y compra más rápido
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
                name="full_name"
                label="Nombre completo"
                fullWidth
                required
                autoFocus
                autoComplete="name"
                value={form.full_name}
                onChange={handleChange}
              />

              <TextField
                name="email"
                label="Correo electrónico"
                type="email"
                fullWidth
                required
                autoComplete="email"
                value={form.email}
                onChange={handleChange}
              />

              <TextField
                name="phone"
                label="Teléfono (opcional)"
                fullWidth
                autoComplete="tel"
                value={form.phone}
                onChange={handleChange}
              />

              <CampoDeContrasena
                name="password"
                label="Contraseña"
                fullWidth
                required
                autoComplete="new-password"
                valor={form.password}
                onCambio={(valor) => setForm({ ...form, password: valor })}
                medirFuerza
                error={passwordTooShort}
                helperText={
                  passwordTooShort
                    ? `Debe tener al menos ${MIN_PASSWORD} caracteres`
                    : `Al menos ${MIN_PASSWORD} caracteres. Una frase larga es mejor que una palabra con símbolos.`
                }
              />

              <CampoDeContrasena
                name="confirmPassword"
                label="Repetir contraseña"
                fullWidth
                required
                autoComplete="new-password"
                valor={form.confirmPassword}
                onCambio={(valor) => setForm({ ...form, confirmPassword: valor })}
                error={mismatch}
                helperText={mismatch ? "Las contraseñas no coinciden" : " "}
              />

              <Button
                type="submit"
                variant="contained"
                fullWidth
                size="large"
                disabled={loading}
                sx={{ py: 1.4, fontWeight: 700 }}
              >
                {loading ? <CircularProgress size={22} color="inherit" /> : "Crear cuenta"}
              </Button>
            </Stack>
          </Box>

          <Typography variant="body2" sx={{ textAlign: "center", mt: 3, color: "text.secondary" }}>
            ¿Ya tienes cuenta?{" "}
            <Box
              component={Link}
              href="/login"
              sx={{ color: "primary.main", fontWeight: 700, textDecoration: "none" }}
            >
              Inicia sesión
            </Box>
          </Typography>
        </Paper>
      </Box>
    </Box>
  );
}
