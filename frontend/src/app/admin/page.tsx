"use client";

/**
 * Dashboard: el estado general de la tienda, y nada más.
 *
 * Antes esta pantalla era dos cosas a la vez. Debajo de cuatro contadores venía
 * el informe completo del modelo de fraude —precisión, exhaustividad, matriz de
 * confusión, impacto en dinero—, que ocupaba más espacio que la tienda entera y
 * que es el detalle de un subsistema, no un resumen del negocio. Todo eso vive
 * ahora en Antifraude; aquí queda un enlace y el número que sí es general: si
 * hay pedidos esperando decisión.
 */

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, type FraudHistoryResponse, type OrderSummaryResponse } from "@/lib/api";
import TarjetasDeIndicadores from "@/components/admin/TarjetasDeIndicadores";
import { useAuth } from "@/lib/auth";
import { ESTADOS_DE_PEDIDO, type EstadoDePedido } from "@/lib/estados";

import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Grid,
  Skeleton,
  Stack,
  Typography,
  alpha,
} from "@mui/material";
import { keyframes } from "@mui/system";

import InventoryIcon from "@mui/icons-material/Inventory";
import LabelIcon from "@mui/icons-material/Label";
import ShoppingCartIcon from "@mui/icons-material/ShoppingCart";
import BuildIcon from "@mui/icons-material/Build";
import PaidOutlinedIcon from "@mui/icons-material/PaidOutlined";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import RefreshIcon from "@mui/icons-material/Refresh";

const aparecer = keyframes`
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
`;

const soles = (monto: number) =>
  `S/ ${monto.toLocaleString("es-PE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

interface Cifras {
  productos: number;
  categorias: number;
  ordenes: number;
  servicios: number;
}

export default function AdminDashboard() {
  const { user, isAdmin } = useAuth();
  const [cifras, setCifras] = useState<Cifras>({
    productos: 0,
    categorias: 0,
    ordenes: 0,
    servicios: 0,
  });
  const [resumen, setResumen] = useState<OrderSummaryResponse | null>(null);
  const [salud, setSalud] = useState<{ status: string } | null>(null);
  // Los tres indicadores de la tesis, en su versión reducida. El detalle vive
  // en Antifraude; aquí solo se enseñan las cifras y un enlace, para que el
  // Dashboard siga siendo un resumen y no el informe del modelo otra vez.
  const [indicadores, setIndicadores] = useState<FraudHistoryResponse | null>(null);
  const [cargando, setCargando] = useState(true);
  // Si alguna de las consultas se cayó. Importa decirlo: un panel lleno de
  // ceros y uno que no pudo preguntar se ven exactamente igual, y el segundo
  // hace pensar que la tienda está vacía.
  const [incompleto, setIncompleto] = useState(false);
  // Cambiarlo vuelve a lanzar el efecto: es lo que usa el botón de reintentar.
  const [intento, setIntento] = useState(0);

  useEffect(() => {
    let vigente = true;

    const cargar = async () => {
      let fallo = false;

      /**
       * Pide un dato sin que su caída arrastre al resto de la pantalla.
       *
       * Antes las dos primeras consultas iban en un `Promise.all` sin
       * proteger, así que cualquiera de las dos que fallara tiraba la función
       * entera: las cuatro tarjetas se quedaban en cero, los indicadores
       * vacíos y sin ningún aviso. Y falla más de lo que parece — el plan
       * gratuito de Render suspende el servicio tras un rato sin visitas, y la
       * primera petición después de eso tarda entre 30 y 50 segundos.
       */
      const pedir = async <T,>(traer: () => Promise<T>): Promise<T | null> => {
        try {
          return await traer();
        } catch {
          fallo = true;
          return null;
        }
      };

      const [productos, categorias] = await Promise.all([
        pedir(() => api.products.list({ per_page: 1, active_only: false })),
        pedir(() => api.categories.list()),
      ]);

      let ordenes = 0;
      let servicios = 0;

      if (isAdmin) {
        // Una sola consulta agrupada trae el total y el desglose por estado;
        // antes hacía falta una petición paginada por cada uno.
        const datos = await pedir(() => api.orders.summary());
        if (datos && vigente) {
          setResumen(datos);
          ordenes = datos.total;
        }

        const listaDeServicios = await pedir(() => api.serviceOrders.list({ page: 1 }));
        if (listaDeServicios) servicios = listaDeServicios.total;

        // Sobre los últimos doce meses: en el Dashboard interesa la foto del
        // año, no la del día.
        const historial = await pedir(() =>
          api.fraud.history({ granularity: "month", periods: 12 })
        );
        if (historial && vigente) setIndicadores(historial);
      }

      // La salud se pide aparte y su fallo no cuenta como panel incompleto:
      // que la API no responda ya se enseña en el chip de la cabecera.
      try {
        const estado = await api.system.health();
        if (vigente) setSalud(estado);
      } catch {
        if (vigente) setSalud(null);
      }

      if (vigente) {
        setCifras({
          productos: productos?.total ?? 0,
          categorias: categorias?.length ?? 0,
          ordenes,
          servicios,
        });
        setIncompleto(fallo);
        setCargando(false);
      }
    };

    cargar();
    return () => {
      vigente = false;
    };
  }, [isAdmin, intento]);

  const TARJETAS = [
    { valor: cifras.productos, etiqueta: "Productos", icono: <InventoryIcon />, color: "#6366f1", href: "/admin/products" },
    { valor: cifras.categorias, etiqueta: "Categorías", icono: <LabelIcon />, color: "#06b6d4", href: "/admin/categories" },
    { valor: cifras.ordenes, etiqueta: "Órdenes", icono: <ShoppingCartIcon />, color: "#10b981", href: "/admin/orders" },
    { valor: cifras.servicios, etiqueta: "Servicios", icono: <BuildIcon />, color: "#f59e0b", href: "/admin/services" },
  ];

  const porEstado = Object.entries(resumen?.by_status ?? {}).sort((a, b) => b[1] - a[1]);
  const enRevision = resumen?.awaiting_review ?? 0;

  return (
    <>
      <Box sx={{ mb: 4 }}>
        <Stack
          direction="row"
          spacing={2}
          sx={{ justifyContent: "space-between", alignItems: "center" }}
        >
          <Box>
            <Typography variant="h5" sx={{ fontWeight: 800 }}>
              Dashboard
            </Typography>
            <Typography variant="body2" sx={{ color: "text.secondary", mt: 0.5 }}>
              Bienvenido, {user?.full_name}
            </Typography>
          </Box>
          {/* El estado sale de /health, no de una etiqueta fija: antes decía
              "Sistema Activo" incluso con la API caída. */}
          <Chip
            label={cargando ? "Comprobando…" : salud ? "Sistema activo" : "Sin conexión con la API"}
            variant="outlined"
            color={cargando ? "default" : salud ? "success" : "error"}
            sx={{ fontWeight: 700 }}
          />
        </Stack>
      </Box>

      {/* Un panel a medio cargar tiene que decirlo. Antes se quedaba en ceros
          y era indistinguible de una tienda sin nada vendido. */}
      {incompleto && !cargando && (
        <Alert
          severity="warning"
          sx={{ mb: 3, borderRadius: 2 }}
          action={
            <Button
              size="small"
              color="inherit"
              startIcon={<RefreshIcon />}
              onClick={() => {
                setCargando(true);
                setIntento((n) => n + 1);
              }}
              sx={{ fontWeight: 700, textTransform: "none" }}
            >
              Reintentar
            </Button>
          }
        >
          Algunas cifras no se pudieron cargar y se muestran en cero. Si el servidor
          estaba en reposo, la primera petición puede tardar hasta un minuto.
        </Alert>
      )}

      {enRevision > 0 && (
        <Alert
          severity="warning"
          sx={{ mb: 3, borderRadius: 2 }}
          action={
            <Button
              component={Link}
              href="/admin/fraud"
              size="small"
              color="inherit"
              endIcon={<ArrowForwardIcon />}
              sx={{ fontWeight: 700, textTransform: "none" }}
            >
              Revisar
            </Button>
          }
        >
          {enRevision === 1
            ? "Hay 1 pedido retenido esperando decisión."
            : `Hay ${enRevision} pedidos retenidos esperando decisión.`}{" "}
          Mientras tanto el cliente no puede pagar y su stock sigue apartado.
        </Alert>
      )}

      <Grid container spacing={3} sx={{ mb: 3 }}>
        {TARJETAS.map((tarjeta, i) => (
          <Grid size={{ xs: 6, md: 3 }} key={tarjeta.etiqueta}>
            <Card
              component={Link}
              href={tarjeta.href}
              elevation={0}
              sx={{
                display: "block",
                textDecoration: "none",
                borderRadius: 3,
                border: "1px solid",
                borderColor: "divider",
                animation: `${aparecer} 0.5s ease-out ${i * 0.08}s both`,
                transition: "all 0.2s",
                "&:hover": {
                  transform: "translateY(-4px)",
                  boxShadow: `0 12px 24px -8px ${alpha(tarjeta.color, 0.2)}`,
                  borderColor: tarjeta.color,
                },
              }}
            >
              <CardContent sx={{ p: 3 }}>
                <Stack
                  direction="row"
                  sx={{ justifyContent: "space-between", alignItems: "center", mb: 2 }}
                >
                  <Typography
                    variant="body2"
                    sx={{
                      color: "text.secondary",
                      fontWeight: 600,
                      textTransform: "uppercase",
                      fontSize: "0.72rem",
                      letterSpacing: 0.5,
                    }}
                  >
                    {tarjeta.etiqueta}
                  </Typography>
                  <Box
                    sx={{
                      width: 40,
                      height: 40,
                      borderRadius: 2,
                      bgcolor: alpha(tarjeta.color, 0.1),
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      color: tarjeta.color,
                    }}
                  >
                    {tarjeta.icono}
                  </Box>
                </Stack>
                {cargando ? (
                  <Skeleton width={60} height={40} />
                ) : (
                  <Typography variant="h4" sx={{ fontWeight: 900, lineHeight: 1, color: "text.primary" }}>
                    {tarjeta.valor}
                  </Typography>
                )}
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* ── Indicadores del antifraude ──────────────────────────────── */}
      <Card
        elevation={0}
        sx={{ borderRadius: 3, border: "1px solid", borderColor: "divider", mb: 3 }}
      >
        <CardContent sx={{ p: 3 }}>
          <Stack
            direction={{ xs: "column", md: "row" }}
            spacing={2}
            sx={{ justifyContent: "space-between", alignItems: { md: "center" }, mb: 2.5 }}
          >
            <Box>
              <Typography variant="subtitle1" sx={{ fontWeight: 800 }}>
                Indicadores del antifraude
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Últimos 12 meses. El detalle y el reporte descargable están en Antifraude.
              </Typography>
            </Box>
            <Button
              component={Link}
              href="/admin/fraud/modelo"
              size="small"
              endIcon={<ArrowForwardIcon />}
              sx={{ textTransform: "none", fontWeight: 700, whiteSpace: "nowrap" }}
            >
              Ver el detalle
            </Button>
          </Stack>
          <TarjetasDeIndicadores datos={indicadores} cargando={cargando} compacto />
        </CardContent>
      </Card>

      <Grid container spacing={3}>
        {/* Los pedidos por estado: es el reparto que resume el día de la
            tienda, y el que decide qué hay que atender. */}
        <Grid size={{ xs: 12, md: 7 }}>
          <Card elevation={0} sx={{ borderRadius: 3, border: "1px solid", borderColor: "divider", height: "100%" }}>
            <CardContent sx={{ p: 3 }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 800, mb: 0.5 }}>
                Órdenes por estado
              </Typography>
              <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 2 }}>
                Sobre las {resumen?.total ?? 0} órdenes registradas.
              </Typography>

              {cargando ? (
                <Stack spacing={1.2}>
                  {[0, 1, 2].map((i) => (
                    <Skeleton key={i} height={26} />
                  ))}
                </Stack>
              ) : porEstado.length === 0 ? (
                <Typography variant="body2" color="text.secondary" sx={{ py: 3, textAlign: "center" }}>
                  Todavía no hay órdenes.
                </Typography>
              ) : (
                porEstado.map(([estado, cuantas]) => {
                  const info = ESTADOS_DE_PEDIDO[estado as EstadoDePedido];
                  const proporcion = resumen?.total ? (cuantas / resumen.total) * 100 : 0;
                  return (
                    <Box key={estado} sx={{ py: 0.9 }}>
                      <Stack direction="row" sx={{ justifyContent: "space-between", mb: 0.6 }}>
                        <Typography variant="body2" color="text.secondary">
                          {info?.label ?? estado}
                        </Typography>
                        <Typography variant="body2" sx={{ fontWeight: 800 }}>
                          {cuantas}
                        </Typography>
                      </Stack>
                      {/* La barra es la misma cifra, en proporción: da el peso
                          relativo sin obligar a hacer la división mentalmente. */}
                      <Box sx={{ height: 6, bgcolor: "action.hover", borderRadius: 3, overflow: "hidden" }}>
                        <Box
                          sx={{
                            width: `${proporcion}%`,
                            height: "100%",
                            bgcolor: "acento.main",
                            borderRadius: 3,
                          }}
                        />
                      </Box>
                    </Box>
                  );
                })
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, md: 5 }}>
          <Card elevation={0} sx={{ borderRadius: 3, border: "1px solid", borderColor: "divider", height: "100%" }}>
            <CardContent sx={{ p: 3 }}>
              <Stack direction="row" spacing={1.5} sx={{ alignItems: "center", mb: 2 }}>
                <Box
                  sx={{
                    width: 44,
                    height: 44,
                    borderRadius: 2.5,
                    bgcolor: alpha("#10b981", 0.1),
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "success.main",
                  }}
                >
                  <PaidOutlinedIcon />
                </Box>
                <Box>
                  <Typography variant="subtitle1" sx={{ fontWeight: 800, lineHeight: 1.2 }}>
                    Cobrado
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Órdenes aprobadas y completadas
                  </Typography>
                </Box>
              </Stack>

              {cargando ? (
                <Skeleton width={160} height={44} />
              ) : (
                <Typography variant="h4" sx={{ fontWeight: 900 }}>
                  {soles(resumen?.revenue ?? 0)}
                </Typography>
              )}
              <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 1 }}>
                Una orden pendiente todavía no es una venta, y una rechazada no lo será
                nunca: ninguna de las dos suma aquí.
              </Typography>

              <Button
                component={Link}
                href="/admin/fraud/modelo"
                variant="outlined"
                fullWidth
                endIcon={<ArrowForwardIcon />}
                sx={{ mt: 2.5, textTransform: "none", fontWeight: 700, borderRadius: 2 }}
              >
                Ver el detalle del antifraude
              </Button>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </>
  );
}
