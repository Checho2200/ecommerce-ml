'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/lib/auth'
import { api, ApiError } from '@/lib/api'
import Header from '@/components/ui/Header'

import {
  Container, Box, Typography, Card, CardContent, Button, TextField,
  MenuItem, Select, FormControl, InputLabel, Alert, CircularProgress,
  Snackbar, Divider,
} from '@mui/material'
import BuildIcon from '@mui/icons-material/Build'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import LaptopIcon from '@mui/icons-material/Laptop'
import PhoneAndroidIcon from '@mui/icons-material/PhoneAndroid'
import DesktopWindowsIcon from '@mui/icons-material/DesktopWindows'
import PrintIcon from '@mui/icons-material/Print'
import ArrowForwardIcon from '@mui/icons-material/ArrowForward'
import ShieldIcon from '@mui/icons-material/Shield'

const DEVICE_TYPES = [
  { value: 'Laptop', icon: LaptopIcon },
  { value: 'Computadora de escritorio', icon: DesktopWindowsIcon },
  { value: 'Smartphone', icon: PhoneAndroidIcon },
  { value: 'Impresora', icon: PrintIcon },
  { value: 'Monitor', icon: DesktopWindowsIcon },
  { value: 'Otro', icon: BuildIcon },
]

const WHY_US = [
  { icon: ShieldIcon, title: 'Técnicos certificados', desc: 'Personal con experiencia y certificaciones en hardware.' },
  { icon: BuildIcon, title: 'Diagnóstico gratuito', desc: 'Te decimos qué tiene tu equipo antes de cobrar.' },
  { icon: CheckCircleIcon, title: 'Garantía de servicio', desc: '30 días de garantía en la reparación realizada.' },
]

export default function ServicesPage() {
  const { isAuthenticated, user } = useAuth()
  const router = useRouter()

  const [form, setForm] = useState({ device_type: '', brand: '', issue_description: '' })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  const [snackbar, setSnackbar] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.device_type || !form.issue_description.trim()) {
      setError('Completa el tipo de dispositivo y la descripción del problema.')
      return
    }
    setLoading(true)
    setError('')
    try {
      await api.serviceOrders.create({
        device_type: form.device_type,
        brand: form.brand || undefined,
        issue_description: form.issue_description,
      })
      setSuccess(true)
      setSnackbar('Solicitud de servicio enviada correctamente')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Error al enviar la solicitud.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
      <Header />

      {/* ── Hero ─────────────────────────────────────────── */}
      <Box sx={{ bgcolor: 'primary.main', py: { xs: 6, md: 8 }, color: 'white', textAlign: 'center' }}>
        <Container maxWidth="md">
          <BuildIcon sx={{ fontSize: 52, opacity: 0.85, mb: 1.5 }} />
          <Typography variant="h3" sx={{ fontWeight: 900, mb: 1.5, fontSize: { xs: '1.8rem', md: '2.5rem' } }}>
            Servicio Técnico
          </Typography>
          <Typography variant="h6" sx={{ opacity: 0.85, fontWeight: 400, maxWidth: 520, mx: 'auto' }}>
            Diagnóstico y reparación de equipos en Trujillo. Técnicos especializados con más de 10 años de experiencia.
          </Typography>
        </Container>
      </Box>

      <Container maxWidth="lg" sx={{ py: { xs: 5, md: 8 } }}>
        <Box className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-10">
          {WHY_US.map((item) => (
            <Box
              key={item.title}
              sx={{
                display: 'flex', flexDirection: 'column', alignItems: 'center',
                textAlign: 'center', p: 3.5, borderRadius: 3, border: '1px solid', borderColor: 'divider',
              }}
            >
              <Box sx={{ width: 52, height: 52, borderRadius: 2, bgcolor: 'primary.main', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', mb: 2 }}>
                <item.icon />
              </Box>
              <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>{item.title}</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>{item.desc}</Typography>
            </Box>
          ))}
        </Box>

        <Box className="flex flex-col lg:flex-row gap-6">
          {/* Formulario */}
          <Box sx={{ flex: 1 }}>
            <Card elevation={0} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 3 }}>
              <CardContent sx={{ p: 3 }}>
                <Typography variant="h6" sx={{ fontWeight: 700, mb: 3 }}>
                  {success ? '¡Solicitud enviada!' : 'Solicitar Servicio Técnico'}
                </Typography>

                {success ? (
                  <Box sx={{ textAlign: 'center', py: 4 }}>
                    <CheckCircleIcon sx={{ fontSize: 64, color: 'success.main', mb: 2 }} />
                    <Typography variant="h6" sx={{ fontWeight: 700, mb: 1 }}>¡Solicitud recibida!</Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 4 }}>
                      Nos pondremos en contacto contigo pronto para coordinar el diagnóstico de tu equipo.
                    </Typography>
                    <Button
                      component={Link}
                      href="/orders"
                      variant="contained"
                      endIcon={<ArrowForwardIcon />}
                      sx={{ textTransform: 'none', fontWeight: 700, borderRadius: 2 }}
                    >
                      Ver mis solicitudes
                    </Button>
                  </Box>
                ) : !isAuthenticated ? (
                  <Box sx={{ textAlign: 'center', py: 4 }}>
                    <ShieldIcon sx={{ fontSize: 48, color: 'text.disabled', mb: 2 }} />
                    <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1 }}>Inicia sesión para continuar</Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                      Necesitas una cuenta para solicitar servicio técnico y hacer seguimiento de tu equipo.
                    </Typography>
                    <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center' }}>
                      <Button component={Link} href="/login?redirect=/services" variant="contained" sx={{ textTransform: 'none', fontWeight: 700, borderRadius: 2 }}>
                        Iniciar Sesión
                      </Button>
                      <Button component={Link} href="/register?redirect=/services" variant="outlined" sx={{ textTransform: 'none', fontWeight: 700, borderRadius: 2 }}>
                        Crear Cuenta
                      </Button>
                    </Box>
                  </Box>
                ) : (
                  <>
                    {error && <Alert severity="error" sx={{ mb: 3, borderRadius: 2 }}>{error}</Alert>}
                    <Box component="form" onSubmit={handleSubmit} sx={{ display: 'flex', flexDirection: 'column', gap: 2.5 }}>
                      <FormControl fullWidth required>
                        <InputLabel>Tipo de Dispositivo</InputLabel>
                        <Select
                          value={form.device_type}
                          label="Tipo de Dispositivo"
                          onChange={(e) => setForm({ ...form, device_type: e.target.value })}
                        >
                          {DEVICE_TYPES.map((d) => (
                            <MenuItem key={d.value} value={d.value}>{d.value}</MenuItem>
                          ))}
                        </Select>
                      </FormControl>
                      <TextField
                        label="Marca / Modelo (opcional)"
                        fullWidth
                        value={form.brand}
                        onChange={(e) => setForm({ ...form, brand: e.target.value })}
                        placeholder="Ej. Lenovo ThinkPad E15"
                      />
                      <TextField
                        label="Descripción del problema"
                        fullWidth
                        required
                        multiline
                        rows={4}
                        value={form.issue_description}
                        onChange={(e) => setForm({ ...form, issue_description: e.target.value })}
                        placeholder="Describe lo que le ocurre a tu equipo con el mayor detalle posible..."
                      />
                      <Button
                        type="submit"
                        variant="contained"
                        size="large"
                        disabled={loading}
                        sx={{ textTransform: 'none', fontWeight: 700, borderRadius: 2, py: 1.5 }}
                      >
                        {loading ? <CircularProgress size={22} color="inherit" /> : 'Enviar Solicitud'}
                      </Button>
                    </Box>
                  </>
                )}
              </CardContent>
            </Card>
          </Box>

          {/* Info lateral */}
          <Box sx={{ width: { xs: '100%', lg: 300 }, flexShrink: 0 }}>
            <Card elevation={0} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 3, p: 3 }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 2 }}>¿Cómo funciona?</Typography>
              <Divider sx={{ mb: 2 }} />
              {[
                { step: '1', title: 'Envías tu solicitud', desc: 'Describe el problema de tu equipo.' },
                { step: '2', title: 'Te contactamos', desc: 'Coordinamos fecha y lugar de recojo o visita.' },
                { step: '3', title: 'Diagnóstico gratuito', desc: 'Evaluamos tu equipo y te damos un presupuesto.' },
                { step: '4', title: 'Reparación', desc: 'Con tu aprobación, procedemos con el servicio.' },
              ].map((item) => (
                <Box key={item.step} sx={{ display: 'flex', gap: 2, mb: 2.5 }}>
                  <Box sx={{ width: 28, height: 28, borderRadius: '50%', bgcolor: 'primary.main', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, fontSize: '0.8rem', fontWeight: 800 }}>
                    {item.step}
                  </Box>
                  <Box>
                    <Typography variant="body2" sx={{ fontWeight: 700 }}>{item.title}</Typography>
                    <Typography variant="caption" color="text.secondary">{item.desc}</Typography>
                  </Box>
                </Box>
              ))}
              <Divider sx={{ my: 2 }} />
              <Typography variant="caption" color="text.secondary">
                📍 Trujillo, La Libertad — también atendemos a Lima y otras ciudades vía envío.
              </Typography>
            </Card>
          </Box>
        </Box>
      </Container>

      <Snackbar open={!!snackbar} autoHideDuration={4000} onClose={() => setSnackbar('')} anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}>
        <Alert onClose={() => setSnackbar('')} severity="success" variant="filled">{snackbar}</Alert>
      </Snackbar>
    </Box>
  )
}
