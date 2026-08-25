'use client'

import { useState, useEffect } from 'react'
import { useThemeStore } from '@/lib/stores/theme'
import { api } from '@/lib/api'

import {
  Box, Typography, Card, CardContent, Divider,
  Switch, FormControlLabel, Chip, Button, CircularProgress,
} from '@mui/material'
import DarkModeIcon from '@mui/icons-material/DarkMode'
import LightModeIcon from '@mui/icons-material/LightMode'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import ErrorIcon from '@mui/icons-material/Error'
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined'
import PaletteIcon from '@mui/icons-material/Palette'
import ApiIcon from '@mui/icons-material/Api'

export default function AdminSettingsPage() {
  const { mode, toggleTheme } = useThemeStore()
  const [apiStatus, setApiStatus] = useState<'idle' | 'loading' | 'ok' | 'error'>('idle')

  const pingApi = async () => {
    setApiStatus('loading')
    try {
      await api.categories.list()
      setApiStatus('ok')
    } catch {
      setApiStatus('error')
    }
  }

  useEffect(() => {
    pingApi()
  }, [])

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

      {/* ── API y Sistema ───────────────────────────────── */}
      <Card elevation={0} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 3, mb: 3 }}>
        <CardContent sx={{ p: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2 }}>
            <ApiIcon color="primary" />
            <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>Estado del Sistema</Typography>
          </Box>
          <Divider sx={{ mb: 3 }} />

          {[
            { label: 'Frontend (Next.js)', version: '16.3.2', status: 'ok' as const },
            { label: 'Backend API', status: apiStatus === 'ok' ? 'ok' as const : apiStatus === 'error' ? 'error' as const : 'loading' as const },
            { label: 'Base de Datos', status: 'ok' as const, note: 'SQLite' },
            { label: 'Motor Antifraude', status: 'warning' as const, note: 'Reglas heurísticas activas' },
          ].map((item) => (
            <Box
              key={item.label}
              sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', py: 1.5, borderBottom: '1px solid', borderColor: 'divider', '&:last-child': { borderBottom: 'none' } }}
            >
              <Box>
                <Typography variant="body2" sx={{ fontWeight: 600 }}>{item.label}</Typography>
                {item.note && <Typography variant="caption" color="text.secondary">{item.note}</Typography>}
                {item.version && <Typography variant="caption" color="text.secondary"> v{item.version}</Typography>}
              </Box>
              {item.status === 'loading' ? (
                <CircularProgress size={18} />
              ) : item.status === 'ok' ? (
                <Chip icon={<CheckCircleIcon />} label="Activo" size="small" color="success" variant="outlined" sx={{ fontWeight: 700 }} />
              ) : item.status === 'error' ? (
                <Chip icon={<ErrorIcon />} label="Error" size="small" color="error" variant="outlined" sx={{ fontWeight: 700 }} />
              ) : (
                <Chip label="Parcial" size="small" color="warning" variant="outlined" sx={{ fontWeight: 700 }} />
              )}
            </Box>
          ))}

          <Button
            variant="outlined"
            size="small"
            onClick={pingApi}
            disabled={apiStatus === 'loading'}
            sx={{ mt: 2, textTransform: 'none', fontWeight: 600, borderRadius: 2 }}
          >
            {apiStatus === 'loading' ? 'Verificando...' : 'Verificar conexión'}
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
