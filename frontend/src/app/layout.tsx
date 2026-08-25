import { Analytics } from '@vercel/analytics/next'
import type { Metadata, Viewport } from 'next'
import './globals.css'
import AppThemeProvider from '@/components/ThemeProvider'
import AuthProvider from '@/lib/auth'

export const metadata: Metadata = {
  title: 'GRUPO STS SAC | Periféricos y Hardware',
  description: 'Compra teclados, mouse, audífonos, monitores y periféricos para tu setup. Soporte especializado y envíos a todo el Perú.',
  keywords: ['periféricos', 'hardware', 'teclados mecánicos', 'mouse gaming', 'audífonos', 'monitores', 'Trujillo'],
  generator: 'v0.app',
  icons: {
    icon: [
      { url: '/icon-light-32x32.png', media: '(prefers-color-scheme: light)' },
      { url: '/icon-dark-32x32.png', media: '(prefers-color-scheme: dark)' },
      { url: '/icon.svg', type: 'image/svg+xml' },
    ],
    apple: '/apple-icon.png',
  },
}

export const viewport: Viewport = {
  colorScheme: 'light dark',
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: 'white' },
    { media: '(prefers-color-scheme: dark)', color: 'black' },
  ],
}

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="es">
      <body className="antialiased">
        <AppThemeProvider>
          <AuthProvider>
            {children}
            {process.env.NODE_ENV === 'production' && <Analytics />}
          </AuthProvider>
        </AppThemeProvider>
      </body>
    </html>
  )
}
