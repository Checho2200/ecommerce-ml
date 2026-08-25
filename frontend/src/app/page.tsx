'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import Header from '@/components/ui/Header'
import { useCartStore } from '@/lib/stores/cart'
import { api, ProductResponse } from '@/lib/api'

// MUI
import {
  Container,
  Typography,
  Button,
  Box,
  Card,
  CardContent,
  CardActions,
  Chip,
  Skeleton,
  Snackbar,
  Alert,
  Avatar,
  Divider,
} from '@mui/material'
import ShoppingCartOutlinedIcon from '@mui/icons-material/ShoppingCartOutlined'
import LocalShippingOutlinedIcon from '@mui/icons-material/LocalShippingOutlined'
import SupportAgentOutlinedIcon from '@mui/icons-material/SupportAgentOutlined'
import VerifiedOutlinedIcon from '@mui/icons-material/VerifiedOutlined'
import KeyboardIcon from '@mui/icons-material/Keyboard'
import MouseIcon from '@mui/icons-material/Mouse'
import HeadphonesIcon from '@mui/icons-material/Headphones'
import MonitorIcon from '@mui/icons-material/Monitor'
import ArrowForwardIcon from '@mui/icons-material/ArrowForward'
import LocationOnIcon from '@mui/icons-material/LocationOn'
import GroupsIcon from '@mui/icons-material/Groups'
import EmojiEventsIcon from '@mui/icons-material/EmojiEvents'

/* ─────────────────────────────────────────────────────────────
   DATOS DE LA EMPRESA
   Cambia las URLs de imagen por fotos reales de la empresa
   ──────────────────────────────────────────────────────────── */
const COMPANY = {
  heroImage:
    'https://images.unsplash.com/photo-1498049794561-7780e7231661?auto=format&fit=crop&w=1600&q=80',
  aboutImage:
    'https://images.unsplash.com/photo-1551434678-e076c223a692?auto=format&fit=crop&w=800&q=80',
  founded: '2015',
  location: 'Trujillo, La Libertad — Perú',
  description:
    'Somos una empresa trujillana especializada en tecnología, periféricos y servicio técnico. Llevamos más de 10 años asesorando a profesionales, gamers y empresas con los mejores equipos del mercado.',
}

const TEAM = [
  {
    name: 'Equipo de Ventas',
    role: 'Atención al cliente',
    // Reemplaza con foto real del equipo
    image: 'https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?auto=format&fit=crop&w=200&q=80',
  },
  {
    name: 'Taller Técnico',
    role: 'Servicio especializado',
    image: 'https://images.unsplash.com/photo-1537368910025-700350fe46c7?auto=format&fit=crop&w=200&q=80',
  },
  {
    name: 'Gestión',
    role: 'Administración',
    image: 'https://images.unsplash.com/photo-1560250097-0b93528c311a?auto=format&fit=crop&w=200&q=80',
  },
]

/* ─────────────────────────────────────────────────────────────
   CATEGORÍAS
   ──────────────────────────────────────────────────────────── */
const CATEGORIES = [
  { name: 'Teclados', icon: KeyboardIcon, desc: 'Mecánicos y de oficina' },
  { name: 'Mouse', icon: MouseIcon, desc: 'Precisión y ergonomía' },
  { name: 'Audífonos', icon: HeadphonesIcon, desc: 'Audio inmersivo' },
  { name: 'Monitores', icon: MonitorIcon, desc: 'Imagen profesional' },
]

const BENEFITS = [
  { icon: LocalShippingOutlinedIcon, title: 'Envío a todo el Perú', desc: 'Despacho rápido y seguro a nivel nacional.' },
  { icon: SupportAgentOutlinedIcon, title: 'Soporte técnico', desc: 'Te asesoramos para elegir el producto ideal.' },
  { icon: VerifiedOutlinedIcon, title: 'Garantía real', desc: 'Productos originales con respaldo directo.' },
]

/* ─────────────────────────────────────────────────────────────
   PRODUCT CARD
   ──────────────────────────────────────────────────────────── */
function ProductCard({ product, onAdd }: { product: ProductResponse; onAdd: () => void }) {
  return (
    <Card
      elevation={0}
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        border: '1px solid',
        borderColor: 'divider',
        borderRadius: 3,
        overflow: 'hidden',
        transition: 'box-shadow 0.2s, transform 0.2s',
        '&:hover': { boxShadow: '0 8px 30px rgba(0,0,0,0.08)', transform: 'translateY(-2px)' },
      }}
    >
      <Box sx={{ position: 'relative', aspectRatio: '4/3', overflow: 'hidden', bgcolor: 'grey.100' }}>
        {product.image_url ? (
          <img src={product.image_url} alt={product.name} className="w-full h-full object-cover" />
        ) : (
          <Box className="w-full h-full flex items-center justify-center">
            <Typography variant="body2" color="text.secondary">Sin imagen</Typography>
          </Box>
        )}
        {product.discount_price && (
          <Chip
            label="Oferta"
            size="small"
            color="error"
            sx={{ position: 'absolute', top: 10, left: 10, fontWeight: 700, fontSize: '0.7rem' }}
          />
        )}
      </Box>
      <CardContent sx={{ flexGrow: 1, p: 2.5 }}>
        <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'uppercase', letterSpacing: 1, fontWeight: 600 }}>
          {product.category?.name || 'Hardware'}
        </Typography>
        <Typography
          variant="subtitle1"
          sx={{
            fontWeight: 700, mt: 0.5, lineHeight: 1.3,
            display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden',
          }}
        >
          {product.name}
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 1, mt: 1.5 }}>
          <Typography variant="h6" sx={{ fontWeight: 800 }}>
            S/{(product.discount_price ?? product.price).toFixed(2)}
          </Typography>
          {product.discount_price && (
            <Typography variant="body2" color="text.secondary" sx={{ textDecoration: 'line-through' }}>
              S/{product.price.toFixed(2)}
            </Typography>
          )}
        </Box>
      </CardContent>
      <CardActions sx={{ px: 2.5, pb: 2.5, pt: 0 }}>
        <Button
          variant="contained"
          fullWidth
          startIcon={<ShoppingCartOutlinedIcon />}
          onClick={onAdd}
          sx={{ textTransform: 'none', fontWeight: 600, borderRadius: 2, py: 1 }}
        >
          Agregar al carrito
        </Button>
      </CardActions>
    </Card>
  )
}

function ProductSkeleton() {
  return (
    <Card elevation={0} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 3, overflow: 'hidden' }}>
      <Skeleton variant="rectangular" sx={{ aspectRatio: '4/3' }} />
      <CardContent>
        <Skeleton width="40%" height={16} />
        <Skeleton width="80%" height={24} sx={{ mt: 1 }} />
        <Skeleton width="30%" height={28} sx={{ mt: 1.5 }} />
      </CardContent>
      <Box sx={{ px: 2.5, pb: 2.5 }}>
        <Skeleton variant="rounded" height={42} />
      </Box>
    </Card>
  )
}

/* ─────────────────────────────────────────────────────────────
   MAIN PAGE
   ──────────────────────────────────────────────────────────── */
export default function Page() {
  const addToCart = useCartStore((s) => s.addToCart)
  const [products, setProducts] = useState<ProductResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [snackbar, setSnackbar] = useState<string | null>(null)

  useEffect(() => {
    api.products
      .list({ per_page: 8, active_only: true })
      .then((d) => setProducts(d.items))
      .catch(() => setProducts([]))
      .finally(() => setLoading(false))
  }, [])

  const handleAddToCart = (product: ProductResponse) => {
    addToCart(product, 1)
    setSnackbar(`"${product.name}" agregado al carrito`)
  }

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
      <Header />

      {/* ── HERO con imagen de fondo ──────────────────────── */}
      <Box
        sx={{
          position: 'relative',
          overflow: 'hidden',
          minHeight: { xs: 420, md: 520 },
          display: 'flex',
          alignItems: 'center',
        }}
      >
        {/* Imagen de fondo */}
        <Box
          component="img"
          src={COMPANY.heroImage}
          alt="Tienda Grupo STS SAC"
          sx={{
            position: 'absolute',
            inset: 0,
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            objectPosition: 'center',
          }}
        />
        {/* Overlay oscuro */}
        <Box
          sx={{
            position: 'absolute',
            inset: 0,
            background: 'linear-gradient(90deg, rgba(10,20,50,0.82) 0%, rgba(10,20,50,0.45) 60%, rgba(10,20,50,0.1) 100%)',
          }}
        />
        {/* Contenido */}
        <Container maxWidth="lg" sx={{ position: 'relative', py: { xs: 8, md: 10 } }}>
          <Box sx={{ maxWidth: 560 }}>
            <Typography
              variant="overline"
              sx={{ color: '#facc15', fontWeight: 700, letterSpacing: 3, mb: 1, display: 'block' }}
            >
              Trujillo, Perú
            </Typography>
            <Typography
              variant="h2"
              component="h1"
              sx={{
                fontWeight: 900,
                color: 'white',
                fontSize: { xs: '2rem', sm: '2.6rem', md: '3.2rem' },
                lineHeight: 1.15,
                mb: 2,
              }}
            >
              Tecnología para tu espacio de trabajo
            </Typography>
            <Typography
              variant="h6"
              sx={{ color: 'rgba(255,255,255,0.8)', fontWeight: 400, mb: 4, fontSize: { xs: '1rem', md: '1.1rem' } }}
            >
              Periféricos, hardware y servicio técnico especializado. Más de 10 años acompañando a profesionales y gamers en Trujillo.
            </Typography>
            <Box className="flex flex-wrap gap-3">
              <Button
                component={Link}
                href="/catalog"
                variant="contained"
                size="large"
                endIcon={<ArrowForwardIcon />}
                sx={{
                  bgcolor: 'primary.main', color: 'white', fontWeight: 700,
                  px: 4, py: 1.5, borderRadius: 2, textTransform: 'none', fontSize: '1rem',
                  '&:hover': { bgcolor: 'primary.dark' },
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
                  borderColor: 'rgba(255,255,255,0.5)', color: 'white', fontWeight: 600,
                  px: 4, py: 1.5, borderRadius: 2, textTransform: 'none', fontSize: '1rem',
                  '&:hover': { borderColor: 'white', bgcolor: 'rgba(255,255,255,0.08)' },
                }}
              >
                Servicio técnico
              </Button>
            </Box>
          </Box>
        </Container>
      </Box>

      {/* ── ESTADÍSTICAS ─────────────────────────────────── */}
      <Box sx={{ bgcolor: 'primary.main', py: 3 }}>
        <Container maxWidth="lg">
          <Box className="grid grid-cols-3 gap-6 text-center">
            {[
              { icon: EmojiEventsIcon, value: '+10 años', label: 'de experiencia' },
              { icon: GroupsIcon, value: '+500', label: 'clientes satisfechos' },
              { icon: LocationOnIcon, value: 'Trujillo', label: 'y todo el Perú' },
            ].map((stat) => (
              <Box key={stat.label} sx={{ color: 'white' }}>
                <stat.icon sx={{ fontSize: 28, opacity: 0.8, mb: 0.5 }} />
                <Typography variant="h6" sx={{ fontWeight: 900, lineHeight: 1 }}>{stat.value}</Typography>
                <Typography variant="caption" sx={{ opacity: 0.75 }}>{stat.label}</Typography>
              </Box>
            ))}
          </Box>
        </Container>
      </Box>

      {/* ── CATEGORÍAS ────────────────────────────────────── */}
      <Container maxWidth="lg" sx={{ py: { xs: 6, md: 8 } }}>
        <Typography variant="h5" sx={{ fontWeight: 800, mb: 4, textAlign: 'center' }}>
          Categorías
        </Typography>
        <Box className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {CATEGORIES.map((cat) => (
            <Card
              key={cat.name}
              component={Link}
              href={`/catalog?category=${cat.name}`}
              elevation={0}
              sx={{
                textDecoration: 'none',
                border: '1px solid',
                borderColor: 'divider',
                borderRadius: 3,
                p: 3,
                textAlign: 'center',
                transition: 'all 0.2s',
                '&:hover': { borderColor: 'primary.main', bgcolor: 'action.hover' },
              }}
            >
              <cat.icon sx={{ fontSize: 40, color: 'primary.main', mb: 1.5 }} />
              <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>{cat.name}</Typography>
              <Typography variant="body2" color="text.secondary">{cat.desc}</Typography>
            </Card>
          ))}
        </Box>
      </Container>

      {/* ── PRODUCTOS DESTACADOS ──────────────────────────── */}
      <Box sx={{ bgcolor: 'action.hover', py: { xs: 6, md: 8 } }}>
        <Container maxWidth="lg">
          <Box className="flex justify-between items-end mb-6">
            <Box>
              <Typography variant="h5" sx={{ fontWeight: 800 }}>Productos destacados</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>Lo mejor de nuestra tienda</Typography>
            </Box>
            <Button component={Link} href="/catalog" endIcon={<ArrowForwardIcon />} sx={{ textTransform: 'none', fontWeight: 600 }}>
              Ver todos
            </Button>
          </Box>
          <Box className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {loading
              ? Array.from({ length: 4 }).map((_, i) => <ProductSkeleton key={i} />)
              : products.slice(0, 8).map((p) => (
                  <ProductCard key={p.id} product={p} onAdd={() => handleAddToCart(p)} />
                ))}
          </Box>
          {!loading && products.length === 0 && (
            <Box sx={{ textAlign: 'center', py: 8 }}>
              <Typography variant="h6" color="text.secondary">No hay productos disponibles en este momento.</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>Vuelve pronto, estamos actualizando nuestro catálogo.</Typography>
            </Box>
          )}
        </Container>
      </Box>

      {/* ── SOBRE NOSOTROS ────────────────────────────────── */}
      <Container maxWidth="lg" sx={{ py: { xs: 6, md: 10 } }}>
        <Box className="grid grid-cols-1 md:grid-cols-2 gap-10 items-center">
          {/* Texto */}
          <Box>
            <Typography variant="overline" color="primary" sx={{ fontWeight: 700, letterSpacing: 2 }}>
              Quiénes somos
            </Typography>
            <Typography variant="h4" sx={{ fontWeight: 900, mt: 1, mb: 3, lineHeight: 1.2 }}>
              Más de una década conectando a Trujillo con la tecnología
            </Typography>
            <Typography variant="body1" color="text.secondary" sx={{ lineHeight: 1.8, mb: 3 }}>
              {COMPANY.description}
            </Typography>
            <Box className="flex items-center gap-2" sx={{ mb: 1 }}>
              <LocationOnIcon color="primary" fontSize="small" />
              <Typography variant="body2" sx={{ fontWeight: 600 }}>{COMPANY.location}</Typography>
            </Box>
            <Button
              component={Link}
              href="/services"
              variant="outlined"
              sx={{ mt: 3, textTransform: 'none', fontWeight: 700, borderRadius: 2 }}
            >
              Conoce nuestro servicio técnico
            </Button>
          </Box>
          {/* Foto */}
          <Box
            sx={{
              borderRadius: 4,
              overflow: 'hidden',
              aspectRatio: '4/3',
              border: '1px solid',
              borderColor: 'divider',
            }}
          >
            <Box
              component="img"
              src={COMPANY.aboutImage}
              alt="Equipo Grupo STS SAC"
              sx={{ width: '100%', height: '100%', objectFit: 'cover' }}
            />
          </Box>
        </Box>
      </Container>

      {/* ── NUESTRO EQUIPO ────────────────────────────────── */}
      <Box sx={{ bgcolor: 'action.hover', py: { xs: 6, md: 8 } }}>
        <Container maxWidth="lg">
          <Typography variant="h5" sx={{ fontWeight: 800, mb: 1, textAlign: 'center' }}>Nuestro equipo</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', mb: 5 }}>
            Personas reales comprometidas con tu satisfacción
          </Typography>
          <Box className="grid grid-cols-1 sm:grid-cols-3 gap-6">
            {TEAM.map((member) => (
              <Box
                key={member.name}
                sx={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  textAlign: 'center',
                  p: 4,
                  borderRadius: 3,
                  border: '1px solid',
                  borderColor: 'divider',
                  bgcolor: 'background.paper',
                }}
              >
                <Avatar
                  src={member.image}
                  alt={member.name}
                  sx={{ width: 88, height: 88, mb: 2, border: '3px solid', borderColor: 'primary.main' }}
                />
                <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>{member.name}</Typography>
                <Typography variant="body2" color="text.secondary">{member.role}</Typography>
              </Box>
            ))}
          </Box>
        </Container>
      </Box>

      {/* ── BENEFICIOS ────────────────────────────────────── */}
      <Container maxWidth="lg" sx={{ py: { xs: 6, md: 8 } }}>
        <Typography variant="h5" sx={{ fontWeight: 800, mb: 4, textAlign: 'center' }}>¿Por qué elegirnos?</Typography>
        <Box className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {BENEFITS.map((b) => (
            <Box
              key={b.title}
              sx={{
                display: 'flex', flexDirection: 'column', alignItems: 'center',
                textAlign: 'center', p: 4, borderRadius: 3, border: '1px solid', borderColor: 'divider',
              }}
            >
              <Box
                sx={{
                  width: 56, height: 56, borderRadius: 2, bgcolor: 'primary.main',
                  color: 'primary.contrastText', display: 'flex', alignItems: 'center',
                  justifyContent: 'center', mb: 2,
                }}
              >
                <b.icon fontSize="medium" />
              </Box>
              <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>{b.title}</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>{b.desc}</Typography>
            </Box>
          ))}
        </Box>
      </Container>

      {/* ── FOOTER ────────────────────────────────────────── */}
      <Box component="footer" sx={{ borderTop: '1px solid', borderColor: 'divider', py: 4 }}>
        <Container maxWidth="lg">
          <Box className="flex flex-col md:flex-row items-center justify-between gap-4">
            <Box>
              <Typography variant="subtitle1" sx={{ fontWeight: 800 }}>GRUPO STS SAC</Typography>
              <Typography variant="caption" color="text.secondary">{COMPANY.location}</Typography>
            </Box>
            <Box className="flex gap-4">
              <Button component={Link} href="/catalog" size="small" color="inherit" sx={{ textTransform: 'none' }}>Catálogo</Button>
              <Button component={Link} href="/services" size="small" color="inherit" sx={{ textTransform: 'none' }}>Servicio Técnico</Button>
              <Button component={Link} href="/register" size="small" color="inherit" sx={{ textTransform: 'none' }}>Crear Cuenta</Button>
            </Box>
            <Typography variant="body2" color="text.secondary">© 2026 Grupo STS SAC</Typography>
          </Box>
        </Container>
      </Box>

      {/* ── SNACKBAR ─────────────────────────────────────── */}
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
