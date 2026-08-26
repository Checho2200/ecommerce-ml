'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import Header from '@/components/ui/Header'
import ProductCard, { ProductCardSkeleton } from '@/components/ui/ProductCard'
import FraudSection from '@/components/home/FraudSection'
import SafeImage from '@/components/ui/SafeImage'
import { api, ProductResponse, CategoryResponse } from '@/lib/api'

import {
  Container,
  Typography,
  Button,
  Box,
  Grid,
  Chip,
  Snackbar,
  Alert,
  Stack,
} from '@mui/material'
import LocalShippingOutlinedIcon from '@mui/icons-material/LocalShippingOutlined'
import SupportAgentOutlinedIcon from '@mui/icons-material/SupportAgentOutlined'
import VerifiedOutlinedIcon from '@mui/icons-material/VerifiedOutlined'
import ArrowForwardIcon from '@mui/icons-material/ArrowForward'
import LocationOnIcon from '@mui/icons-material/LocationOn'
import GroupsIcon from '@mui/icons-material/Groups'
import EmojiEventsIcon from '@mui/icons-material/EmojiEvents'
import ShieldOutlinedIcon from '@mui/icons-material/ShieldOutlined'
import RefreshIcon from '@mui/icons-material/Refresh'

// Íconos por categoría
import MemoryIcon from '@mui/icons-material/Memory'
import VideogameAssetIcon from '@mui/icons-material/VideogameAsset'
import DeveloperBoardIcon from '@mui/icons-material/DeveloperBoard'
import StorageIcon from '@mui/icons-material/Storage'
import MonitorIcon from '@mui/icons-material/Monitor'
import KeyboardIcon from '@mui/icons-material/Keyboard'
import PowerIcon from '@mui/icons-material/Power'
import HeadphonesIcon from '@mui/icons-material/Headphones'
import RouterIcon from '@mui/icons-material/Router'
import CategoryIcon from '@mui/icons-material/Category'
import type { SvgIconComponent } from '@mui/icons-material'

/* ── Datos de la empresa ──────────────────────────────────── */
// Datos tomados del sitio oficial: https://gruposts.com.pe
const COMPANY = {
  heroImage: '/brand/hero.webp',
  aboutImage: '/brand/local.jpg',
  location: 'Jr. Alfonso Ugarte 493 — Centro Histórico de Trujillo',
  description:
    'Grupo STS es una empresa con más de 30 años de trayectoria en el mercado tecnológico y presencia en La Libertad y Piura. Brindamos soluciones integrales en soporte técnico de equipos informáticos, servidores de datos, y administración de redes y comunicaciones.',
}

/* Una sola fuente de verdad: alimenta la petición, los esqueletos y el render. */
const FEATURED_COUNT = 8

const CATEGORY_ICONS: Record<string, SvgIconComponent> = {
  'procesadores': MemoryIcon,
  'tarjetas-de-video': VideogameAssetIcon,
  'memorias-ram': DeveloperBoardIcon,
  'almacenamiento': StorageIcon,
  'monitores': MonitorIcon,
  'perifericos': KeyboardIcon,
  'cases-y-fuentes': PowerIcon,
  'placas-madre': DeveloperBoardIcon,
  'audio': HeadphonesIcon,
  'redes': RouterIcon,
}

const STATS = [
  { icon: EmojiEventsIcon, value: '+30 años', label: 'en el mercado tecnológico' },
  { icon: GroupsIcon, value: 'La Libertad y Piura', label: 'presencia regional' },
  { icon: LocationOnIcon, value: 'Trujillo', label: 'envíos a todo el Perú' },
]

const BENEFITS = [
  { icon: LocalShippingOutlinedIcon, title: 'Envío a todo el Perú', desc: 'Despacho rápido y seguro a nivel nacional.' },
  { icon: SupportAgentOutlinedIcon, title: 'Soporte técnico', desc: 'Te asesoramos para elegir el producto ideal.' },
  { icon: VerifiedOutlinedIcon, title: 'Garantía real', desc: 'Productos originales con respaldo directo.' },
]

export default function HomePage() {
  const [products, setProducts] = useState<ProductResponse[]>([])
  const [categories, setCategories] = useState<CategoryResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [failed, setFailed] = useState(false)
  const [slow, setSlow] = useState(false)
  const [snackbar, setSnackbar] = useState<string | null>(null)
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setFailed(false)
    setSlow(false)

    // Render duerme el backend tras ~15 min sin tráfico; si tarda, lo avisamos
    // en vez de dejar los esqueletos girando sin explicación.
    const slowTimer = setTimeout(() => !cancelled && setSlow(true), 3000)

    Promise.all([
      api.products.list({ per_page: FEATURED_COUNT, active_only: true }),
      api.categories.list(),
    ])
      .then(([prodRes, catRes]) => {
        if (cancelled) return
        setProducts(prodRes.items)
        setCategories(catRes)
      })
      .catch(() => {
        if (!cancelled) setFailed(true)
      })
      .finally(() => {
        if (cancelled) return
        clearTimeout(slowTimer)
        setLoading(false)
        setSlow(false)
      })

    return () => {
      cancelled = true
      clearTimeout(slowTimer)
    }
  }, [reloadKey])

  return (
    <Box>
      <Header />

      {/* ── HERO ──────────────────────────────────────────── */}
      <Box
        sx={{
          position: 'relative',
          minHeight: { xs: 460, md: 560 },
          display: 'flex',
          alignItems: 'center',
          overflow: 'hidden',
        }}
      >
        <Box
          component="img"
          src={COMPANY.heroImage}
          alt=""
          aria-hidden
          sx={{
            position: 'absolute', inset: 0, width: '100%', height: '100%',
            objectFit: 'cover',
          }}
        />
        <Box
          aria-hidden
          sx={{
            position: 'absolute', inset: 0,
            background:
              'linear-gradient(100deg, rgba(8,15,32,0.94) 0%, rgba(8,15,32,0.82) 45%, rgba(8,15,32,0.45) 100%)',
          }}
        />

        <Container maxWidth="lg" sx={{ position: 'relative', py: { xs: 7, md: 9 } }}>
          <Box sx={{ maxWidth: 660 }}>
            <Chip
              icon={<ShieldOutlinedIcon sx={{ fontSize: 16, color: '#93c5fd !important' }} />}
              label="Compra protegida por IA"
              component="a"
              href="#seguridad"
              clickable
              size="small"
              sx={{
                bgcolor: 'rgba(37,99,235,0.22)', color: '#bfdbfe',
                border: '1px solid rgba(147,197,253,0.4)',
                fontWeight: 700, mb: 2.5,
                '&:hover': { bgcolor: 'rgba(37,99,235,0.35)' },
              }}
            />
            <Typography
              variant="h1"
              sx={{
                color: 'white', fontWeight: 900, lineHeight: 1.1,
                fontSize: { xs: '2.2rem', sm: '2.8rem', md: '3.5rem' },
              }}
            >
              Tecnología para tu espacio de trabajo
            </Typography>
            <Typography
              sx={{
                color: 'rgba(255,255,255,0.82)', mt: 2.5, maxWidth: 540,
                fontSize: { xs: '1rem', md: '1.15rem' }, lineHeight: 1.75,
              }}
            >
              Procesadores, tarjetas de video, memorias y periféricos con garantía real.
              Asesoría honesta y servicio técnico especializado en Trujillo.
            </Typography>

            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.8} sx={{ mt: 4 }}>
              <Button
                component={Link}
                href="/catalog"
                variant="contained"
                size="large"
                endIcon={<ArrowForwardIcon />}
                sx={{ px: 3.5, py: 1.4, fontWeight: 700, fontSize: '1rem' }}
              >
                Ver catálogo
              </Button>
              <Button
                component={Link}
                href="/services"
                variant="outlined"
                size="large"
                sx={{
                  px: 3.5, py: 1.4, fontWeight: 700, fontSize: '1rem',
                  color: 'white', borderColor: 'rgba(255,255,255,0.5)',
                  '&:hover': { borderColor: 'white', bgcolor: 'rgba(255,255,255,0.08)' },
                }}
              >
                Servicio técnico
              </Button>
            </Stack>
          </Box>
        </Container>
      </Box>

      {/* ── BARRA DE CONFIANZA ────────────────────────────── */}
      <Box sx={{ bgcolor: 'background.paper', borderBottom: '1px solid', borderColor: 'divider' }}>
        <Container maxWidth="lg">
          <Grid container sx={{ py: { xs: 3, md: 3.5 } }}>
            {STATS.map((s) => (
              <Grid size={{ xs: 12, sm: 4 }} key={s.label}>
                <Stack
                  direction="row"
                  spacing={1.8}
                 
                 
                  sx={{ alignItems: "center", justifyContent: { xs: 'flex-start', sm: 'center' }, py: { xs: 1, sm: 0 } }}>
                  <s.icon sx={{ color: 'primary.main', fontSize: 30 }} />
                  <Box>
                    <Typography variant="h6" sx={{ fontWeight: 900, lineHeight: 1.1 }}>
                      {s.value}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {s.label}
                    </Typography>
                  </Box>
                </Stack>
              </Grid>
            ))}
          </Grid>
        </Container>
      </Box>

      {/* ── CATEGORÍAS ────────────────────────────────────── */}
      <Container maxWidth="lg" sx={{ py: { xs: 6, md: 9 } }}>
        <Box sx={{ textAlign: 'center', mb: 5 }}>
          <Typography variant="overline" sx={{ color: 'primary.main', fontWeight: 800, letterSpacing: 1.2 }}>
            CATEGORÍAS
          </Typography>
          <Typography variant="h4" sx={{ fontWeight: 900, mt: 0.5 }}>
            Explora por tipo de componente
          </Typography>
        </Box>

        <Grid container spacing={2.5}>
          {(loading ? Array.from({ length: 8 }) : categories).map((cat, i) => {
            if (loading || !cat) {
              return (
                <Grid size={{ xs: 6, sm: 4, md: 3 }} key={`cat-skeleton-${i}`}>
                  <Box
                    sx={{
                      height: 132, borderRadius: 3, border: '1px solid',
                      borderColor: 'divider', bgcolor: 'action.hover',
                    }}
                  />
                </Grid>
              )
            }
            const c = cat as CategoryResponse
            const Icon = CATEGORY_ICONS[c.slug] ?? CategoryIcon
            return (
              <Grid size={{ xs: 6, sm: 4, md: 3 }} key={c.id}>
                <Box
                  component={Link}
                  href={`/catalog?category_id=${c.id}`}
                  sx={{
                    display: 'flex', flexDirection: 'column', alignItems: 'center',
                    justifyContent: 'center', gap: 1.2, textAlign: 'center',
                    height: 132, p: 2, borderRadius: 3,
                    border: '1px solid', borderColor: 'divider',
                    bgcolor: 'background.paper', textDecoration: 'none',
                    transition: 'all 0.3s cubic-bezier(0.4,0,0.2,1)',
                    '&:hover': {
                      borderColor: 'primary.main',
                      transform: 'translateY(-6px)',
                      boxShadow: '0 16px 32px -12px rgba(0,0,0,0.16)',
                      '& .cat-icon': { color: 'primary.main', transform: 'scale(1.12)' },
                    },
                  }}
                >
                  <Icon
                    className="cat-icon"
                    sx={{ fontSize: 36, color: 'text.secondary', transition: 'all 0.3s' }}
                  />
                  <Typography variant="subtitle2" sx={{ fontWeight: 800, color: 'text.primary' }}>
                    {c.name}
                  </Typography>
                  {c.is_high_risk && (
                    <Typography variant="caption" sx={{ color: 'text.disabled', fontSize: '0.66rem' }}>
                      Alta demanda
                    </Typography>
                  )}
                </Box>
              </Grid>
            )
          })}
        </Grid>
      </Container>

      {/* ── PRODUCTOS DESTACADOS ──────────────────────────── */}
      <Box sx={{ bgcolor: 'background.paper', py: { xs: 6, md: 9 } }}>
        <Container maxWidth="lg">
          <Stack
            direction={{ xs: 'column', sm: 'row' }}
           
           
            spacing={2}
            sx={{ alignItems: { xs: 'flex-start', sm: 'flex-end' }, justifyContent: "space-between", mb: 4 }}>
            <Box>
              <Typography variant="overline" sx={{ color: 'primary.main', fontWeight: 800, letterSpacing: 1.2 }}>
                DESTACADOS
              </Typography>
              <Typography variant="h4" sx={{ fontWeight: 900, mt: 0.5 }}>
                Lo más buscado
              </Typography>
            </Box>
            <Button component={Link} href="/catalog" endIcon={<ArrowForwardIcon />} sx={{ fontWeight: 700 }}>
              Ver todo el catálogo
            </Button>
          </Stack>

          {slow && (
            <Alert severity="info" sx={{ mb: 3, borderRadius: 2 }}>
              Estamos activando el servidor. La primera carga puede tardar hasta 50 segundos.
            </Alert>
          )}

          {failed ? (
            <Box
              sx={{
                textAlign: 'center', py: 7, borderRadius: 3,
                border: '1px dashed', borderColor: 'divider',
              }}
            >
              <Typography variant="h6" sx={{ fontWeight: 700 }}>
                No pudimos cargar los productos
              </Typography>
              <Typography color="text.secondary" sx={{ mt: 1, mb: 3 }}>
                El servidor puede estar despertando. Vuelve a intentarlo en unos segundos.
              </Typography>
              <Button
                variant="contained"
                startIcon={<RefreshIcon />}
                onClick={() => setReloadKey((k) => k + 1)}
              >
                Reintentar
              </Button>
            </Box>
          ) : (
            <Grid container spacing={2.5}>
              {loading
                ? Array.from({ length: FEATURED_COUNT }).map((_, i) => (
                    <Grid size={{ xs: 6, sm: 6, md: 3 }} key={`prod-skeleton-${i}`}>
                      <ProductCardSkeleton />
                    </Grid>
                  ))
                : products.map((p, i) => (
                    <Grid size={{ xs: 6, sm: 6, md: 3 }} key={p.id}>
                      <ProductCard
                        product={p}
                        index={i}
                        onAdded={(prod) => setSnackbar(`${prod.name} agregado al carrito`)}
                      />
                    </Grid>
                  ))}
            </Grid>
          )}
        </Container>
      </Box>

      {/* ── SECCIÓN DE IA ANTIFRAUDE ──────────────────────── */}
      <FraudSection />

      {/* ── SOBRE NOSOTROS ────────────────────────────────── */}
      <Container maxWidth="lg" sx={{ py: { xs: 6, md: 10 } }}>
        <Grid container spacing={{ xs: 4, md: 7 }} sx={{ alignItems: "center" }}>
          <Grid size={{ xs: 12, md: 6 }}>
            <Typography variant="overline" sx={{ color: 'primary.main', fontWeight: 800, letterSpacing: 1.2 }}>
              SOBRE NOSOTROS
            </Typography>
            <Typography variant="h4" sx={{ fontWeight: 900, mt: 0.5, mb: 2.5 }}>
              Tecnología y soporte que inspiran confianza
            </Typography>
            <Typography color="text.secondary" sx={{ lineHeight: 1.85, mb: 2 }}>
              {COMPANY.description}
            </Typography>
            <Stack direction="row" spacing={1} sx={{ alignItems: "center", mb: 3.5 }}>
              <LocationOnIcon sx={{ color: 'primary.main', fontSize: 20 }} />
              <Typography variant="body2" color="text.secondary">
                {COMPANY.location}
              </Typography>
            </Stack>
            <Button
              component={Link}
              href="/services"
              variant="outlined"
              endIcon={<ArrowForwardIcon />}
              sx={{ fontWeight: 700 }}
            >
              Conoce nuestro servicio técnico
            </Button>
          </Grid>
          <Grid size={{ xs: 12, md: 6 }}>
            <Box sx={{ borderRadius: 4, overflow: 'hidden', aspectRatio: '16/10' }}>
              <SafeImage src={COMPANY.aboutImage} alt="Equipo de Grupo STS en su taller de Trujillo" objectFit="cover" />
            </Box>
          </Grid>
        </Grid>
      </Container>

      {/* ── BENEFICIOS ────────────────────────────────────── */}
      <Box sx={{ bgcolor: 'background.paper', py: { xs: 6, md: 8 }, borderTop: '1px solid', borderColor: 'divider' }}>
        <Container maxWidth="lg">
          <Grid container spacing={3}>
            {BENEFITS.map((b) => (
              <Grid size={{ xs: 12, md: 4 }} key={b.title}>
                <Stack direction="row" spacing={2.2} sx={{ alignItems: "flex-start" }}>
                  <Box
                    sx={{
                      flexShrink: 0, width: 48, height: 48, borderRadius: 2.5,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      bgcolor: 'primary.main', color: 'white',
                    }}
                  >
                    <b.icon />
                  </Box>
                  <Box>
                    <Typography variant="subtitle1" sx={{ fontWeight: 800 }}>
                      {b.title}
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, lineHeight: 1.7 }}>
                      {b.desc}
                    </Typography>
                  </Box>
                </Stack>
              </Grid>
            ))}
          </Grid>
        </Container>
      </Box>

      {/* ── CTA FINAL ─────────────────────────────────────── */}
      <Box
        sx={{
          py: { xs: 7, md: 9 },
          background: 'linear-gradient(120deg, #1d4ed8 0%, #2563eb 60%, #3b82f6 100%)',
          color: 'white',
        }}
      >
        <Container maxWidth="md" sx={{ textAlign: 'center' }}>
          <Typography variant="h4" sx={{ fontWeight: 900, fontSize: { xs: '1.7rem', md: '2.2rem' } }}>
            ¿Listo para armar tu equipo?
          </Typography>
          <Typography sx={{ mt: 1.5, mb: 4, color: 'rgba(255,255,255,0.85)', fontSize: '1.05rem' }}>
            Revisa el catálogo completo o escríbenos y te ayudamos a elegir.
          </Typography>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ justifyContent: "center" }}>
            <Button
              component={Link}
              href="/catalog"
              size="large"
              sx={{
                px: 4, py: 1.4, fontWeight: 800, bgcolor: 'white', color: 'primary.dark',
                '&:hover': { bgcolor: 'rgba(255,255,255,0.9)' },
              }}
            >
              Ir al catálogo
            </Button>
            <Button
              component={Link}
              href="/register"
              size="large"
              variant="outlined"
              sx={{
                px: 4, py: 1.4, fontWeight: 800, color: 'white',
                borderColor: 'rgba(255,255,255,0.6)',
                '&:hover': { borderColor: 'white', bgcolor: 'rgba(255,255,255,0.1)' },
              }}
            >
              Crear cuenta
            </Button>
          </Stack>
        </Container>
      </Box>

      <Snackbar
        open={!!snackbar}
        autoHideDuration={2500}
        onClose={() => setSnackbar(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert onClose={() => setSnackbar(null)} severity="success" variant="filled" sx={{ width: '100%' }}>
          {snackbar}
        </Alert>
      </Snackbar>
    </Box>
  )
}
