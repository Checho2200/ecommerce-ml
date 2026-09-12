'use client'

import { useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useCartStore } from '@/lib/stores/cart'
import { precioEfectivo } from '@/lib/precio'
import { useAuth } from '@/lib/auth'
import { api, ApiError } from '@/lib/api'
import type { OrderResponse } from '@/lib/api'
import { abrirFormularioDeNiubiz } from '@/lib/niubiz'
import Header from '@/components/ui/Header'

import {
  Container, Box, Typography, Button, TextField, Card, CardContent,
  Alert, CircularProgress, Divider, Select, MenuItem, FormControl,
  InputLabel,
} from '@mui/material'
import LocalShippingIcon from '@mui/icons-material/LocalShipping'
import CreditCardIcon from '@mui/icons-material/CreditCard'
import ShieldIcon from '@mui/icons-material/Shield'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import ArrowForwardIcon from '@mui/icons-material/ArrowForward'
import GppMaybeIcon from '@mui/icons-material/GppMaybe'
import HourglassTopIcon from '@mui/icons-material/HourglassTop'
import OpenInNewIcon from '@mui/icons-material/OpenInNew'

export default function CheckoutPage() {
  const router = useRouter()
  const { items, totalPrice, clearCart } = useCartStore()
  const { isAuthenticated, user } = useAuth()

  const [address, setAddress] = useState('')
  const [city, setCity] = useState('Trujillo')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  const [orderId, setOrderId] = useState('')
  const [orderStatus, setOrderStatus] = useState('')
  // El pedido recien creado, mientras espera que la persona elija con cual de
  // las dos pasarelas paga. El carrito no se vacia todavia: si abandona el
  // pago, sus productos tienen que seguir ahi.
  const [pedido, setPedido] = useState<OrderResponse | null>(null)
  const [pasarela, setPasarela] = useState('')
  // Cuanto tarda la persona en completar el checkout es una de las cuatro
  // variables que mira el modelo de fraude. El instante de entrada se anota en
  // una ref dentro de un efecto: leer el reloj durante el render hace que dos
  // renders del mismo estado den resultados distintos.
  const mountTime = useRef(0)

  useEffect(() => {
    mountTime.current = Date.now()
  }, [])

  // ── Not authenticated ────────────────────────────────────
  if (!isAuthenticated) {
    return (
      <Box sx={{ minHeight: '100dvh', bgcolor: 'background.default' }}>
        <Header />
        <Container maxWidth="sm">
          <Box sx={{ py: 12, textAlign: 'center' }}>
            <ShieldIcon sx={{ fontSize: 64, color: 'text.disabled', mb: 2 }} />
            <Typography variant="h5" sx={{ fontWeight: 800, mb: 1 }}>Inicia sesión para continuar</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 4 }}>
              Necesitas una cuenta para realizar compras en GRUPO STS SAC.
            </Typography>
            <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center' }}>
              <Button component={Link} href="/login?redirect=/checkout" variant="contained" sx={{ textTransform: 'none', fontWeight: 700, borderRadius: 2 }}>
                Iniciar Sesión
              </Button>
              <Button component={Link} href="/register?redirect=/checkout" variant="outlined" sx={{ textTransform: 'none', fontWeight: 700, borderRadius: 2 }}>
                Crear Cuenta
              </Button>
            </Box>
          </Box>
        </Container>
      </Box>
    )
  }

  // ── Cart empty ───────────────────────────────────────────
  if (items.length === 0 && !success) {
    router.push('/cart')
    return null
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!address.trim()) { setError('La dirección de envío es obligatoria.'); return }
    setLoading(true)
    setError('')
    try {
      const order = await api.orders.create({
        items: items.map((i) => ({ product_id: i.product.id, quantity: i.quantity, unit_price: precioEfectivo(i.product) })),
        shipping_address: address,
        shipping_city: city,
        checkout_duration_seconds: (Date.now() - mountTime.current) / 1000,
      })
      // El carrito NO se vacia aqui: si el pago falla o el cliente lo abandona,
      // volveria a la tienda sin sus productos y teniendo que buscarlos otra
      // vez. Se vacia en /checkout/success, cuando la pasarela confirma el cobro.
      if (order.status === 'PENDING' && order.niubiz_disponible) {
        // Hay con que elegir, o solo esta Niubiz: en los dos casos se le
        // ensena el boton en vez de abrir nada solo, porque el formulario de
        // Niubiz necesita que alguien lo pida.
        setPedido(order)
      } else if (order.payment_url) {
        window.location.href = order.payment_url
      } else {
        clearCart()
        setOrderId(order.id)
        setOrderStatus(order.status)
        setSuccess(true)
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Error al procesar tu orden. Inténtalo de nuevo.')
    } finally {
      setLoading(false)
    }
  }

  const pagarConNiubiz = async () => {
    if (!pedido) return
    setPasarela('niubiz')
    setError('')
    try {
      const sesion = await api.orders.niubizSession(pedido.id)
      await abrirFormularioDeNiubiz(sesion, {
        ordenId: pedido.id,
        nombreDelComercio: 'GRUPO STS SAC',
      })
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : 'No pudimos abrir el formulario de pago. Intentalo de nuevo.',
      )
    } finally {
      // Se suelta el boton aunque el modal haya abierto: si la persona lo
      // cierra sin pagar, tiene que poder volver a intentarlo.
      setPasarela('')
    }
  }

  // -- Con que pagar ----------------------------------------
  // El pedido ya existe y ya paso por el modelo de fraude; lo que falta es
  // cobrarlo. Son dos pasarelas distintas: MercadoPago lleva a su propio sitio
  // y avisa despues por webhook, y Niubiz cobra en un formulario que se abre
  // encima de esta pagina.
  if (pedido) {
    return (
      <Box sx={{ minHeight: '100dvh', bgcolor: 'background.default' }}>
        <Header />
        <Container maxWidth="sm">
          <Box sx={{ py: 10 }}>
            <Typography variant="h4" sx={{ fontWeight: 900, mb: 1, textAlign: 'center' }}>
              Como quieres pagar?
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 4, textAlign: 'center' }}>
              Tu pedido por S/{pedido.total_amount.toFixed(2)} esta reservado. No se te
              cobrara nada hasta que completes el pago.
            </Typography>

            {error && <Alert severity="error" sx={{ mb: 3, borderRadius: 2 }}>{error}</Alert>}

            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              {pedido.niubiz_disponible && (
                <Button
                  variant="contained"
                  size="large"
                  fullWidth
                  startIcon={<CreditCardIcon />}
                  disabled={pasarela !== ''}
                  onClick={pagarConNiubiz}
                  sx={{ textTransform: 'none', fontWeight: 700, borderRadius: 2, py: 1.75 }}
                >
                  {pasarela === 'niubiz'
                    ? <CircularProgress size={22} color="inherit" />
                    : 'Pagar con tarjeta (Niubiz)'}
                </Button>
              )}

              {pedido.payment_url && (
                <Button
                  variant="outlined"
                  size="large"
                  fullWidth
                  endIcon={<OpenInNewIcon />}
                  disabled={pasarela !== ''}
                  onClick={() => {
                    setPasarela('mercadopago')
                    window.location.href = pedido.payment_url as string
                  }}
                  sx={{ textTransform: 'none', fontWeight: 700, borderRadius: 2, py: 1.75 }}
                >
                  Pagar con MercadoPago
                </Button>
              )}
            </Box>

            <Typography
              variant="caption"
              color="text.secondary"
              sx={{ mt: 3, display: 'flex', alignItems: 'center', gap: 0.5, justifyContent: 'center' }}
            >
              <ShieldIcon sx={{ fontSize: 14 }} />
              Los datos de tu tarjeta los maneja la pasarela; la tienda nunca los recibe.
            </Typography>

            <Box sx={{ textAlign: 'center', mt: 4 }}>
              <Button component={Link} href="/orders" size="small" sx={{ textTransform: 'none' }}>
                Pagarlo mas tarde desde mis compras
              </Button>
            </Box>
          </Box>
        </Container>
      </Box>
    )
  }

  // ── Desenlace de la orden ────────────────────────────────
  // Solo se llega aqui cuando no hubo enlace de pago, y eso pasa por tres
  // motivos muy distintos. Antes los tres mostraban "compra exitosa", asi que
  // un pedido bloqueado por el detector de fraude felicitaba al cliente.
  if (success) {
    const desenlace = {
      REJECTED: {
        icono: <GppMaybeIcon sx={{ fontSize: 44 }} />,
        color: 'error.main',
        titulo: 'No pudimos procesar tu pedido',
        detalle:
          'Nuestro sistema de seguridad detecto una anomalia en esta compra y la ' +
          'detuvo antes de cobrarte. No se realizo ningun cargo. Si crees que es ' +
          'un error, escribenos y lo revisamos.',
      },
      // Un pedido ya no nace en revision: el modelo solo corta el checkout
      // cuando bloquea, y lo que marca para revisar se retiene despues del
      // cobro. Este desenlace queda para los pedidos que quedaron retenidos
      // con las reglas anteriores y para cualquier caso raro; si desapareciera,
      // esos clientes verian «Pedido registrado» sin explicacion.
      FRAUD_REVIEW: {
        icono: <HourglassTopIcon sx={{ fontSize: 44 }} />,
        color: 'warning.main',
        titulo: 'Tu pedido esta en revision',
        detalle:
          'Un miembro del equipo va a revisar esta compra antes de continuar. ' +
          'Todavia no se te ha cobrado nada; te avisaremos en cuanto este resuelta.',
      },
    }[orderStatus] ?? {
      icono: <CheckCircleIcon sx={{ fontSize: 44 }} />,
      color: 'success.main',
      titulo: 'Pedido registrado',
      detalle:
        'Tu pedido quedo registrado, pero no pudimos iniciar el pago en linea. ' +
        'Puedes reintentarlo desde tus compras en unos minutos.',
    }

    return (
      <Box sx={{ minHeight: '100dvh', bgcolor: 'background.default' }}>
        <Header />
        <Container maxWidth="sm">
          <Box sx={{ py: 12, textAlign: 'center' }}>
            <Box sx={{ width: 80, height: 80, borderRadius: '50%', bgcolor: desenlace.color, color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', mx: 'auto', mb: 3 }}>
              {desenlace.icono}
            </Box>
            <Typography variant="h4" sx={{ fontWeight: 900, mb: 1 }}>{desenlace.titulo}</Typography>
            <Typography variant="body1" color="text.secondary" sx={{ mb: 2 }}>{desenlace.detalle}</Typography>
            <Box sx={{ display: 'inline-block', bgcolor: 'action.hover', px: 3, py: 1, borderRadius: 2, mb: 4 }}>
              <Typography variant="body2" sx={{ fontWeight: 700 }}>Orden ID: {orderId.split('-')[0]}...</Typography>
            </Box>
            <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center' }}>
              <Button component={Link} href="/orders" variant="contained" endIcon={<ArrowForwardIcon />} sx={{ textTransform: 'none', fontWeight: 700, borderRadius: 2 }}>
                Ver mis compras
              </Button>
              <Button component={Link} href="/" variant="outlined" sx={{ textTransform: 'none', fontWeight: 700, borderRadius: 2 }}>
                Volver al inicio
              </Button>
            </Box>
          </Box>
        </Container>
      </Box>
    )
  }

  // ── Checkout form ────────────────────────────────────────
  return (
    <Box sx={{ minHeight: '100dvh', bgcolor: 'background.default' }}>
      <Header />
      <Container maxWidth="lg" sx={{ py: { xs: 4, md: 6 } }}>
        <Typography variant="h4" sx={{ fontWeight: 900, mb: 4 }}>Checkout</Typography>

        <Box className="flex flex-col lg:flex-row gap-6">
          {/* Formulario */}
          <Box sx={{ flex: 1 }}>
            <Card elevation={0} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 3, mb: 3 }}>
              <CardContent sx={{ p: 3 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 3 }}>
                  <LocalShippingIcon color="primary" />
                  <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>Datos de Envío</Typography>
                </Box>

                {error && <Alert severity="error" sx={{ mb: 3, borderRadius: 2 }}>{error}</Alert>}

                <Box component="form" id="checkout-form" onSubmit={handleSubmit} sx={{ display: 'flex', flexDirection: 'column', gap: 2.5 }}>
                  <TextField
                    label="Nombre Completo"
                    value={user?.full_name || ''}
                    disabled
                    fullWidth
                    helperText="Nombre registrado en tu cuenta"
                  />
                  <TextField
                    label="Dirección de Envío"
                    required
                    fullWidth
                    value={address}
                    onChange={(e) => setAddress(e.target.value)}
                    placeholder="Ej. Av. Los Incas 123, Urb. San Andrés"
                  />
                  <Box className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <FormControl fullWidth>
                      <InputLabel>Ciudad</InputLabel>
                      <Select value={city} label="Ciudad" onChange={(e) => setCity(e.target.value)}>
                        {['Trujillo', 'Lima', 'Arequipa', 'Chiclayo', 'Piura'].map((c) => (
                          <MenuItem key={c} value={c}>{c}</MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                    <TextField
                      label="Teléfono"
                      value={user?.phone || ''}
                      disabled
                      fullWidth
                    />
                  </Box>
                </Box>
              </CardContent>
            </Card>

            {/* Pago */}
            <Card elevation={0} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 3 }}>
              <CardContent sx={{ p: 3 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 3 }}>
                  <CreditCardIcon color="primary" />
                  <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>Método de Pago</Typography>
                </Box>
                <Box sx={{ border: '2px solid', borderColor: 'primary.main', borderRadius: 2, p: 2, bgcolor: 'action.selected', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>Tarjeta de Crédito / Débito</Typography>
                  <Box sx={{ display: 'flex', gap: 1 }}>
                    <Box sx={{ width: 32, height: 20, bgcolor: 'primary.main', borderRadius: 0.5 }} />
                    <Box sx={{ width: 32, height: 20, bgcolor: 'error.main', borderRadius: 0.5 }} />
                  </Box>
                </Box>
                <Typography variant="caption" color="text.secondary" sx={{ mt: 1.5, display: 'flex', alignItems: 'center', gap: 0.5 }}>
                  <ShieldIcon sx={{ fontSize: 14 }} />
                  Elegiras entre Niubiz y MercadoPago en el siguiente paso. Pagos
                  protegidos por nuestro sistema antifraude.
                </Typography>
              </CardContent>
            </Card>
          </Box>

          {/* Resumen */}
          <Box sx={{ width: { xs: '100%', lg: 320 }, flexShrink: 0 }}>
            <Card elevation={0} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 3, p: 3, position: 'sticky', top: 96 }}>
              <Typography variant="h6" sx={{ fontWeight: 700, mb: 3 }}>Tu Pedido</Typography>

              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5, mb: 3 }}>
                {items.map((item) => (
                  <Box key={item.product.id} className="flex justify-between" sx={{ gap: 2 }}>
                    <Typography variant="body2" sx={{ fontWeight: 500, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {item.product.name} <Typography component="span" variant="caption" color="text.secondary">×{item.quantity}</Typography>
                    </Typography>
                    <Typography variant="body2" sx={{ fontWeight: 700, whiteSpace: 'nowrap' }}>
                      S/{(precioEfectivo(item.product) * item.quantity).toFixed(2)}
                    </Typography>
                  </Box>
                ))}
              </Box>

              <Divider sx={{ mb: 2 }} />
              <Box className="flex justify-between" sx={{ mb: 1 }}>
                <Typography variant="body2" color="text.secondary">Envío</Typography>
                <Typography variant="body2" sx={{ fontWeight: 600, color: 'success.main' }}>Gratis</Typography>
              </Box>
              <Box className="flex justify-between" sx={{ mb: 3 }}>
                <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>Total</Typography>
                <Typography variant="h6" sx={{ fontWeight: 900, color: 'primary.main' }}>S/{totalPrice.toFixed(2)}</Typography>
              </Box>

              <Button
                type="submit"
                form="checkout-form"
                variant="contained"
                fullWidth
                size="large"
                disabled={loading}
                sx={{ textTransform: 'none', fontWeight: 700, borderRadius: 2, py: 1.5 }}
              >
                {loading ? <CircularProgress size={22} color="inherit" /> : `Pagar S/${totalPrice.toFixed(2)}`}
              </Button>
            </Card>
          </Box>
        </Box>
      </Container>
    </Box>
  )
}
