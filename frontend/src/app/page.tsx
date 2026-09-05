'use client'

/**
 * Portada de la tienda.
 *
 * Ordena la página y trae los datos; el aspecto de cada bloque vive en
 * `components/home`. La secuencia es la de una tienda que se explica sola:
 * qué vendemos (portada), dónde buscarlo (categorías), qué hay ahora
 * (novedades), por qué comprar aquí (confianza) y quiénes somos (empresa y
 * contacto). Cada idea aparece una sola vez y con una sola llamada a la acción.
 */

import { useEffect, useState } from 'react'
import { Alert, Box, Snackbar } from '@mui/material'

import Header from '@/components/ui/Header'
import WhatsAppFab from '@/components/ui/WhatsAppFab'
import Hero from '@/components/home/Hero'
import CategoryGrid from '@/components/home/CategoryGrid'
import FeaturedProducts from '@/components/home/FeaturedProducts'
import FraudSection from '@/components/home/FraudSection'
import AboutSection from '@/components/home/AboutSection'
import { api, ProductResponse, CategoryResponse } from '@/lib/api'

/* Una sola fuente de verdad: alimenta la petición, los esqueletos y el render. */
const NOVEDADES = 8

export default function HomePage() {
  const [products, setProducts] = useState<ProductResponse[]>([])
  const [categories, setCategories] = useState<CategoryResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [failed, setFailed] = useState(false)
  const [slow, setSlow] = useState(false)
  const [snackbar, setSnackbar] = useState<string | null>(null)
  const [reloadKey, setReloadKey] = useState(0)

  // Reintento manual: nace de un clic, así que puede tocar el estado sin
  // encadenar renders, y deja los tres indicadores como al montar.
  const reintentarCarga = () => {
    setLoading(true)
    setFailed(false)
    setSlow(false)
    setReloadKey((k) => k + 1)
  }

  // Los tres estados arrancan ya en el valor que necesita una carga en curso,
  // y el botón de reintentar los devuelve a ese punto antes de subir reloadKey.
  // Ponerlos aquí dentro obligaría a un render encadenado en cada montaje.
  useEffect(() => {
    let cancelled = false

    // Render duerme el backend tras ~15 min sin tráfico; si tarda, lo avisamos
    // en vez de dejar los esqueletos girando sin explicación.
    const slowTimer = setTimeout(() => !cancelled && setSlow(true), 3000)

    Promise.all([
      // El orden va explícito: el título de la sección promete novedades.
      api.products.list({ per_page: NOVEDADES, active_only: true, sort: 'recientes' }),
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

      <Box component="main">
        <Hero />
        <CategoryGrid categories={categories} loading={loading} />
        <FeaturedProducts
          products={products}
          loading={loading}
          failed={failed}
          slow={slow}
          cantidad={NOVEDADES}
          onReintentar={reintentarCarga}
          onAgregado={(p) => setSnackbar(`${p.name} agregado al carrito`)}
        />
        <FraudSection />
        <AboutSection />
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
