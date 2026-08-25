"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import {
  Box,
  Typography,
  TextField,
  Button,
  Paper,
  InputAdornment,
  IconButton,
  Alert,
  CircularProgress,
  Grid,
} from "@mui/material";
import { keyframes } from "@mui/system";
import EmailIcon from "@mui/icons-material/Email";
import LockIcon from "@mui/icons-material/Lock";
import PersonIcon from "@mui/icons-material/Person";
import PhoneIcon from "@mui/icons-material/Phone";
import Visibility from "@mui/icons-material/Visibility";
import VisibilityOff from "@mui/icons-material/VisibilityOff";
import RocketLaunchIcon from "@mui/icons-material/RocketLaunch";
import SecurityIcon from "@mui/icons-material/Security";

const fadeIn = keyframes`
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
`;

export default function RegisterPage() {
  const [form, setForm] = useState({
    email: "",
    password: "",
    confirmPassword: "",
    full_name: "",
    phone: "",
  });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();
  const router = useRouter();

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [e.target.name]: e.target.value });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
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
      router.push("/admin");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al registrarse");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box
      sx={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        bgcolor: "background.default",
        position: "relative",
        overflow: "hidden",
        px: 2,
        py: 4,
      }}
    >
      {/* Background decoration */}
      <Box sx={{ position: "absolute", inset: 0, pointerEvents: "none" }}>
        <Box sx={{ position: "absolute", top: "-20%", right: "-10%", width: "50%", height: "60%", background: "radial-gradient(ellipse, rgba(37,99,235,0.08) 0%, transparent 70%)" }} />
        <Box sx={{ position: "absolute", bottom: "-20%", left: "-10%", width: "50%", height: "60%", background: "radial-gradient(ellipse, rgba(16,185,129,0.05) 0%, transparent 70%)" }} />
      </Box>

      <Paper
        elevation={0}
        sx={{
          position: "relative",
          width: "100%",
          maxWidth: 480,
          p: { xs: 3, sm: 4 },
          borderRadius: 4,
          border: "1px solid",
          borderColor: "divider",
          bgcolor: "background.paper",
          animation: `${fadeIn} 0.5s ease-out forwards`,
        }}
      >
        {/* Logo */}
        <Box sx={{ textAlign: "center", mb: 4 }}>
          <Box sx={{
            width: 56, height: 56, borderRadius: 2,
            background: "linear-gradient(135deg, #064e3b 0%, #10b981 100%)",
            display: "flex", alignItems: "center", justifyContent: "center",
            margin: "0 auto 16px", boxShadow: "0 8px 24px -8px rgba(16,185,129,0.5)",
          }}>
            <RocketLaunchIcon sx={{ color: "white", fontSize: 28 }} />
          </Box>
          <Typography variant="h5" sx={{ fontWeight: 800, letterSpacing: "-0.02em" }}>
            Crear Cuenta
          </Typography>
          <Typography variant="body2" sx={{ color: "text.secondary", mt: 0.5 }}>
            Únete a GRUPO STS SAC
          </Typography>
        </Box>

        {/* Error */}
        {error && (
          <Alert severity="error" sx={{ mb: 3, borderRadius: 2 }}>
            {error}
          </Alert>
        )}

        {/* Form */}
        <Box component="form" onSubmit={handleSubmit} sx={{ display: "flex", flexDirection: "column", gap: 2.5 }}>
          <TextField
            id="reg-name"
            name="full_name"
            label="Nombre completo"
            type="text"
            fullWidth
            required
            autoFocus
            value={form.full_name}
            onChange={handleChange}
            placeholder="Tu nombre completo"
            slotProps={{
              input: {
                startAdornment: (
                  <InputAdornment position="start">
                    <PersonIcon sx={{ fontSize: 18, color: "text.secondary" }} />
                  </InputAdornment>
                ),
              },
            }}
          />
          <TextField
            id="reg-email"
            name="email"
            label="Email"
            type="email"
            fullWidth
            required
            value={form.email}
            onChange={handleChange}
            placeholder="tu@email.com"
            slotProps={{
              input: {
                startAdornment: (
                  <InputAdornment position="start">
                    <EmailIcon sx={{ fontSize: 18, color: "text.secondary" }} />
                  </InputAdornment>
                ),
              },
            }}
          />
          <TextField
            id="reg-phone"
            name="phone"
            label="Teléfono (opcional)"
            type="tel"
            fullWidth
            value={form.phone}
            onChange={handleChange}
            placeholder="987654321"
            slotProps={{
              input: {
                startAdornment: (
                  <InputAdornment position="start">
                    <PhoneIcon sx={{ fontSize: 18, color: "text.secondary" }} />
                  </InputAdornment>
                ),
              },
            }}
          />
          <Grid container spacing={2}>
            <Grid size={{ xs: 12, sm: 6 }}>
              <TextField
                id="reg-pass"
                name="password"
                label="Contraseña"
                type={showPassword ? "text" : "password"}
                fullWidth
                required
                value={form.password}
                onChange={handleChange}
                placeholder="Mín. 6 caracteres"
                slotProps={{
                  htmlInput: { minLength: 6 },
                  input: {
                    startAdornment: (
                      <InputAdornment position="start">
                        <LockIcon sx={{ fontSize: 18, color: "text.secondary" }} />
                      </InputAdornment>
                    ),
                    endAdornment: (
                      <InputAdornment position="end">
                        <IconButton onClick={() => setShowPassword(!showPassword)} edge="end" size="small" tabIndex={-1}>
                          {showPassword ? <VisibilityOff fontSize="small" /> : <Visibility fontSize="small" />}
                        </IconButton>
                      </InputAdornment>
                    ),
                  },
                }}
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 6 }}>
              <TextField
                id="reg-confirm"
                name="confirmPassword"
                label="Confirmar"
                type={showConfirm ? "text" : "password"}
                fullWidth
                required
                value={form.confirmPassword}
                onChange={handleChange}
                placeholder="Repetir contraseña"
                slotProps={{
                  htmlInput: { minLength: 6 },
                  input: {
                    endAdornment: (
                      <InputAdornment position="end">
                        <IconButton onClick={() => setShowConfirm(!showConfirm)} edge="end" size="small" tabIndex={-1}>
                          {showConfirm ? <VisibilityOff fontSize="small" /> : <Visibility fontSize="small" />}
                        </IconButton>
                      </InputAdornment>
                    ),
                  },
                }}
              />
            </Grid>
          </Grid>

          <Button
            id="register-submit"
            type="submit"
            variant="contained"
            fullWidth
            disabled={loading}
            sx={{
              py: 1.5,
              fontWeight: 800,
              fontSize: "0.95rem",
              borderRadius: 2,
              mt: 0.5,
              background: "linear-gradient(135deg, #064e3b 0%, #10b981 100%)",
              boxShadow: "0 8px 24px -8px rgba(16,185,129,0.4)",
              "&:hover": {
                background: "linear-gradient(135deg, #065f46 0%, #059669 100%)",
                transform: "translateY(-1px)",
                boxShadow: "0 12px 28px -8px rgba(16,185,129,0.5)",
              },
              transition: "all 0.2s",
            }}
          >
            {loading ? <CircularProgress size={20} sx={{ color: "white" }} /> : "Crear Cuenta"}
          </Button>
        </Box>

        {/* Footer link */}
        <Typography variant="body2" sx={{ textAlign: "center", mt: 3, color: "text.secondary" }}>
          ¿Ya tienes cuenta?{" "}
          <Box
            component={Link}
            href="/login"
            sx={{ color: "primary.main", fontWeight: 700, textDecoration: "none", "&:hover": { textDecoration: "underline" } }}
          >
            Inicia sesión
          </Box>
        </Typography>

        {/* Security note */}
        <Box sx={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 0.5, mt: 2 }}>
          <SecurityIcon sx={{ fontSize: 12, color: "text.disabled" }} />
          <Typography variant="caption" sx={{ color: "text.disabled" }}>
            Conexión segura — GRUPO STS SAC Trujillo, Perú
          </Typography>
        </Box>
      </Paper>
    </Box>
  );
}
