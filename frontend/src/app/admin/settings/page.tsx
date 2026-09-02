'use client'

import { useCallback, useEffect, useState } from 'react'
import { useThemeStore } from '@/lib/stores/theme'
import { api } from '@/lib/api'

import {
  Box, Typography, Card, CardContent, Divider,
  Switch, FormControlLabel, Chip, Button, CircularProgress, Alert,
} from '@mui/material'
import DarkModeIcon from '@mui/icons-material/DarkMode'
import LightModeIcon from '@mui/icons-material/LightMode'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import ErrorIcon from '@mui/icons-material/Error'
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined'
import PaletteIcon from '@mui/icons-material/Palette'
import ApiIcon from '@mui/icons-material/Api'
import PsychologyIcon from '@mui/icons-material/Psychology'

type Salud = Awaited<ReturnType<typeof api.system.health>>

export default function AdminSettingsPage() {
  const { mode, toggleTheme } = useThemeStore()

  // El estado del sistema sale de /health, no de valores escritos a mano: el
  // panel decía "SQLite" y "reglas heurísticas" cuando en producción corre
  // PostgreSQL con el modelo LightGBM cargado.
  const [salud, setSalud] = useState<Salud | null>(null)
  const [consultando, setConsultando] = useState(true)

  const consultarSalud = useCallback(() => {
    setConsultando(true)
    return api.system
      .health()
      .then((datos) => setSalud(datos))
      .catch(() => setSalud(null))
      .finally(() => setConsultando(false))
  }, [])

  useEffect(() => {
    let vigente = true
    api.system
      .health()
      .then((datos) => { if (vigente) setSalud(datos) })
      .catch(() => { if (vigente) setSalud(null) })
      .finally(() => { if (vigente) setConsultando(false) })
    return () => { vigente = false }
  }, [])

  // --- Reentrenamiento del modelo ---
  const [reentrenando, setReentrenando] = useState(false)
  const [avisoModelo, setAvisoModelo] = useState<{ tipo: 'success' | 'error'; texto: string } | null>(null)

  const reentrenar = async () => {
    setReentrenando(true)
    setAvisoModelo(null)
    try {
      const respuesta = await api.fraud.retrain()
      setAvisoModelo({ tipo: 'success', texto: respuesta.message })
    } catch (error: unknown) {
      setAvisoModelo({
        tipo: 'error',
        texto: error instanceof Error ? error.message : 'No se pudo iniciar el reentrenamiento.',
      })
    } finally {
      setReentrenando(false)
    }
  }

  const componentes = [
    { label: 'Frontend (Next.js)', note: 'v16.3.2', estado: 'ok' as const },
    {
      label: 'Backend API',
      note: salud?.status === 'healthy' ? 'Respondiendo' : 'Sin respuesta',
      estado: consultando ? 'cargando' as const : salud ? 'ok' as const : 'error' as const,
    },
    {
      label: 'Base de datos',
      note: salud?.database === 'connected' ? 'Conectada' : 'No disponible',
      estado: consultando ? 'cargando' as const : salud?.database === 'connected' ? 'ok' as const : 'error' as const,
    },
    {
      label: 'Motor antifraude',
      note: salud?.ml_model === 'loaded' ? 'Modelo LightGBM cargado' : 'Modelo no cargado',
      estado: consultando ? 'cargando' as const : salud?.ml_model === 'loaded' ? 'ok' as const : 'parcial' as const,
    },
    {
      label: 'Pasarela de pagos',
      note: salud?.payments === 'configured' ? 'MercadoPago configurado' : 'Sin credenciales',
      estado: consultando ? 'cargando' as const : salud?.payments === 'configured' ? 'ok' as const : 'parcial' as const,
    },
  ]

  return (
    <>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h5" sx={{ fontWeight: 800 }}>Configuración</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
          Ajustes del panel y del sistema
        </Typography>
      </Box>

      {/* ── Apariencia ──────────────────────────────────── */}
      <Card elevation={0} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 3, mb: 3 }}>
        <CardContent sx={{ p: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2 }}>
            <PaletteIcon color="primary" />
            <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>Apariencia</Typography>
          </Box>
          <Divider sx={{ mb: 3 }} />

          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', p: 2, borderRadius: 2, border: '1px solid', borderColor: 'divider' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              {mode === 'dark' ? (
                <DarkModeIcon color="primary" />
              ) : (
                <LightModeIcon color="primary" />
              )}
              <Box>
                <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                  Modo {mode === 'dark' ? 'Oscuro' : 'Claro'}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Se aplica a toda la plataforma y se guarda automáticamente
                </Typography>
              </Box>
            </Box>
            <FormControlLabel
              control={
                <Switch
                  checked={mode === 'dark'}
                  onChange={toggleTheme}
                  color="primary"
                />
              }
              label=""
              sx={{ m: 0 }}
            />
          </Box>

          <Box sx={{ mt: 2, p: 2, borderRadius: 2, bgcolor: 'action.hover' }}>
            <Typography variant="caption" color="text.secondary">
              <InfoOutlinedIcon sx={{ fontSize: 14, mr: 0.5, verticalAlign: 'middle' }} />
              El modo oscuro/claro también está disponible en el botón del header de la tienda.
            </Typography>
          </Box>
        </CardContent>
      </Card>

      {/* ── Modelo de detección de fraude ───────────────── */}
      <Card elevation={0} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 3, mb: 3 }}>
        <CardContent sx={{ p: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2 }}>
            <PsychologyIcon color="primary" />
            <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>Modelo antifraude</Typography>
          </Box>
          <Divider sx={{ mb: 3 }} />

          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            El modelo aprende de los pedidos que se marcaron como fraude real en
            la pantalla de órdenes. Reentrenar lo vuelve a ajustar con todo ese
            historial y recarga la versión nueva sin reiniciar el servidor.
          </Typography>

          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2 }}>
            <Typography variant="body2" sx={{ fontWeight: 600 }}>Estado actual</Typography>
            {consultando ? (
              <CircularProgress size={18} />
            ) : salud?.ml_model === 'loaded' ? (
              <Chip icon={<CheckCircleIcon />} label="Cargado" size="small" color="success" variant="outlined" sx={{ fontWeight: 700 }} />
            ) : (
              <Chip label="No cargado" size="small" color="warning" variant="outlined" sx={{ fontWeight: 700 }} />
            )}
          </Box>

          {avisoModelo && (
            <Alert severity={avisoModelo.tipo} sx={{ mb: 2 }}>
              {avisoModelo.texto}
            </Alert>
          )}

          <Button
            variant="contained"
            size="small"
            onClick={reentrenar}
            disabled={reentrenando}
            sx={{ textTransform: 'none', fontWeight: 600, borderRadius: 2 }}
          >
            {reentrenando ? 'Iniciando...' : 'Reentrenar modelo'}
          </Button>
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1.5 }}>
            El entrenamiento corre en segundo plano y puede tardar varios
            minutos. Puedes seguir usando el panel mientras tanto.
          </Typography>
        </CardContent>
      </Card>

      {/* ── API y Sistema ───────────────────────────────── */}
      <Card elevation={0} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 3, mb: 3 }}>
        <CardContent sx={{ p: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2 }}>
            <ApiIcon color="primary" />
            <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>Estado del Sistema</Typography>
          </Box>
          <Divider sx={{ mb: 3 }} />

          {componentes.map((item) => (
            <Box
              key={item.label}
              sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', py: 1.5, borderBottom: '1px solid', borderColor: 'divider', '&:last-child': { borderBottom: 'none' } }}
            >
              <Box>
                <Typography variant="body2" sx={{ fontWeight: 600 }}>{item.label}</Typography>
                {item.note && <Typography variant="caption" color="text.secondary">{item.note}</Typography>}
              </Box>
              {item.estado === 'cargando' ? (
                <CircularProgress size={18} />
              ) : item.estado === 'ok' ? (
                <Chip icon={<CheckCircleIcon />} label="Activo" size="small" color="success" variant="outlined" sx={{ fontWeight: 700 }} />
              ) : item.estado === 'error' ? (
                <Chip icon={<ErrorIcon />} label="Error" size="small" color="error" variant="outlined" sx={{ fontWeight: 700 }} />
              ) : (
                <Chip label="Parcial" size="small" color="warning" variant="outlined" sx={{ fontWeight: 700 }} />
              )}
            </Box>
          ))}

          <Button
            variant="outlined"
            size="small"
            onClick={consultarSalud}
            disabled={consultando}
            sx={{ mt: 2, textTransform: 'none', fontWeight: 600, borderRadius: 2 }}
          >
            {consultando ? 'Verificando...' : 'Verificar conexión'}
          </Button>
        </CardContent>
      </Card>

      {/* ── Info de la Tienda ────────────────────────────── */}
      <Card elevation={0} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 3 }}>
        <CardContent sx={{ p: 3 }}>
          <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 2 }}>Información de la Tienda</Typography>
          <Divider sx={{ mb: 3 }} />
          {[
            { label: 'Nombre', value: 'GRUPO STS SAC' },
            { label: 'Ubicación', value: 'Trujillo, La Libertad — Perú' },
            { label: 'Moneda', value: 'Soles (S/)' },
            { label: 'Versión del sistema', value: '1.0.0' },
          ].map((item) => (
            <Box
              key={item.label}
              sx={{ display: 'flex', justifyContent: 'space-between', py: 1.5, borderBottom: '1px solid', borderColor: 'divider', '&:last-child': { borderBottom: 'none' } }}
            >
              <Typography variant="body2" color="text.secondary">{item.label}</Typography>
              <Typography variant="body2" sx={{ fontWeight: 600 }}>{item.value}</Typography>
            </Box>
          ))}
        </CardContent>
      </Card>
    </>
  )
}
