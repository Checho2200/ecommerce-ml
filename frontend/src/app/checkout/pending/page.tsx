'use client'

import { useSearchParams } from 'next/navigation'
import Link from 'next/link'
import Header from '@/components/ui/Header'
import { Container, Box, Typography, Button } from '@mui/material'
import HourglassTopIcon from '@mui/icons-material/HourglassTop'
import { Suspense } from 'react'

function PendingContent() {
  const searchParams = useSearchParams()
  const orderId = searchParams.get('order_id') || 'desconocido'

  return (
    <Container maxWidth="sm">
      <Box sx={{ py: 12, textAlign: 'center' }}>
        <Box sx={{ width: 80, height: 80, borderRadius: '50%', bgcolor: 'warning.main', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', mx: 'auto', mb: 3 }}>
          <HourglassTopIcon sx={{ fontSize: 44 }} />
        </Box>
        <Typography variant="h4" sx={{ fontWeight: 900, mb: 1 }}>Pago en proceso</Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 2 }}>
          Tu pago fue registrado y está siendo revisado. No hace falta que lo vuelvas
          a intentar: en cuanto se confirme, tu orden pasará a completada y podrás
          verla en tus órdenes.
        </Typography>
        {orderId !== 'desconocido' && (
          <Box sx={{ display: 'inline-block', bgcolor: 'action.hover', px: 3, py: 1, borderRadius: 2, mb: 4 }}>
            <Typography variant="body2" sx={{ fontWeight: 700 }}>Orden ID: {orderId.split('-')[0]}...</Typography>
          </Box>
        )}
        <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center' }}>
          <Button component={Link} href="/orders" variant="contained" sx={{ textTransform: 'none', fontWeight: 700, borderRadius: 2 }}>
            Ver mis órdenes
          </Button>
          <Button component={Link} href="/catalog" variant="outlined" sx={{ textTransform: 'none', fontWeight: 700, borderRadius: 2 }}>
            Seguir comprando
          </Button>
        </Box>
      </Box>
    </Container>
  )
}

export default function CheckoutPendingPage() {
  return (
    <Box sx={{ minHeight: '100dvh', bgcolor: 'background.default' }}>
      <Header />
      <Suspense fallback={<Box sx={{ py: 12, textAlign: 'center' }}><Typography>Cargando...</Typography></Box>}>
        <PendingContent />
      </Suspense>
    </Box>
  )
}
