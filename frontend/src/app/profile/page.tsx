'use client'

import { useEffect, useState, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/lib/auth'
import { api, ApiError } from '@/lib/api'
import Header from '@/components/ui/Header'

import {
  Container, Box, Typography, Card, CardContent, Button,
  TextField, Avatar, Divider, Alert, Snackbar, IconButton,
  CircularProgress, Skeleton,
} from '@mui/material'
import PhotoCameraIcon from '@mui/icons-material/PhotoCamera'
import SaveIcon from '@mui/icons-material/Save'
import PersonIcon from '@mui/icons-material/Person'
import ShoppingBagIcon from '@mui/icons-material/ShoppingBag'

export default function ProfilePage() {
  const { user, loading: authLoading, isAuthenticated, refresh } = useAuth()
  const router = useRouter()

  // El formulario no copia los datos del usuario con un efecto: guarda solo lo
  // que la persona escribio (`borrador`) y, mientras no haya escrito nada,
  // muestra lo que dice el contexto. Asi no hay dos copias del mismo dato que
  // puedan quedar desincronizadas, ni un render encadenado al montar.
  const [borrador, setBorrador] = useState<{ full_name: string; phone: string } | null>(null)
  const form = borrador ?? { full_name: user?.full_name ?? '', phone: user?.phone ?? '' }
  const setForm = (valores: { full_name: string; phone: string }) => setBorrador(valores)

  const [avatarSubido, setAvatarSubido] = useState<string | null>(null)
  const avatarUrl = avatarSubido ?? user?.avatar_url ?? null
  const setAvatarUrl = setAvatarSubido
  const [uploadingAvatar, setUploadingAvatar] = useState(false)
  const [saving, setSaving] = useState(false)
  const [snackbar, setSnackbar] = useState<{ msg: string; severity: 'success' | 'error' } | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login?redirect=/profile')
    }
  }, [authLoading, isAuthenticated, router])

  const handleAvatarChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploadingAvatar(true)
    try {
      const { url } = await api.upload.image(file)
      // El usuario todavia no tiene columna para la foto en la base de datos,
      // asi que el backend acepta la peticion y la ignora: la imagen ya quedo
      // subida y aqui se muestra, pero no sobrevive a un cierre de sesion.
      await api.auth.updateProfile({ avatar_url: url })
      setAvatarUrl(url)
      setSnackbar({ msg: 'Foto de perfil actualizada', severity: 'success' })
    } catch {
      setSnackbar({ msg: 'Error al subir la imagen', severity: 'error' })
    } finally {
      setUploadingAvatar(false)
    }
  }

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      await api.auth.updateProfile({ full_name: form.full_name, phone: form.phone })
      // Se relee el perfil para que el nombre nuevo aparezca tambien en la
      // cabecera, y el borrador local deja de hacer falta.
      await refresh()
      setBorrador(null)
      setSnackbar({ msg: 'Perfil actualizado correctamente', severity: 'success' })
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'No se pudo actualizar el perfil. Intentalo de nuevo.'
      setSnackbar({ msg, severity: 'error' })
    } finally {
      setSaving(false)
    }
  }

  if (authLoading) {
    return (
      <Box sx={{ minHeight: '100dvh', bgcolor: 'background.default' }}>
        <Header />
        <Container maxWidth="sm" sx={{ py: 6 }}>
          <Skeleton variant="circular" width={96} height={96} sx={{ mx: 'auto', mb: 2 }} />
          <Skeleton variant="rounded" height={56} sx={{ mb: 2 }} />
          <Skeleton variant="rounded" height={56} />
        </Container>
      </Box>
    )
  }

  if (!user) return null

  return (
    <Box sx={{ minHeight: '100dvh', bgcolor: 'background.default' }}>
      <Header />

      <Container maxWidth="sm" sx={{ py: { xs: 4, md: 6 } }}>
        <Typography variant="h4" sx={{ fontWeight: 900, mb: 4 }}>Mi Perfil</Typography>

        {/* ── Foto de Perfil ─────────────────────────────── */}
        <Card elevation={0} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 3, mb: 3 }}>
          <CardContent sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 3 }}>
              <Box sx={{ position: 'relative' }}>
                <Avatar
                  src={avatarUrl || undefined}
                  sx={{ width: 88, height: 88, border: '3px solid', borderColor: 'primary.main', fontSize: '2rem' }}
                >
                  {user.full_name.charAt(0).toUpperCase()}
                </Avatar>
                <IconButton
                  onClick={() => fileRef.current?.click()}
                  disabled={uploadingAvatar}
                  size="small"
                  sx={{
                    position: 'absolute', bottom: -4, right: -4,
                    bgcolor: 'primary.main', color: 'white', width: 32, height: 32,
                    '&:hover': { bgcolor: 'primary.dark' },
                  }}
                >
                  {uploadingAvatar ? <CircularProgress size={14} color="inherit" /> : <PhotoCameraIcon sx={{ fontSize: 16 }} />}
                </IconButton>
                <input type="file" accept="image/*" ref={fileRef} style={{ display: 'none' }} onChange={handleAvatarChange} />
              </Box>
              <Box>
                <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>{user.full_name}</Typography>
                <Typography variant="body2" color="text.secondary">{user.email}</Typography>
                <Typography variant="caption" color="primary" sx={{ fontWeight: 700, textTransform: 'uppercase', letterSpacing: 1 }}>
                  {user.role}
                </Typography>
              </Box>
            </Box>
          </CardContent>
        </Card>

        {/* ── Datos Personales ────────────────────────────── */}
        <Card elevation={0} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 3, mb: 3 }}>
          <CardContent sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 3 }}>
              <PersonIcon color="primary" />
              <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>Datos Personales</Typography>
            </Box>
            <Box component="form" onSubmit={handleSave} sx={{ display: 'flex', flexDirection: 'column', gap: 2.5 }}>
              <TextField
                label="Nombre completo"
                fullWidth
                value={form.full_name}
                onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                required
              />
              <TextField
                label="Email"
                fullWidth
                value={user.email}
                disabled
                helperText="El email no se puede cambiar"
              />
              <TextField
                label="Teléfono"
                fullWidth
                value={form.phone}
                onChange={(e) => setForm({ ...form, phone: e.target.value })}
                placeholder="987654321"
              />
              <Button
                type="submit"
                variant="contained"
                disabled={saving}
                startIcon={saving ? <CircularProgress size={16} color="inherit" /> : <SaveIcon />}
                sx={{ textTransform: 'none', fontWeight: 700, borderRadius: 2, py: 1.5, alignSelf: 'flex-start' }}
              >
                {saving ? 'Guardando...' : 'Guardar cambios'}
              </Button>
            </Box>
          </CardContent>
        </Card>

        {/* ── Accesos rápidos ──────────────────────────────── */}
        <Card elevation={0} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 3 }}>
          <CardContent sx={{ p: 3 }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 2 }}>Accesos rápidos</Typography>
            <Divider sx={{ mb: 2 }} />
            <Button
              fullWidth
              variant="outlined"
              startIcon={<ShoppingBagIcon />}
              href="/orders"
              sx={{ textTransform: 'none', fontWeight: 600, borderRadius: 2, justifyContent: 'flex-start', mb: 1.5 }}
            >
              Ver mis compras
            </Button>
            <Button
              fullWidth
              variant="outlined"
              href="/cart"
              sx={{ textTransform: 'none', fontWeight: 600, borderRadius: 2, justifyContent: 'flex-start' }}
            >
              Ir al carrito
            </Button>
          </CardContent>
        </Card>
      </Container>

      <Snackbar
        open={!!snackbar}
        autoHideDuration={3500}
        onClose={() => setSnackbar(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert onClose={() => setSnackbar(null)} severity={snackbar?.severity} variant="filled" sx={{ width: '100%' }}>
          {snackbar?.msg}
        </Alert>
      </Snackbar>
    </Box>
  )
}
