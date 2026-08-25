'use client'

import { useSearchParams } from 'next/navigation'
import Link from 'next/link'
import Header from '@/components/ui/Header'
import { Container, Box, Typography, Button } from '@mui/material'
import ErrorIcon from '@mui/icons-material/Error'
import { Suspense } from 'react'

function FailureContent() {
  const searchParams = useSearchParams()
  const orderId = searchParams.get('order_id') || 'desconocido'

  return (
    <Container maxWidth="sm">
      <Box sx={{ py: 12, textAlign: 'center' }}>
        <Box sx={{ width: 80, height: 80, borderRadius: '50%', bgcolor: 'error.main', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', mx: 'auto', mb: 3 }}>
          <ErrorIcon sx={{ fontSize: 44 }} />
        </Box>
        <Typography variant="h4" sx={{ fontWeight: 900, mb: 1 }}>Pago Fallido o Cancelado</Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 2 }}>
          Lo sentimos, no pudimos procesar tu pago. Tu orden ha quedado pendiente.
        </Typography>
        {orderId !== 'desconocido' && (
          <Box sx={{ display: 'inline-block', bgcolor: 'action.hover', px: 3, py: 1, borderRadius: 2, mb: 4 }}>
            <Typography variant="body2" sx={{ fontWeight: 700 }}>Orden ID: {orderId.split('-')[0]}...</Typography>
          </Box>
        )}
        <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center' }}>
          <Button component={Link} href="/checkout" variant="contained" sx={{ textTransform: 'none', fontWeight: 700, borderRadius: 2 }}>
            Intentar de nuevo
          </Button>
          <Button component={Link} href="/orders" variant="outlined" sx={{ textTransform: 'none', fontWeight: 700, borderRadius: 2 }}>
            Ver mis órdenes
          </Button>
        </Box>
      </Box>
    </Container>
  )
}

export default function CheckoutFailurePage() {
  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
      <Header />
      <Suspense fallback={<Box sx={{ py: 12, textAlign: 'center' }}><Typography>Cargando...</Typography></Box>}>
        <FailureContent />
      </Suspense>
    </Box>
  )
}
