import { Analytics } from '@vercel/analytics/next'
import type { Metadata, Viewport } from 'next'
import './globals.css'
import AppThemeProvider from '@/components/ThemeProvider'
import AuthProvider from '@/lib/auth'
import Footer from '@/components/ui/Footer'
import BackendWarmup from '@/components/system/BackendWarmup'

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
    { media: '(prefers-color-scheme: light)', color: '#f8fafc' },
    { media: '(prefers-color-scheme: dark)', color: '#0f172a' },
  ],
}

// Pinta el color de fondo correcto ANTES del primer render, leyendo la
// preferencia guardada por Zustand. Sin esto, quien tiene modo oscuro ve un
// destello blanco en cada carga.
const themeInitScript = `
(function(){try{
  var raw = localStorage.getItem('sts-theme');
  var mode = raw ? (JSON.parse(raw).state || {}).mode : null;
  if (mode !== 'dark' && mode !== 'light') mode = 'light';
  var bg = mode === 'dark' ? '#0f172a' : '#f8fafc';
  document.documentElement.style.colorScheme = mode;
  document.documentElement.style.backgroundColor = bg;
}catch(e){}})();
`;

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="es" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
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
