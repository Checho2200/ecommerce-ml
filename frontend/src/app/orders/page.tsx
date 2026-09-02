'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '@/lib/auth'
import { api, OrderResponse, ApiError } from '@/lib/api'
import Header from '@/components/ui/Header'

import {
  Container, Box, Typography, Card, Button, Chip,
  Divider, Dialog, DialogTitle, DialogContent, DialogContentText,
  DialogActions, CircularProgress, Skeleton,
} from '@mui/material'
import ShoppingBagIcon from '@mui/icons-material/ShoppingBag'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import CancelIcon from '@mui/icons-material/Cancel'
import HourglassIcon from '@mui/icons-material/HourglassEmpty'
import WarningIcon from '@mui/icons-material/Warning'
import ArrowForwardIcon from '@mui/icons-material/ArrowForward'

const STATUS_MAP: Record<string, { label: string; color: 'warning' | 'info' | 'success' | 'error' | 'default'; icon: React.ReactElement }> = {
  PENDING:      { label: 'Pendiente',   color: 'warning', icon: <HourglassIcon /> },
  FRAUD_REVIEW: { label: 'En Revisión', color: 'warning', icon: <WarningIcon /> },
  APPROVED:     { label: 'Aprobado',    color: 'info',    icon: <CheckCircleIcon /> },
  COMPLETED:    { label: 'Completado',  color: 'success', icon: <CheckCircleIcon /> },
  REJECTED:     { label: 'Rechazado',   color: 'error',   icon: <CancelIcon /> },
  CANCELLED:    { label: 'Cancelado',   color: 'error',   icon: <CancelIcon /> },
}

export default function MyOrdersPage() {
  const router = useRouter()
  const { isAuthenticated, loading: authLoading } = useAuth()
  const [orders, setOrders] = useState<OrderResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [cancelDialog, setCancelDialog] = useState<string | null>(null)
  const [cancelling, setCancelling] = useState(false)
  const [consultadoEn, setConsultadoEn] = useState(0)

  // El listado se guarda dentro del callback de la promesa, no en el cuerpo del
  // efecto, y junto a él se anota el instante en que llegó: de ahí sale el
  // plazo de cancelación, que no puede calcularse durante el render porque
  // leer el reloj haría que dos renders del mismo estado no coincidieran.
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login?redirect=/orders')
      return
    }
    if (!isAuthenticated) return

    let vigente = true
    api.orders
      .listMyOrders({ per_page: 50 })
      .then((res) => {
        if (!vigente) return
        setOrders(res.items)
        setConsultadoEn(Date.now())
        setLoading(false)
      })
      .catch(() => { if (vigente) setLoading(false) })

    return () => { vigente = false }
  }, [isAuthenticated, authLoading, router])

  const handleCancel = async () => {
    if (!cancelDialog) return
    setCancelling(true)
    try {
      await api.orders.cancel(cancelDialog)
      setOrders((prev) => prev.map((o) => o.id === cancelDialog ? { ...o, status: 'CANCELLED' } : o))
    } catch (err) {
      alert(err instanceof ApiError ? err.message : 'Error al cancelar la orden.')
    } finally {
      setCancelling(false)
      setCancelDialog(null)
    }
  }

  const isCancellable = (order: OrderResponse) => {
    if (order.status !== 'PENDING') return false
    const hoursElapsed = (consultadoEn - new Date(order.created_at).getTime()) / 3600000
    return hoursElapsed <= 1
  }

  if (authLoading || loading) {
    return (
      <Box sx={{ minHeight: '100dvh', bgcolor: 'background.default' }}>
        <Header />
        <Container maxWidth="lg" sx={{ py: 6 }}>
          <Skeleton width={200} height={40} sx={{ mb: 4 }} />
          {[1, 2].map((i) => <Skeleton key={i} variant="rounded" height={200} sx={{ mb: 2 }} />)}
        </Container>
      </Box>
    )
  }

  return (
    <Box sx={{ minHeight: '100dvh', bgcolor: 'background.default' }}>
      <Header />

      <Container maxWidth="lg" sx={{ py: { xs: 4, md: 6 } }}>
        <Typography variant="h4" sx={{ fontWeight: 900, mb: 4 }}>Mis Compras</Typography>

        {orders.length === 0 ? (
          <Card elevation={0} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 3, p: { xs: 6, md: 8 }, textAlign: 'center' }}>
            <ShoppingBagIcon sx={{ fontSize: 64, color: 'text.disabled', mb: 2 }} />
            <Typography variant="h6" sx={{ fontWeight: 700, mb: 1 }}>Aún no tienes compras</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 4, maxWidth: 360, mx: 'auto' }}>
              Tu historial de órdenes está vacío. ¡Explora el catálogo y realiza tu primera compra!
            </Typography>
            <Button component={Link} href="/catalog" variant="contained" sx={{ textTransform: 'none', fontWeight: 700, borderRadius: 2, px: 4 }}>
              Ver Catálogo
            </Button>
          </Card>
        ) : (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            {orders.map((order) => {
              const statusInfo = STATUS_MAP[order.status] || { label: order.status, color: 'default' as const, icon: <></> }
              return (
                <Card key={order.id} elevation={0} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 3, overflow: 'hidden' }}>
                  {/* Header */}
                  <Box sx={{ px: 3, py: 2, bgcolor: 'action.hover', display: 'flex', flexWrap: 'wrap', gap: 2, alignItems: 'center', justifyContent: 'space-between' }}>
                    <Box sx={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                      {[
                        { label: 'Fecha', value: new Date(order.created_at).toLocaleDateString('es-PE', { year: 'numeric', month: 'short', day: 'numeric' }) },
                        { label: 'Total', value: `S/${order.total_amount.toFixed(2)}` },
                        { label: 'Orden', value: `#${order.id.split('-')[0].toUpperCase()}` },
                      ].map((item) => (
                        <Box key={item.label}>
                          <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'uppercase', fontWeight: 700, letterSpacing: 0.5 }}>
                            {item.label}
                          </Typography>
                          <Typography variant="body2" sx={{ fontWeight: 700 }}>{item.value}</Typography>
                        </Box>
                      ))}
                    </Box>
                    <Box sx={{ display: 'flex', gap: 1.5, alignItems: 'center' }}>
                      <Chip
                        icon={statusInfo.icon}
                        label={statusInfo.label}
                        color={statusInfo.color}
                        size="small"
                        variant="outlined"
                        sx={{ fontWeight: 700 }}
                      />
                      {isCancellable(order) && (
                        <Button
                          size="small"
                          color="error"
                          variant="outlined"
                          onClick={() => setCancelDialog(order.id)}
                          sx={{ textTransform: 'none', fontWeight: 700, borderRadius: 2 }}
                        >
                          Cancelar
                        </Button>
                      )}
                    </Box>
                  </Box>

                  {/* Items */}
                  <Box sx={{ px: 3, py: 2 }}>
                    {order.items.map((item, idx) => (
                      <Box key={item.id}>
                        {idx > 0 && <Divider sx={{ my: 1 }} />}
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', py: 1 }}>
                          <Box>
                            <Typography
                              component={Link}
                              href={`/producto/${item.product_id}`}
                              variant="body2"
                              sx={{ fontWeight: 600, textDecoration: 'none', color: 'text.primary', '&:hover': { color: 'primary.main' } }}
                            >
                              {item.product_name || 'Producto eliminado'}
                            </Typography>
                            <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                              Cantidad: {item.quantity}
                            </Typography>
                          </Box>
                          <Typography variant="body2" sx={{ fontWeight: 700 }}>
                            S/{(item.unit_price * item.quantity).toFixed(2)}
                          </Typography>
                        </Box>
                      </Box>
                    ))}
                  </Box>

                  {/* Footer */}
                  {(order.shipping_address || order.status === 'COMPLETED') && (
                    <Box sx={{ px: 3, py: 2, borderTop: '1px solid', borderColor: 'divider', bgcolor: 'action.hover', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 2 }}>
                      {order.shipping_address && (
                        <Typography variant="caption" color="text.secondary">
                          📍 {order.shipping_address}, {order.shipping_city}
                        </Typography>
                      )}
                      {order.status === 'COMPLETED' && order.items[0] && (
                        <Button
                          component={Link}
                          href={`/producto/${order.items[0].product_id}`}
                          size="small"
                          endIcon={<ArrowForwardIcon />}
                          sx={{ textTransform: 'none', fontWeight: 600 }}
                        >
                          Dejar reseña
                        </Button>
                      )}
                    </Box>
                  )}
                </Card>
              )
            })}
          </Box>
        )}
      </Container>

      {/* Cancel Dialog */}
      <Dialog open={!!cancelDialog} onClose={() => !cancelling && setCancelDialog(null)} sx={{ '& .MuiDialog-paper': { borderRadius: 3 } }}>
        <DialogTitle sx={{ fontWeight: 700 }}>Cancelar Orden</DialogTitle>
        <DialogContent>
          <DialogContentText>
            ¿Estás seguro de que deseas cancelar esta orden? Esta acción no se puede deshacer.
          </DialogContentText>
        </DialogContent>
        <DialogActions sx={{ p: 2.5, gap: 1 }}>
          <Button onClick={() => setCancelDialog(null)} disabled={cancelling} sx={{ textTransform: 'none', fontWeight: 600, borderRadius: 2 }}>
            No, mantener
          </Button>
          <Button onClick={handleCancel} disabled={cancelling} color="error" variant="contained" sx={{ textTransform: 'none', fontWeight: 700, borderRadius: 2 }}>
            {cancelling ? <CircularProgress size={18} color="inherit" /> : 'Sí, cancelar'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
