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
import { api, type OrderSummaryResponse } from "@/lib/api";
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
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    let vigente = true;

    const cargar = async () => {
      try {
        const [productos, categorias] = await Promise.all([
          api.products.list({ per_page: 1, active_only: false }),
          api.categories.list(),
        ]);

        let ordenes = 0;
        let servicios = 0;

        if (isAdmin) {
          try {
            // Una sola consulta agrupada trae el total y el desglose por
            // estado; antes hacía falta una petición paginada por cada uno.
            const datos = await api.orders.summary();
            if (vigente) setResumen(datos);
            ordenes = datos.total;
          } catch {
            /* sin permisos o API caída: las tarjetas quedan en cero */
          }
          try {
            servicios = (await api.serviceOrders.list({ page: 1 })).total;
          } catch {
            /* idem */
          }
        }

        try {
          if (vigente) setSalud(await api.system.health());
        } catch {
          if (vigente) setSalud(null);
        }

        if (vigente) {
          setCifras({
            productos: productos.total,
            categorias: categorias.length,
            ordenes,
            servicios,
          });
        }
      } finally {
        if (vigente) setCargando(false);
      }
    };

    cargar();
    return () => {
      vigente = false;
    };
  }, [isAdmin]);

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
                href="/admin/fraud"
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
