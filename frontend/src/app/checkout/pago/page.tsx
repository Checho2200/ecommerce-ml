'use client'

/**
 * Formulario de pago simulado.
 *
 * La tienda no llama a ninguna pasarela: el cobro se resuelve dentro del
 * sistema. Y la pantalla lo dice, arriba del todo y sin letra pequeña, porque
 * una simulación honesta se declara. Lo que el comprador escribe aquí se valida
 * como lo haría una pasarela de verdad —el número con el algoritmo de Luhn, la
 * vigencia de la tarjeta— y el resultado entra en el pedido por el mismo camino
 * que entraría el de un cobro real.
 *
 * Del número de tarjeta solo sobreviven los cuatro últimos dígitos, que son los
 * que guarda la orden. El resto se usa para validar y se descarta.
 */

import { Suspense, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { api, ApiError } from '@/lib/api'
import Header from '@/components/ui/Header'

import {
  Container, Box, Typography, Button, TextField, Card, CardContent,
  Alert, CircularProgress, Divider, Chip,
} from '@mui/material'
import CreditCardIcon from '@mui/icons-material/CreditCard'
import ScienceIcon from '@mui/icons-material/Science'
import LockIcon from '@mui/icons-material/Lock'

/**
 * Tarjetas con desenlace fijo, las mismas que reconoce el backend.
 *
 * Se enseñan en pantalla a propósito, igual que hacen los entornos de prueba de
 * cualquier pasarela: sin ellas no habría forma de demostrar el camino del
 * rechazo —qué le pasa al pedido y al inventario cuando un cobro no prospera—
 * sin depender de la suerte.
 */
const TARJETAS = [
  { numero: '4111 1111 1111 1111', que: 'Se aprueba', color: 'success' as const },
  { numero: '4000 0000 0000 0002', que: 'Fondos insuficientes', color: 'error' as const },
  { numero: '5105 1051 0510 5100', que: 'Tarjeta reportada', color: 'error' as const },
]

function FormularioDePago() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const orderId = searchParams.get('order_id') || ''

  const [numero, setNumero] = useState('')
  const [vencimiento, setVencimiento] = useState('')
  const [cvv, setCvv] = useState('')
  const [titular, setTitular] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState('')

  // Se escribe de cuatro en cuatro, como en cualquier formulario de tarjeta.
  const escribirNumero = (valor: string) => {
    const digitos = valor.replace(/\D/g, '').slice(0, 19)
    setNumero(digitos.replace(/(.{4})/g, '$1 ').trim())
  }

  // MM/AA, poniendo la barra sola.
  const escribirVencimiento = (valor: string) => {
    const digitos = valor.replace(/\D/g, '').slice(0, 4)
    setVencimiento(
      digitos.length > 2 ? `${digitos.slice(0, 2)}/${digitos.slice(2)}` : digitos,
    )
  }

  const pagar = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    const [mes, anio] = vencimiento.split('/')
    if (!mes || !anio) {
      setError('Escribe el vencimiento como MM/AA.')
      return
    }

    setEnviando(true)
    try {
      const resultado = await api.orders.pagarSimulado(orderId, {
        numero: numero.replace(/\s/g, ''),
        mes: Number(mes),
        // Dos dígitos en pantalla, cuatro para el servidor.
        anio: 2000 + Number(anio),
        cvv,
        titular,
      })

      if (resultado.aprobado) {
        router.push(`/checkout/success?order_id=${orderId}`)
        return
      }

      // Un rechazo del emisor deja el pedido cancelado: no tiene sentido
      // dejarle reintentar sobre algo que ya no existe.
      if (resultado.estado_del_pedido === 'cancelada') {
        router.push(`/checkout/failure?order_id=${orderId}`)
        return
      }

      // Lo demás son erratas: el pedido sigue vivo y puede corregir.
      setError(resultado.motivo || 'No pudimos procesar el pago.')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No pudimos procesar el pago.')
    } finally {
      setEnviando(false)
    }
  }

  if (!orderId) {
    return (
      <Container maxWidth="sm">
        <Box sx={{ py: 12, textAlign: 'center' }}>
          <Typography variant="h6" sx={{ fontWeight: 700, mb: 2 }}>
            No sabemos qué pedido pagar
          </Typography>
          <Button component={Link} href="/orders" variant="contained" sx={{ textTransform: 'none', fontWeight: 700 }}>
            Ver mis compras
          </Button>
        </Box>
      </Container>
    )
  }

  return (
    <Container maxWidth="sm">
      <Box sx={{ py: { xs: 4, md: 8 } }}>
        {/* El aviso va arriba y sin letra pequeña: una simulación honesta se
            declara antes de que nadie escriba nada, no después. */}
        <Alert
          icon={<ScienceIcon />}
          severity="info"
          sx={{ mb: 3, borderRadius: 2, alignItems: 'center' }}
        >
          <Typography variant="body2" sx={{ fontWeight: 700 }}>
            Pago simulado — no se realizará ningún cargo
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Esta tienda no cobra con una pasarela real. El pedido quedará
            registrado como pagado con una pasarela simulada.
          </Typography>
        </Alert>

        <Card elevation={0} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 3 }}>
          <CardContent sx={{ p: { xs: 2.5, md: 3.5 } }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 3 }}>
              <CreditCardIcon color="primary" />
              <Typography variant="h6" sx={{ fontWeight: 800 }}>Datos de la tarjeta</Typography>
            </Box>

            {error && <Alert severity="error" sx={{ mb: 3, borderRadius: 2 }}>{error}</Alert>}

            <Box component="form" onSubmit={pagar} sx={{ display: 'flex', flexDirection: 'column', gap: 2.5 }}>
              <TextField
                label="Número de tarjeta"
                required
                fullWidth
                value={numero}
                onChange={(e) => escribirNumero(e.target.value)}
                placeholder="4111 1111 1111 1111"
                slotProps={{ htmlInput: { inputMode: 'numeric' } }}
              />
              <TextField
                label="Nombre del titular"
                required
                fullWidth
                value={titular}
                onChange={(e) => setTitular(e.target.value)}
                placeholder="Como aparece en la tarjeta"
                helperText="El panel compara este nombre con el de la cuenta cuando revisa un pedido."
              />
              <Box sx={{ display: 'flex', gap: 2 }}>
                <TextField
                  label="Vencimiento"
                  required
                  fullWidth
                  value={vencimiento}
                  onChange={(e) => escribirVencimiento(e.target.value)}
                  placeholder="MM/AA"
                  slotProps={{ htmlInput: { inputMode: 'numeric' } }}
                />
                <TextField
                  label="CVV"
                  required
                  fullWidth
                  value={cvv}
                  onChange={(e) => setCvv(e.target.value.replace(/\D/g, '').slice(0, 4))}
                  placeholder="123"
                  slotProps={{ htmlInput: { inputMode: 'numeric' } }}
                />
              </Box>

              <Button
                type="submit"
                variant="contained"
                size="large"
                fullWidth
                disabled={enviando}
                sx={{ textTransform: 'none', fontWeight: 700, borderRadius: 2, py: 1.5, mt: 1 }}
              >
                {enviando ? <CircularProgress size={22} color="inherit" /> : 'Pagar'}
              </Button>

              <Typography
                variant="caption"
                color="text.secondary"
                sx={{ display: 'flex', alignItems: 'center', gap: 0.5, justifyContent: 'center' }}
              >
                <LockIcon sx={{ fontSize: 14 }} />
                De la tarjeta solo se guardan los cuatro últimos dígitos.
              </Typography>
            </Box>

            <Divider sx={{ my: 3 }} />

            <Typography variant="caption" sx={{ fontWeight: 700, display: 'block', mb: 1.5 }}>
              Tarjetas de prueba
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              {TARJETAS.map((t) => (
                <Box
                  key={t.numero}
                  sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 1 }}
                >
                  <Typography
                    variant="body2"
                    sx={{ fontFamily: 'monospace', cursor: 'pointer' }}
                    onClick={() => escribirNumero(t.numero)}
                  >
                    {t.numero}
                  </Typography>
                  <Chip label={t.que} size="small" color={t.color} variant="outlined" sx={{ fontWeight: 600 }} />
                </Box>
              ))}
            </Box>
            <Typography variant="caption" color="text.secondary" sx={{ mt: 1.5, display: 'block' }}>
              Cualquier otro número válido se aprueba. Pulsa uno para copiarlo al
              formulario.
            </Typography>
          </CardContent>
        </Card>

        <Box sx={{ textAlign: 'center', mt: 3 }}>
          <Button component={Link} href="/orders" size="small" sx={{ textTransform: 'none' }}>
            Pagarlo más tarde desde mis compras
          </Button>
        </Box>
      </Box>
    </Container>
  )
}

export default function PagoSimuladoPage() {
  return (
    <Box sx={{ minHeight: '100dvh', bgcolor: 'background.default' }}>
      <Header />
      <Suspense fallback={null}>
        <FormularioDePago />
      </Suspense>
    </Box>
  )
}
