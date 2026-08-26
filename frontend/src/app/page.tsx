'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import Header from '@/components/ui/Header'
import ProductCard, { ProductCardSkeleton } from '@/components/ui/ProductCard'
import FraudSection from '@/components/home/FraudSection'
import SafeImage from '@/components/ui/SafeImage'
import WhatsAppFab from '@/components/ui/WhatsAppFab'
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

// Datos tomados del sitio oficial: https://gruposts.com.pe
const COMPANY = {
  heroImage: '/brand/tienda.webp',
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

const STATS = [
  { icon: EmojiEventsIcon, value: '+30 años', label: 'de trayectoria' },
  { icon: GroupsIcon, value: 'Trujillo y Piura', label: 'presencia regional' },
  { icon: LocalShippingOutlinedIcon, value: 'Todo el Perú', label: 'cobertura de envíos' },
]

const BENEFITS = [
  { icon: LocalShippingOutlinedIcon, title: 'Envío a todo el Perú', desc: 'Despacho rápido y seguro a nivel nacional.' },
  { icon: SupportAgentOutlinedIcon, title: 'Soporte técnico', desc: 'Te asesoramos para elegir el producto ideal.' },
  { icon: VerifiedOutlinedIcon, title: 'Garantía real', desc: 'Productos originales con respaldo directo.' },
]

/** Encabezado de sección, para que el ritmo sea el mismo en toda la portada. */
function SectionHeading({
  eyebrow,
  title,
  center = false,
}: {
  eyebrow: string
  title: string
  center?: boolean
}) {
  return (
    <Box sx={{ textAlign: center ? 'center' : 'left' }}>
      <Typography
        variant="overline"
        sx={{ color: 'primary.main', fontWeight: 800, letterSpacing: 1.2, lineHeight: 1.6 }}
      >
        {eyebrow}
      </Typography>
      <Typography
        variant="h4"
        sx={{ fontWeight: 900, mt: 0.5, fontSize: { xs: '1.55rem', sm: '1.9rem', md: '2.125rem' } }}
      >
        {title}
      </Typography>
    </Box>
  )
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

      {/* ── HERO ──────────────────────────────────────────── */}
      <Box
        sx={{
          position: 'relative',
          minHeight: { xs: 520, sm: 500, md: 580 },
          display: 'flex',
          // En móvil el texto se apoya abajo, sobre la parte más oscura.
          alignItems: { xs: 'flex-end', md: 'center' },
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
            // En pantallas angostas encuadra el mostrador, no el borde derecho.
            objectPosition: { xs: '32% center', md: 'center' },
          }}
        />
        <Box
          aria-hidden
          sx={{
            position: 'absolute', inset: 0,
            // El degradado horizontal solo funciona donde el texto ocupa la
            // mitad izquierda. En un teléfono el texto va de borde a borde, así
            // que ahí el oscurecido tiene que venir desde abajo.
            background: {
              xs: 'linear-gradient(to top, rgba(4,16,38,0.97) 30%, rgba(4,16,38,0.88) 58%, rgba(4,16,38,0.60) 100%)',
              md: 'linear-gradient(100deg, rgba(4,16,38,0.94) 0%, rgba(4,16,38,0.86) 38%, rgba(4,16,38,0.58) 68%, rgba(4,16,38,0.38) 100%)',
            },
          }}
        />

        <Container maxWidth="lg" sx={{ position: 'relative', py: { xs: 5, md: 9 } }}>
          <Box sx={{ maxWidth: { xs: '100%', md: 660 } }}>
            <Chip
              icon={<ShieldOutlinedIcon sx={{ fontSize: 16, color: '#93c5fd !important' }} />}
              label="Compra protegida"
              component="a"
              href="#seguridad"
              clickable
              size="small"
              sx={{
                bgcolor: 'rgba(37,99,235,0.25)', color: '#bfdbfe',
                border: '1px solid rgba(147,197,253,0.4)',
                fontWeight: 700, mb: { xs: 2, md: 2.5 },
                '&:hover': { bgcolor: 'rgba(37,99,235,0.4)' },
              }}
            />
            <Typography
              variant="h1"
              sx={{
                color: 'white', fontWeight: 900, lineHeight: 1.12,
                fontSize: { xs: '2rem', sm: '2.6rem', md: '3.5rem' },
                textWrap: 'balance',
              }}
            >
              Tecnología y soporte en el corazón de Trujillo
            </Typography>
            <Typography
              sx={{
                color: 'rgba(255,255,255,0.85)', mt: { xs: 1.8, md: 2.5 }, maxWidth: 540,
                fontSize: { xs: '0.98rem', md: '1.15rem' }, lineHeight: 1.7,
              }}
            >
              Componentes, periféricos y servicio técnico especializado, con más de
              30 años de experiencia respaldándonos.
            </Typography>

            <Stack
              direction={{ xs: 'column', sm: 'row' }}
              spacing={1.5}
              sx={{ mt: { xs: 3, md: 4 } }}
            >
              <Button
                component={Link}
                href="/catalog"
                variant="contained"
                size="large"
                endIcon={<ArrowForwardIcon />}
                sx={{
                  px: 3.5, py: 1.5, fontWeight: 700, fontSize: '1rem',
                  '&:active': { transform: 'scale(0.98)' },
                }}
              >
                Ver catálogo
              </Button>
              <Button
                component={Link}
                href="/services"
                variant="outlined"
                size="large"
                sx={{
                  px: 3.5, py: 1.5, fontWeight: 700, fontSize: '1rem',
                  color: 'white', borderColor: 'rgba(255,255,255,0.55)',
                  '&:hover': { borderColor: 'white', bgcolor: 'rgba(255,255,255,0.1)' },
                  '&:active': { transform: 'scale(0.98)' },
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
          <Grid container sx={{ py: { xs: 2.5, md: 3.5 } }}>
            {STATS.map((s) => (
              // En móvil los tres van en fila: antes se apilaban y ocupaban
              // media pantalla para decir muy poco.
              <Grid size={4} key={s.label}>
                <Stack
                  direction={{ xs: 'column', sm: 'row' }}
                  spacing={{ xs: 0.6, sm: 1.8 }}
                  sx={{
                    alignItems: 'center',
                    justifyContent: { xs: 'flex-start', sm: 'center' },
                    textAlign: { xs: 'center', sm: 'left' },
                    px: { xs: 0.5, sm: 0 },
                  }}
                >
                  <s.icon sx={{ color: 'primary.main', fontSize: { xs: 24, md: 30 } }} />
                  <Box>
                    <Typography
                      sx={{
                        fontWeight: 900, lineHeight: 1.2,
                        fontSize: { xs: '0.82rem', sm: '1.05rem', md: '1.25rem' },
                      }}
                    >
                      {s.value}
                    </Typography>
                    <Typography
                      variant="caption"
                      color="text.secondary"
                      sx={{ fontSize: { xs: '0.68rem', sm: '0.75rem' }, lineHeight: 1.35 }}
                    >
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
      <Container maxWidth="lg" sx={{ py: { xs: 5, md: 9 } }}>
        <Box sx={{ mb: { xs: 3, md: 5 } }}>
          <SectionHeading eyebrow="CATEGORÍAS" title="Explora por tipo de componente" center />
        </Box>

        {/* En móvil es un carrusel que se desliza con el dedo; en escritorio,
            cinco por fila, así las 10 categorías caben en dos filas exactas. */}
        <Box
          sx={{
            display: 'flex',
            gap: 2,
            flexWrap: { xs: 'nowrap', md: 'wrap' },
            overflowX: { xs: 'auto', md: 'visible' },
            scrollSnapType: { xs: 'x proximity', md: 'none' },
            WebkitOverflowScrolling: 'touch',
            scrollbarWidth: 'none',
            '&::-webkit-scrollbar': { display: 'none' },
            // El carrusel llega hasta los bordes de la pantalla en móvil
            mx: { xs: -2, md: 0 },
            px: { xs: 2, md: 0 },
            pb: { xs: 1, md: 0 },
          }}
        >
          {(loading ? Array.from({ length: 6 }) : categories).map((cat, i) => {
            const common = {
              flex: { xs: '0 0 130px', md: '1 1 calc(20% - 16px)' },
              scrollSnapAlign: 'start' as const,
              height: { xs: 122, md: 138 },
              borderRadius: 3,
              border: '1px solid',
              borderColor: 'divider',
            }

            if (loading || !cat) {
              return <Box key={`cat-skeleton-${i}`} sx={{ ...common, bgcolor: 'action.hover' }} />
            }

            const c = cat as CategoryResponse
            const Icon = CATEGORY_ICONS[c.slug] ?? CategoryIcon
            return (
              <Box
                key={c.id}
                component={Link}
                href={`/catalog?category_id=${c.id}`}
                sx={{
                  ...common,
                  display: 'flex', flexDirection: 'column',
                  alignItems: 'center', justifyContent: 'center',
                  gap: 1, textAlign: 'center', p: 1.5,
                  bgcolor: 'background.paper', textDecoration: 'none',
                  transition: 'all 0.28s cubic-bezier(0.4,0,0.2,1)',
                  // El hover solo se aplica donde existe un puntero de verdad
                  '@media (hover: hover)': {
                    '&:hover': {
                      borderColor: 'primary.main',
                      transform: 'translateY(-6px)',
                      boxShadow: '0 16px 32px -12px rgba(0,0,0,0.16)',
                      '& .cat-icon': { color: 'primary.main', transform: 'scale(1.12)' },
                    },
                  },
                  // Retroalimentación al tocar, que es lo que hay en un móvil
                  '&:active': { transform: 'scale(0.96)', borderColor: 'primary.main' },
                }}
              >
                <Icon
                  className="cat-icon"
                  sx={{
                    fontSize: { xs: 30, md: 36 },
                    color: 'text.secondary',
                    transition: 'all 0.28s',
                  }}
                />
                <Typography
                  variant="subtitle2"
                  sx={{
                    fontWeight: 800, color: 'text.primary', lineHeight: 1.25,
                    fontSize: { xs: '0.78rem', md: '0.875rem' },
                  }}
                >
                  {c.name}
                </Typography>
              </Box>
            )
          })}
        </Box>
      </Container>

      {/* ── PRODUCTOS DESTACADOS ──────────────────────────── */}
      <Box sx={{ bgcolor: 'background.paper', py: { xs: 5, md: 9 } }}>
        <Container maxWidth="lg">
          <Stack
            direction={{ xs: 'column', sm: 'row' }}
            spacing={1.5}
            sx={{
              alignItems: { xs: 'flex-start', sm: 'flex-end' },
              justifyContent: 'space-between',
              mb: { xs: 3, md: 4 },
            }}
          >
            <SectionHeading eyebrow="DESTACADOS" title="Lo más buscado" />
            <Button
              component={Link}
              href="/catalog"
              endIcon={<ArrowForwardIcon />}
              sx={{ fontWeight: 700, ml: { xs: -1, sm: 0 } }}
            >
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
                textAlign: 'center', py: { xs: 5, md: 7 }, px: 2, borderRadius: 3,
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
            <Grid container spacing={{ xs: 1.5, sm: 2.5 }}>
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

      {/* ── SECCIÓN DE CONFIANZA ──────────────────────────── */}
      <FraudSection />

      {/* ── SOBRE NOSOTROS ────────────────────────────────── */}
      <Container maxWidth="lg" sx={{ py: { xs: 5, md: 10 } }}>
        <Grid container spacing={{ xs: 3, md: 7 }} sx={{ alignItems: 'center' }}>
          {/* La foto va primero en móvil: entra por los ojos antes que el texto */}
          <Grid size={{ xs: 12, md: 6 }} sx={{ order: { xs: 1, md: 2 } }}>
            <Box
              sx={{
                borderRadius: { xs: 3, md: 4 },
                overflow: 'hidden',
                aspectRatio: '16/10',
                boxShadow: '0 20px 40px -20px rgba(0,0,0,0.28)',
              }}
            >
              <SafeImage src={COMPANY.aboutImage} alt="Equipo de Grupo STS SAC" objectFit="cover" />
            </Box>
          </Grid>

          <Grid size={{ xs: 12, md: 6 }} sx={{ order: { xs: 2, md: 1 } }}>
            <SectionHeading
              eyebrow="SOBRE NOSOTROS"
              title="Tecnología y soporte que inspiran confianza"
            />
            <Typography color="text.secondary" sx={{ lineHeight: 1.85, mt: 2.5, mb: 2 }}>
              {COMPANY.description}
            </Typography>
            <Stack direction="row" spacing={1} sx={{ alignItems: 'flex-start', mb: 3.5 }}>
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

      {/* ── BENEFICIOS ────────────────────────────────────── */}
      <Box
        sx={{
          bgcolor: 'background.paper',
          py: { xs: 5, md: 8 },
          borderTop: '1px solid',
          borderColor: 'divider',
        }}
      >
        <Container maxWidth="lg">
          <Grid container spacing={{ xs: 2.5, md: 3 }}>
            {BENEFITS.map((b) => (
              <Grid size={{ xs: 12, sm: 4 }} key={b.title}>
                <Stack
                  direction={{ xs: 'row', sm: 'column', md: 'row' }}
                  spacing={2}
                  sx={{ alignItems: { xs: 'center', sm: 'flex-start' } }}
                >
                  <Box
                    sx={{
                      flexShrink: 0, width: 46, height: 46, borderRadius: 2.5,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      bgcolor: 'primary.main', color: 'white',
                    }}
                  >
                    <b.icon />
                  </Box>
                  <Box>
                    <Typography variant="subtitle1" sx={{ fontWeight: 800, lineHeight: 1.3 }}>
                      {b.title}
                    </Typography>
                    <Typography
                      variant="body2"
                      color="text.secondary"
                      sx={{ mt: 0.5, lineHeight: 1.65 }}
                    >
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
          py: { xs: 6, md: 9 },
          background: 'linear-gradient(120deg, #1d4ed8 0%, #2563eb 60%, #3b82f6 100%)',
          color: 'white',
        }}
      >
        <Container maxWidth="md" sx={{ textAlign: 'center' }}>
          <Typography
            variant="h4"
            sx={{ fontWeight: 900, fontSize: { xs: '1.5rem', md: '2.2rem' }, textWrap: 'balance' }}
          >
            ¿Listo para armar tu equipo?
          </Typography>
          <Typography
            sx={{
              mt: 1.5, mb: { xs: 3, md: 4 },
              color: 'rgba(255,255,255,0.88)',
              fontSize: { xs: '0.98rem', md: '1.05rem' },
            }}
          >
            Revisa el catálogo completo o escríbenos y te ayudamos a elegir.
          </Typography>
          <Stack
            direction={{ xs: 'column', sm: 'row' }}
            spacing={1.5}
            sx={{ justifyContent: 'center' }}
          >
            <Button
              component={Link}
              href="/catalog"
              size="large"
              sx={{
                px: 4, py: 1.4, fontWeight: 800, bgcolor: 'white', color: 'primary.dark',
                '&:hover': { bgcolor: 'rgba(255,255,255,0.9)' },
                '&:active': { transform: 'scale(0.98)' },
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
                '&:active': { transform: 'scale(0.98)' },
              }}
            >
              Crear cuenta
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
