'use client'

import { useSearchParams } from 'next/navigation'
import Link from 'next/link'
import Header from '@/components/ui/Header'
import { Container, Box, Typography, Button } from '@mui/material'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import ArrowForwardIcon from '@mui/icons-material/ArrowForward'
import { Suspense } from 'react'

function SuccessContent() {
  const searchParams = useSearchParams()
  const orderId = searchParams.get('order_id') || 'desconocido'

  return (
    <Container maxWidth="sm">
      <Box sx={{ py: 12, textAlign: 'center' }}>
        <Box sx={{ width: 80, height: 80, borderRadius: '50%', bgcolor: 'success.main', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', mx: 'auto', mb: 3 }}>
          <CheckCircleIcon sx={{ fontSize: 44 }} />
        </Box>
        <Typography variant="h4" sx={{ fontWeight: 900, mb: 1 }}>¡Pago Exitoso!</Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 2 }}>
          Tu pago ha sido procesado correctamente y tu orden está en preparación.
        </Typography>
        {orderId !== 'desconocido' && (
          <Box sx={{ display: 'inline-block', bgcolor: 'action.hover', px: 3, py: 1, borderRadius: 2, mb: 4 }}>
            <Typography variant="body2" sx={{ fontWeight: 700 }}>Orden ID: {orderId.split('-')[0]}...</Typography>
          </Box>
        )}
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
  )
}

export default function CheckoutSuccessPage() {
  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
      <Header />
      <Suspense fallback={<Box sx={{ py: 12, textAlign: 'center' }}><Typography>Cargando...</Typography></Box>}>
        <SuccessContent />
      </Suspense>
    </Box>
  )
}
