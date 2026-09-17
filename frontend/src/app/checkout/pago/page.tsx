'use client'

/**
 * Formulario de pago.
 *
 * La tienda cobra con una pasarela simulada, y la pantalla lo dice arriba del
 * todo y sin letra pequeña, antes de que nadie escriba nada: una simulación
 * honesta se declara. Todo lo demás se comporta como un checkout de verdad,
 * porque un formulario que no valida nada ni dice qué se está pagando no
 * demuestra nada.
 *
 * Lo que hace igual que una pasarela real:
 *
 * - Enseña **qué se paga** antes de pedir la tarjeta, con el importe y el
 *   número de pedido. Ninguna pasarela cobra a ciegas.
 * - Reconoce la marca de la tarjeta según se escribe, por el primer dígito.
 * - Valida el número con el algoritmo de Luhn, la vigencia y el código de
 *   seguridad, y devuelve un **código de respuesta** —"51" fondos
 *   insuficientes, "43" tarjeta reportada— como el que devuelve una pasarela.
 * - Entrega una **referencia de cobro** cuando se aprueba, que es la misma que
 *   queda guardada en el pedido y se ve en el panel.
 *
 * Del número de tarjeta solo sobreviven los cuatro últimos dígitos. El resto se
 * usa para validar y se descarta.
 */

import { Suspense, useCallback, useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { api, ApiError } from '@/lib/api'
import type { OrderResponse } from '@/lib/api'
import Header from '@/components/ui/Header'

import {
  Container, Box, Typography, Button, TextField, Card, CardContent,
  Alert, CircularProgress, Divider, Chip, Skeleton,
} from '@mui/material'
import CreditCardIcon from '@mui/icons-material/CreditCard'
import ScienceIcon from '@mui/icons-material/Science'
import LockIcon from '@mui/icons-material/Lock'

/**
 * Tarjetas con desenlace fijo, las mismas que reconoce el servidor.
 *
 * Se enseñan en pantalla a propósito, igual que hacen los entornos de prueba de
 * cualquier pasarela: sin ellas no habría forma de demostrar el camino del
 * rechazo —qué le pasa al pedido y al inventario cuando un cobro no prospera—
 * sin depender de la suerte.
 */
const TARJETAS = [
  { numero: '4111 1111 1111 1111', que: 'Aprobada', color: 'success' as const },
  { numero: '4000 0000 0000 0002', que: 'Rechazada · 51', color: 'error' as const },
  { numero: '5105 1051 0510 5100', que: 'Rechazada · 43', color: 'error' as const },
]

/** La marca según el primer dígito, como hace cualquier formulario de pago. */
function marcaDe(digitos: string): string | null {
  if (digitos.startsWith('4')) return 'Visa'
  if (digitos.startsWith('5')) return 'Mastercard'
  if (digitos.startsWith('3')) return 'Amex'
  return null
}

function FormularioDePago() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const orderId = searchParams.get('order_id') || ''

  const [orden, setOrden] = useState<OrderResponse | null>(null)
  const [cargando, setCargando] = useState(true)

  const [numero, setNumero] = useState('')
  const [vencimiento, setVencimiento] = useState('')
  const [cvv, setCvv] = useState('')
  const [titular, setTitular] = useState('')
  const [procesando, setProcesando] = useState(false)
  const [error, setError] = useState('')
  const [codigo, setCodigo] = useState('')

  const cargarOrden = useCallback(async () => {
    if (!orderId) { setCargando(false); return }
    try {
      setOrden(await api.orders.get(orderId))
    } catch {
      // Si no se puede leer, el formulario sigue sirviendo: el importe lo pone
      // el servidor al cobrar, no esta pantalla.
    } finally {
      setCargando(false)
    }
  }, [orderId])

  useEffect(() => { cargarOrden() }, [cargarOrden])

  const escribirNumero = (valor: string) => {
    const digitos = valor.replace(/\D/g, '').slice(0, 19)
    setNumero(digitos.replace(/(.{4})/g, '$1 ').trim())
  }

  const escribirVencimiento = (valor: string) => {
    const digitos = valor.replace(/\D/g, '').slice(0, 4)
    setVencimiento(
      digitos.length > 2 ? `${digitos.slice(0, 2)}/${digitos.slice(2)}` : digitos,
    )
  }

  const marca = marcaDe(numero.replace(/\s/g, ''))

  const pagar = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setCodigo('')

    const [mes, anio] = vencimiento.split('/')
    if (!mes || !anio) {
      setError('Escribe el vencimiento como MM/AA.')
      return
    }

    setProcesando(true)
    // Un cobro que se resuelve en cincuenta milisegundos no se parece a ninguno
    // real, y el parpadeo impide leer que algo estaba pasando. Se espera a que
    // pase un tiempo mínimo antes de enseñar el desenlace; el servidor ya
    // contestó, esto solo gobierna la pantalla.
    const empezo = Date.now()
    const esperarLoMinimo = async () => {
      const queda = 1400 - (Date.now() - empezo)
      if (queda > 0) await new Promise((r) => setTimeout(r, queda))
    }

    try {
      const resultado = await api.orders.pagarSimulado(orderId, {
        numero: numero.replace(/\s/g, ''),
        mes: Number(mes),
        anio: 2000 + Number(anio),
        cvv,
        titular,
      })
      await esperarLoMinimo()

      if (resultado.aprobado) {
        const ref = resultado.referencia ? `&ref=${encodeURIComponent(resultado.referencia)}` : ''
        router.push(`/checkout/success?order_id=${orderId}${ref}`)
        return
      }

      // Un rechazo del emisor deja el pedido cancelado: no tiene sentido
      // ofrecer un reintento sobre algo que ya no existe.
      if (resultado.estado_del_pedido === 'cancelada') {
        router.push(`/checkout/failure?order_id=${orderId}`)
        return
      }

      // Lo demás son erratas: el pedido sigue vivo y se puede corregir.
      setError(resultado.motivo || 'No pudimos procesar el pago.')
      setCodigo(resultado.codigo || '')
    } catch (err) {
      await esperarLoMinimo()
      setError(err instanceof ApiError ? err.message : 'No pudimos procesar el pago.')
    } finally {
      setProcesando(false)
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
        <Alert icon={<ScienceIcon />} severity="info" sx={{ mb: 3, borderRadius: 2 }}>
          <Typography variant="body2" sx={{ fontWeight: 700 }}>
            Pago simulado — no se realizará ningún cargo
          </Typography>
          <Typography variant="caption" color="text.secondary">
            El pedido quedará registrado como pagado con una pasarela simulada.
          </Typography>
        </Alert>

        {/* Qué se está pagando. Ninguna pasarela real cobra a ciegas. */}
        <Card elevation={0} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 3, mb: 2 }}>
          <CardContent sx={{ p: 2.5 }}>
            {cargando ? (
              <Skeleton height={28} />
            ) : (
              <>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                  <Typography variant="body2" color="text.secondary">Total a pagar</Typography>
                  <Typography variant="h5" sx={{ fontWeight: 900 }}>
                    S/{(orden?.total_amount ?? 0).toFixed(2)}
                  </Typography>
                </Box>
                <Typography variant="caption" color="text.secondary">
                  Pedido {orderId.split('-')[0]}
                  {orden?.items?.length ? ` · ${orden.items.length} artículo(s)` : ''}
                </Typography>
              </>
            )}
          </CardContent>
        </Card>

        <Card elevation={0} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 3 }}>
          <CardContent sx={{ p: { xs: 2.5, md: 3.5 } }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 3 }}>
              <CreditCardIcon color="primary" />
              <Typography variant="h6" sx={{ fontWeight: 800, flex: 1 }}>Datos de la tarjeta</Typography>
              {marca && <Chip label={marca} size="small" variant="outlined" sx={{ fontWeight: 700 }} />}
            </Box>

            {error && (
              <Alert severity="error" sx={{ mb: 3, borderRadius: 2 }}>
                {error}
                {codigo && (
                  <Typography variant="caption" sx={{ display: 'block', mt: 0.5, fontFamily: 'monospace' }}>
                    Código de respuesta: {codigo}
                  </Typography>
                )}
              </Alert>
            )}

            <Box component="form" onSubmit={pagar} sx={{ display: 'flex', flexDirection: 'column', gap: 2.5 }}>
              <TextField
                label="Número de tarjeta"
                required fullWidth
                value={numero}
                onChange={(e) => escribirNumero(e.target.value)}
                placeholder="4111 1111 1111 1111"
                disabled={procesando}
                slotProps={{ htmlInput: { inputMode: 'numeric' } }}
              />
              <TextField
                label="Nombre del titular"
                required fullWidth
                value={titular}
                onChange={(e) => setTitular(e.target.value)}
                placeholder="Como aparece en la tarjeta"
                disabled={procesando}
                helperText="El panel compara este nombre con el de la cuenta al revisar un pedido."
              />
              <Box sx={{ display: 'flex', gap: 2 }}>
                <TextField
                  label="Vencimiento"
                  required fullWidth
                  value={vencimiento}
                  onChange={(e) => escribirVencimiento(e.target.value)}
                  placeholder="MM/AA"
                  disabled={procesando}
                  slotProps={{ htmlInput: { inputMode: 'numeric' } }}
                />
                <TextField
                  label="CVV"
                  required fullWidth
                  value={cvv}
                  onChange={(e) => setCvv(e.target.value.replace(/\D/g, '').slice(0, 4))}
                  placeholder="123"
                  disabled={procesando}
                  slotProps={{ htmlInput: { inputMode: 'numeric' } }}
                />
              </Box>

              <Button
                type="submit" variant="contained" size="large" fullWidth
                disabled={procesando}
                sx={{ textTransform: 'none', fontWeight: 700, borderRadius: 2, py: 1.5, mt: 1 }}
              >
                {procesando ? (
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                    <CircularProgress size={20} color="inherit" />
                    Procesando pago…
                  </Box>
                ) : (
                  `Pagar S/${(orden?.total_amount ?? 0).toFixed(2)}`
                )}
              </Button>

              <Typography
                variant="caption" color="text.secondary"
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
                <Box key={t.numero} sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 1 }}>
                  <Typography
                    variant="body2"
                    sx={{ fontFamily: 'monospace', cursor: 'pointer' }}
                    onClick={() => !procesando && escribirNumero(t.numero)}
                  >
                    {t.numero}
                  </Typography>
                  <Chip label={t.que} size="small" color={t.color} variant="outlined" sx={{ fontWeight: 600 }} />
                </Box>
              ))}
            </Box>
            <Typography variant="caption" color="text.secondary" sx={{ mt: 1.5, display: 'block' }}>
              Cualquier otro número válido se aprueba. Pulsa uno para copiarlo.
            </Typography>
          </CardContent>
        </Card>

        <Box sx={{ textAlign: 'center', mt: 3 }}>
          <Button component={Link} href="/orders" size="small" disabled={procesando} sx={{ textTransform: 'none' }}>
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
