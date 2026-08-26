import { Analytics } from '@vercel/analytics/next'
import { Archivo_Black, Barlow } from 'next/font/google'
import type { Metadata, Viewport } from 'next'
import './globals.css'
import AppThemeProvider from '@/components/ThemeProvider'
import AuthProvider from '@/lib/auth'
import Footer from '@/components/ui/Footer'
import BackendWarmup from '@/components/system/BackendWarmup'

// Se cargan con next/font en vez de un @import en el CSS: aquel bloqueaba el
// primer render mientras Google respondía.
const display = Archivo_Black({
  subsets: ['latin'],
  weight: '400',
  variable: '--font-display',
  display: 'swap',
})

const body = Barlow({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700', '800'],
  variable: '--font-body',
  display: 'swap',
})

export const metadata: Metadata = {
  title: 'GRUPO STS SAC | Componentes y Periféricos de Cómputo',
  description:
    'Procesadores, tarjetas de video, memorias, monitores y periféricos con garantía. Servicio técnico especializado y envíos a todo el Perú desde Trujillo.',
  keywords: [
    'componentes de computadora', 'tarjetas de video', 'procesadores',
    'memorias RAM', 'periféricos', 'teclados mecánicos', 'monitores', 'Trujillo',
  ],
  icons: {
    icon: [
      { url: '/icon-32.png', sizes: '32x32', type: 'image/png' },
      { url: '/icon-192.png', sizes: '192x192', type: 'image/png' },
    ],
    apple: '/icon-180.png',
  },
}

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  // Necesario para que env(safe-area-inset-*) funcione en iPhone con notch
  viewportFit: 'cover',
  colorScheme: 'light dark',
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#F2F4F7' },
    { media: '(prefers-color-scheme: dark)', color: '#0B1520' },
  ],
}

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="es" suppressHydrationWarning className={`${display.variable} ${body.variable}`}>
      <head>
        {/* Debe ejecutarse antes de pintar el body: ver public/theme-init.js */}
        <script src="/theme-init.js" />
      </head>
      <body className="antialiased">
        <AppThemeProvider>
          <AuthProvider>
            <div style={{ minHeight: '100dvh', display: 'flex', flexDirection: 'column' }}>
              <div style={{ flex: 1 }}>{children}</div>
              <Footer />
            </div>
            <BackendWarmup />
            {process.env.NODE_ENV === 'production' && <Analytics />}
          </AuthProvider>
        </AppThemeProvider>
      </body>
    </html>
  )
}
