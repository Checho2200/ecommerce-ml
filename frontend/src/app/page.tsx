'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import Header from '@/components/ui/Header'
import ProductCard, { ProductCardSkeleton } from '@/components/ui/ProductCard'
import FraudSection from '@/components/home/FraudSection'
import SafeImage from '@/components/ui/SafeImage'
import WhatsAppFab from '@/components/ui/WhatsAppFab'
import { DISPLAY_FONT } from '@/components/ThemeProvider'
import { api, ProductResponse, CategoryResponse } from '@/lib/api'

import {
  Container,
  Typography,
  Button,
  Box,
  Grid,
  Snackbar,
  Alert,
  Stack,
} from '@mui/material'
import ArrowForwardIcon from '@mui/icons-material/ArrowForward'
import LocationOnIcon from '@mui/icons-material/LocationOn'
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

// Datos tomados del sitio oficial: https://gruposts.com.pe
const COMPANY = {
  aboutImage: '/brand/equipo.webp',
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

      {/* ── HERO COMERCIAL ────────────────────────────────── */}
      <Container maxWidth="lg" sx={{ pt: { xs: 2, md: 3 }, pb: { xs: 2, md: 2 } }}>
        <Grid container spacing={2}>
          {/* Bloque principal */}
          <Grid size={{ xs: 12, md: 8 }}>
            <Box
              sx={{
                position: 'relative',
                overflow: 'hidden',
                bgcolor: 'primary.main',
                color: '#FFFFFF',
                px: { xs: 3, sm: 5, md: 6 },
                py: { xs: 4.5, md: 6 },
                minHeight: { xs: 'auto', md: 360 },
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'center',
              }}
            >
              <Box
                aria-hidden
                sx={{
                  position: 'absolute', right: -90, top: -90,
                  width: 340, height: 340, borderRadius: '50%',
                  bgcolor: 'rgba(255,206,0,0.14)', pointerEvents: 'none',
                }}
              />
              <Box sx={{ position: 'relative' }}>
                <Box
                  sx={{
                    display: 'inline-block', bgcolor: 'secondary.main', color: 'primary.main',
                    fontSize: 12, fontWeight: 800, letterSpacing: '0.08em', px: 1.5, py: 0.7,
                  }}
                >
                  ARMA TU PC
                </Box>
                <Typography
                  variant="h1"
                  sx={{
                    fontSize: { xs: '2.05rem', sm: '2.7rem', md: '3.25rem' },
                    lineHeight: 1.03, mt: 2.2, color: '#FFFFFF',
                  }}
                >
                  Todo para tu equipo,<br />
                  con <Box component="span" sx={{ color: 'secondary.main' }}>garantía real.</Box>
                </Typography>
                <Typography
                  sx={{
                    color: 'rgba(255,255,255,0.85)', mt: 2, maxWidth: 420,
                    fontSize: { xs: '0.95rem', md: '1.02rem' }, lineHeight: 1.55,
                  }}
                >
                  Componentes originales con respaldo directo del taller que lleva
                  30 años en Trujillo.
                </Typography>
                <Button
                  component={Link}
                  href="/catalog"
                  variant="contained"
                  color="secondary"
                  endIcon={<ArrowForwardIcon />}
                  sx={{
                    mt: 3.2, px: 3.5, py: 1.4, fontWeight: 800, fontSize: '0.95rem',
                    width: { xs: '100%', sm: 'auto' },
                    '&:active': { transform: 'scale(0.98)' },
                  }}
                >
                  Ver catálogo
                </Button>
              </Box>
            </Box>
          </Grid>

          {/* Dos tarjetas de apoyo */}
          <Grid size={{ xs: 12, md: 4 }}>
            <Stack spacing={2} sx={{ height: '100%' }}>
              <Box
                component={Link}
                href="/services"
                sx={{
                  flexGrow: 1, bgcolor: 'secondary.main', color: 'primary.main',
                  px: 3, py: { xs: 2.5, md: 3 }, textDecoration: 'none',
                  display: 'flex', flexDirection: 'column', justifyContent: 'center',
                  transition: 'filter 0.2s',
                  '@media (hover: hover)': { '&:hover': { filter: 'brightness(0.95)' } },
                  '&:active': { transform: 'scale(0.99)' },
                }}
              >
                <Typography sx={{ fontFamily: DISPLAY_FONT, fontSize: { xs: '1.4rem', md: '1.65rem' }, lineHeight: 1.1 }}>
                  Servicio técnico
                </Typography>
                <Typography sx={{ fontSize: '0.88rem', mt: 1, opacity: 0.85, lineHeight: 1.5 }}>
                  Laptops, PCs, impresoras y celulares.
                </Typography>
              </Box>

              <Box
                sx={{
                  flexGrow: 1, bgcolor: 'background.paper',
                  border: '1px solid', borderColor: 'divider',
                  px: 3, py: { xs: 2.5, md: 3 },
                  display: 'flex', flexDirection: 'column', justifyContent: 'center',
                }}
              >
                <Typography
                  sx={{
                    fontFamily: DISPLAY_FONT, fontSize: { xs: '1.4rem', md: '1.65rem' },
                    lineHeight: 1.1, color: 'primary.main',
                  }}
                >
                  Delivery a todo el Perú
                </Typography>
                <Typography sx={{ fontSize: '0.88rem', mt: 1, color: 'text.secondary', lineHeight: 1.5 }}>
                  Despacho en 24 a 48 horas útiles.
                </Typography>
              </Box>
            </Stack>
          </Grid>
        </Grid>
      </Container>

      {/* ── CATEGORÍAS ────────────────────────────────────── */}
      <Container maxWidth="lg" sx={{ pb: { xs: 3, md: 4 } }}>
        <Box
          sx={{
            display: 'flex',
            gap: 1.5,
            flexWrap: { xs: 'nowrap', md: 'wrap' },
            overflowX: { xs: 'auto', md: 'visible' },
            scrollSnapType: { xs: 'x proximity', md: 'none' },
            WebkitOverflowScrolling: 'touch',
            scrollbarWidth: 'none',
            '&::-webkit-scrollbar': { display: 'none' },
            mx: { xs: -2, md: 0 },
            px: { xs: 2, md: 0 },
          }}
        >
          {(loading ? Array.from({ length: 7 }) : categories).map((cat, i) => {
            const base = {
              flex: { xs: '0 0 108px', md: '1 1 calc(14.2857% - 13px)' },
              scrollSnapAlign: 'start' as const,
              height: { xs: 100, md: 112 },
              border: '1px solid',
              borderColor: 'divider',
            }

            if (loading || !cat) {
              return <Box key={`cat-sk-${i}`} sx={{ ...base, bgcolor: 'action.hover' }} />
            }

            const c = cat as CategoryResponse
            const Icon = CATEGORY_ICONS[c.slug] ?? CategoryIcon
            return (
              <Box
                key={c.id}
                component={Link}
                href={`/catalog?category_id=${c.id}`}
                sx={{
                  ...base,
                  bgcolor: 'background.paper', textDecoration: 'none',
                  display: 'flex', flexDirection: 'column',
                  alignItems: 'center', justifyContent: 'center',
                  gap: 1, p: 1.2, textAlign: 'center',
                  transition: 'all 0.22s',
                  '@media (hover: hover)': {
                    '&:hover': {
                      borderColor: 'primary.main',
                      '& .cat-icon': { color: 'primary.main' },
                    },
                  },
                  '&:active': { transform: 'scale(0.97)', borderColor: 'primary.main' },
                }}
              >
                <Icon className="cat-icon" sx={{ fontSize: { xs: 24, md: 27 }, color: 'primary.main', transition: 'color 0.22s' }} />
                <Typography
                  sx={{
                    fontSize: { xs: '0.72rem', md: '0.78rem' }, fontWeight: 700,
                    color: 'text.primary', lineHeight: 1.25,
                  }}
                >
                  {c.name}
                </Typography>
              </Box>
            )
          })}
        </Box>
      </Container>

      {/* ── PRODUCTOS ─────────────────────────────────────── */}
      <Container maxWidth="lg" sx={{ pb: { xs: 5, md: 7 } }}>
        <Stack direction="row" spacing={2} sx={{ alignItems: 'center', mb: 2.5 }}>
          <Typography
            sx={{
              fontFamily: DISPLAY_FONT, color: 'primary.main',
              fontSize: { xs: '1.3rem', md: '1.6rem' }, whiteSpace: 'nowrap',
            }}
          >
            Lo más vendido
          </Typography>
          <Box sx={{ flexGrow: 1, height: 3, bgcolor: 'secondary.main' }} />
          <Typography
            component={Link}
            href="/catalog"
            sx={{
              fontSize: '0.85rem', fontWeight: 700, color: 'primary.main',
              textDecoration: 'none', whiteSpace: 'nowrap',
            }}
          >
            Ver todo →
          </Typography>
        </Stack>

        {slow && (
          <Alert severity="info" sx={{ mb: 2.5 }}>
            Estamos activando el servidor. La primera carga puede tardar hasta 50 segundos.
          </Alert>
        )}

        {failed ? (
          <Box sx={{ textAlign: 'center', py: { xs: 5, md: 7 }, px: 2, border: '1px dashed', borderColor: 'divider' }}>
            <Typography sx={{ fontWeight: 700, fontSize: '1.05rem' }}>
              No pudimos cargar los productos
            </Typography>
            <Typography color="text.secondary" sx={{ mt: 1, mb: 3 }}>
              El servidor puede estar despertando. Vuelve a intentarlo en unos segundos.
            </Typography>
            <Button variant="contained" startIcon={<RefreshIcon />} onClick={() => setReloadKey((k) => k + 1)}>
              Reintentar
            </Button>
          </Box>
        ) : (
          <Grid container spacing={{ xs: 1.5, sm: 2 }}>
            {loading
              ? Array.from({ length: FEATURED_COUNT }).map((_, i) => (
                  <Grid size={{ xs: 6, sm: 6, md: 3 }} key={`p-sk-${i}`}>
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

      {/* ── CONFIANZA ─────────────────────────────────────── */}
      <FraudSection />

      {/* ── SOBRE NOSOTROS ────────────────────────────────── */}
      <Container maxWidth="lg" sx={{ py: { xs: 5, md: 8 } }}>
        <Grid container spacing={{ xs: 3, md: 6 }} sx={{ alignItems: 'center' }}>
          <Grid size={{ xs: 12, md: 6 }} sx={{ order: { xs: 1, md: 2 } }}>
            <Box sx={{ overflow: 'hidden', aspectRatio: '16/10' }}>
              <SafeImage src={COMPANY.aboutImage} alt="Equipo de Grupo STS SAC" objectFit="cover" />
            </Box>
          </Grid>

          <Grid size={{ xs: 12, md: 6 }} sx={{ order: { xs: 2, md: 1 } }}>
            <Stack direction="row" spacing={1.5} sx={{ alignItems: 'baseline', mb: 2 }}>
              <Typography sx={{ fontFamily: DISPLAY_FONT, fontSize: '2.6rem', color: 'secondary.main', lineHeight: 1 }}>
                +30
              </Typography>
              <Typography sx={{ fontWeight: 700, color: 'text.secondary', fontSize: '0.95rem' }}>
                años en el mercado tecnológico
              </Typography>
            </Stack>

            <Typography
              variant="h4"
              sx={{ fontSize: { xs: '1.45rem', md: '1.9rem' }, color: 'primary.main', mb: 2 }}
            >
              Tecnología y soporte que inspiran confianza
            </Typography>

            <Typography color="text.secondary" sx={{ lineHeight: 1.8, mb: 2.5 }}>
              {COMPANY.description}
            </Typography>

            <Stack direction="row" spacing={1} sx={{ alignItems: 'flex-start', mb: 3 }}>
              <LocationOnIcon sx={{ color: 'primary.main', fontSize: 20, mt: 0.2, flexShrink: 0 }} />
              <Typography variant="body2" color="text.secondary">
                {COMPANY.location}
              </Typography>
            </Stack>

            <Button
              component={Link}
              href="/services"
              variant="outlined"
              endIcon={<ArrowForwardIcon />}
              sx={{ fontWeight: 700, width: { xs: '100%', sm: 'auto' } }}
            >
              Conoce nuestro servicio técnico
            </Button>
          </Grid>
        </Grid>
      </Container>

      {/* ── CIERRE ────────────────────────────────────────── */}
      <Box sx={{ bgcolor: 'primary.main', color: '#FFFFFF', py: { xs: 5, md: 7 } }}>
        <Container maxWidth="md" sx={{ textAlign: 'center' }}>
          <Typography
            variant="h4"
            sx={{ fontSize: { xs: '1.5rem', md: '2rem' }, color: '#FFFFFF' }}
          >
            ¿No encuentras lo que buscas?
          </Typography>
          <Typography sx={{ mt: 1.5, mb: 3.5, color: 'rgba(255,255,255,0.85)', fontSize: '1rem' }}>
            Escríbenos por WhatsApp y te cotizamos el equipo completo.
          </Typography>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5} sx={{ justifyContent: 'center' }}>
            <Button
              component="a"
              href="https://wa.me/51924215320"
              target="_blank"
              rel="noopener noreferrer"
              variant="contained"
              color="secondary"
              size="large"
              sx={{ px: 4, py: 1.4, fontWeight: 800 }}
            >
              Escribir por WhatsApp
            </Button>
            <Button
              component={Link}
              href="/catalog"
              variant="outlined"
              size="large"
              sx={{
                px: 4, py: 1.4, fontWeight: 800, color: '#FFFFFF',
                borderColor: 'rgba(255,255,255,0.6)',
                '&:hover': { borderColor: '#FFFFFF', bgcolor: 'rgba(255,255,255,0.1)' },
              }}
            >
              Ir al catálogo
            </Button>
          </Stack>
        </Container>
      </Box>

      <WhatsAppFab />

      <Snackbar
        open={!!snackbar}
        autoHideDuration={2500}
        onClose={() => setSnackbar(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
        sx={{ bottom: { xs: 88, sm: 24 } }}
      >
        <Alert onClose={() => setSnackbar(null)} severity="success" variant="filled" sx={{ width: '100%' }}>
          {snackbar}
        </Alert>
      </Snackbar>
    </Box>
  )
}
