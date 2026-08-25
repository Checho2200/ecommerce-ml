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
  Chip,
  Divider,
  alpha,
} from "@mui/material";
import { keyframes } from "@mui/system";
import EmailIcon from "@mui/icons-material/Email";
import LockIcon from "@mui/icons-material/Lock";
import Visibility from "@mui/icons-material/Visibility";
import VisibilityOff from "@mui/icons-material/VisibilityOff";
import BoltIcon from "@mui/icons-material/Bolt";
import VpnKeyIcon from "@mui/icons-material/VpnKey";
import SecurityIcon from "@mui/icons-material/Security";

const fadeIn = keyframes`
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
`;

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
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
      router.push("/admin");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al iniciar sesión");
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
      }}
    >
      {/* Background decoration */}
      <Box sx={{ position: "absolute", inset: 0, pointerEvents: "none" }}>
        <Box sx={{ position: "absolute", top: "-20%", left: "-10%", width: "50%", height: "60%", background: "radial-gradient(ellipse, rgba(37,99,235,0.08) 0%, transparent 70%)" }} />
        <Box sx={{ position: "absolute", bottom: "-20%", right: "-10%", width: "50%", height: "60%", background: "radial-gradient(ellipse, rgba(139,92,246,0.06) 0%, transparent 70%)" }} />
      </Box>

      <Paper
        elevation={0}
        sx={{
          position: "relative",
          width: "100%",
          maxWidth: 440,
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
            background: "linear-gradient(135deg, #1e40af 0%, #6366f1 100%)",
            display: "flex", alignItems: "center", justifyContent: "center",
            margin: "0 auto 16px", boxShadow: "0 8px 24px -8px rgba(99,102,241,0.5)",
          }}>
            <BoltIcon sx={{ color: "white", fontSize: 28 }} />
          </Box>
          <Typography variant="h5" sx={{ fontWeight: 800, letterSpacing: "-0.02em" }}>
            Bienvenido de vuelta
          </Typography>
          <Typography variant="body2" sx={{ color: "text.secondary", mt: 0.5 }}>
            Inicia sesión en GRUPO STS SAC
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
            id="login-email"
            label="Email"
            type="email"
            fullWidth
            required
            autoFocus
            value={email}
            onChange={(e) => setEmail(e.target.value)}
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
            id="login-password"
            label="Contraseña"
            type={showPassword ? "text" : "password"}
            fullWidth
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            slotProps={{
              input: {
                startAdornment: (
                  <InputAdornment position="start">
                    <LockIcon sx={{ fontSize: 18, color: "text.secondary" }} />
                  </InputAdornment>
                ),
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton
                      onClick={() => setShowPassword(!showPassword)}
                      edge="end"
                      size="small"
                      tabIndex={-1}
                    >
                      {showPassword ? <VisibilityOff fontSize="small" /> : <Visibility fontSize="small" />}
                    </IconButton>
                  </InputAdornment>
                ),
              },
            }}
          />
          <Button
            id="login-submit"
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
              background: "linear-gradient(135deg, #1e40af 0%, #6366f1 100%)",
              boxShadow: "0 8px 24px -8px rgba(99,102,241,0.4)",
              "&:hover": {
                background: "linear-gradient(135deg, #1d4ed8 0%, #4f46e5 100%)",
                transform: "translateY(-1px)",
                boxShadow: "0 12px 28px -8px rgba(99,102,241,0.5)",
              },
              transition: "all 0.2s",
            }}
          >
            {loading ? <CircularProgress size={20} sx={{ color: "white" }} /> : "Iniciar Sesión"}
          </Button>
        </Box>

        {/* Footer link */}
        <Typography variant="body2" sx={{ textAlign: "center", mt: 3, color: "text.secondary" }}>
          ¿No tienes cuenta?{" "}
          <Box
            component={Link}
            href="/register"
            sx={{ color: "primary.main", fontWeight: 700, textDecoration: "none", "&:hover": { textDecoration: "underline" } }}
          >
            Regístrate aquí
          </Box>
        </Typography>

        <Divider sx={{ my: 3 }}>
          <Typography variant="caption" sx={{ color: "text.disabled", px: 1 }}>
            CREDENCIALES DE PRUEBA
          </Typography>
        </Divider>

        {/* Demo credentials */}
        <Box sx={{
          p: 2, borderRadius: 2, bgcolor: (t) => alpha(t.palette.primary.main, 0.05),
          border: "1px solid", borderColor: (t) => alpha(t.palette.primary.main, 0.12),
        }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 0.75, mb: 1.5 }}>
            <VpnKeyIcon sx={{ fontSize: 14, color: "primary.main" }} />
            <Typography variant="caption" sx={{ fontWeight: 700, color: "primary.main" }}>
              Acceso rápido
            </Typography>
          </Box>
          <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
            {[
              { role: "Admin", email: "admin@sanchez.pe", pass: "Admin123!" },
              { role: "Cliente", email: "cliente@test.com", pass: "Cliente123!" },
            ].map((c) => (
              <Box key={c.role} sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
                <Chip label={c.role} size="small" color="primary" variant="outlined" sx={{ fontWeight: 700, fontSize: "0.65rem", height: 20 }} />
                <Typography variant="caption" sx={{ color: "text.secondary", fontFamily: "monospace" }}>
                  {c.email}
                </Typography>
                <Typography variant="caption" sx={{ color: "text.disabled" }}>/</Typography>
                <Typography variant="caption" sx={{ color: "text.secondary", fontFamily: "monospace" }}>
                  {c.pass}
                </Typography>
              </Box>
            ))}
          </Box>
        </Box>

        {/* Security note */}
        <Box sx={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 0.5, mt: 2.5 }}>
          <SecurityIcon sx={{ fontSize: 12, color: "text.disabled" }} />
          <Typography variant="caption" sx={{ color: "text.disabled" }}>
            Conexión segura — GRUPO STS SAC Trujillo, Perú
          </Typography>
        </Box>
      </Paper>
    </Box>
  );
}
