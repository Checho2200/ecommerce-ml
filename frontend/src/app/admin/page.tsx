"use client";

import { useEffect, useState } from "react";
import { api, FraudMetricsResponse } from "@/lib/api";
import { useAuth } from "@/lib/auth";

// MUI
import {
  Box,
  Typography,
  Grid,
  Card,
  CardContent,
  Chip,
  Skeleton,
  alpha,
} from "@mui/material";
import { keyframes } from "@mui/system";

// MUI Icons
import InventoryIcon from "@mui/icons-material/Inventory";
import LabelIcon from "@mui/icons-material/Label";
import ShoppingCartIcon from "@mui/icons-material/ShoppingCart";
import BuildIcon from "@mui/icons-material/Build";
import PsychologyIcon from "@mui/icons-material/Psychology";
import SettingsIcon from "@mui/icons-material/Settings";
import TimerIcon from "@mui/icons-material/Timer";
import DoneAllIcon from "@mui/icons-material/DoneAll";
import PaidOutlinedIcon from "@mui/icons-material/PaidOutlined";
import RuleIcon from "@mui/icons-material/Rule";

const fadeIn = keyframes`
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
`;

/** Una cifra del panel, con su icono y su pie explicativo. */
function TarjetaMetrica({
  titulo,
  valor,
  pie,
  icono,
  color,
  cargando,
}: {
  titulo: string;
  valor: string;
  pie: string;
  icono: React.ReactNode;
  color: string;
  cargando: boolean;
}) {
  return (
    <Card elevation={0} sx={{ borderRadius: 3, border: "1px solid", borderColor: "divider", height: "100%" }}>
      <CardContent sx={{ p: 3 }}>
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
          <Typography variant="body2" sx={{ color: "text.secondary", fontWeight: 600, textTransform: "uppercase", fontSize: "0.72rem" }}>
            {titulo}
          </Typography>
          {icono}
        </Box>
        {cargando ? (
          <Skeleton width={80} height={40} />
        ) : (
          <Typography variant="h4" sx={{ fontWeight: 900, color }}>
            {valor}
          </Typography>
        )}
        <Typography variant="caption" sx={{ color: "text.secondary", display: "block", mt: 1 }}>
          {pie}
        </Typography>
      </CardContent>
    </Card>
  );
}

const soles = (monto: number) =>
  `S/ ${monto.toLocaleString("es-PE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

interface DashboardStats {
  totalProducts: number;
  totalOrders: number;
  totalServices: number;
  totalCategories: number;
}

export default function AdminDashboard() {
  const { user, isAdmin } = useAuth();
  const [stats, setStats] = useState<DashboardStats>({
    totalProducts: 0,
    totalOrders: 0,
    totalServices: 0,
    totalCategories: 0,
  });
  const [fraudMetrics, setFraudMetrics] = useState<FraudMetricsResponse | null>(null);
  const [health, setHealth] = useState<{ status: string; database: string; ml_model: string } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const [products, categories] = await Promise.all([
          api.products.list({ per_page: 1, active_only: false }),
          api.categories.list(),
        ]);

        let ordersTotal = 0;
        let servicesTotal = 0;

        if (isAdmin) {
          try {
            const orders = await api.orders.list({ per_page: 1 });
            ordersTotal = orders.total;
          } catch { /* no admin access */ }

          try {
            const services = await api.serviceOrders.list({ page: 1 });
            servicesTotal = services.total;
          } catch { /* no admin access */ }
          
          try {
            const metrics = await api.fraud.getMetrics();
            setFraudMetrics(metrics);
          } catch { /* ignored */ }
        }

        try {
          const healthData = await api.system.health();
          setHealth(healthData);
        } catch { /* ignored */ }

        setStats({
          totalProducts: products.total,
          totalCategories: categories.length,
          totalOrders: ordersTotal,
          totalServices: servicesTotal,
        });
      } catch (err) {
        console.error("Error fetching stats:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
  }, [isAdmin]);

  const STAT_CARDS = [
    { value: stats.totalProducts, label: "Productos", icon: <InventoryIcon />, color: "#6366f1" },
    { value: stats.totalCategories, label: "Categorías", icon: <LabelIcon />, color: "#06b6d4" },
    { value: stats.totalOrders, label: "Órdenes", icon: <ShoppingCartIcon />, color: "#10b981" },
    { value: stats.totalServices, label: "Servicios", icon: <BuildIcon />, color: "#f59e0b" },
  ];

  return (
    <>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <Box>
            <Typography variant="h5" sx={{ fontWeight: 800 }}>
              Dashboard
            </Typography>
            <Typography variant="body2" sx={{ color: "text.secondary", mt: 0.5 }}>
              Bienvenido, {user?.full_name} 👋
            </Typography>
          </Box>
          <Chip
            label="🟢 Sistema Activo"
            variant="outlined"
            color="success"
            sx={{ fontWeight: 700 }}
          />
        </Box>
      </Box>

      {/* Stats Grid */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {STAT_CARDS.map((card, i) => (
          <Grid size={{ xs: 6, md: 3 }} key={i}>
            <Card
              elevation={0}
              sx={{
                borderRadius: 3,
                border: "1px solid",
                borderColor: "divider",
                animation: `${fadeIn} 0.5s ease-out ${i * 0.1}s both`,
                transition: "all 0.2s",
                "&:hover": {
                  transform: "translateY(-4px)",
                  boxShadow: `0 12px 24px -8px ${alpha(card.color, 0.2)}`,
                  borderColor: card.color,
                },
              }}
            >
              <CardContent sx={{ p: 3 }}>
                <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
                  <Typography variant="body2" sx={{ color: "text.secondary", fontWeight: 600, textTransform: "uppercase", fontSize: "0.72rem", letterSpacing: 0.5 }}>
                    {card.label}
                  </Typography>
                  <Box
                    sx={{
                      width: 40,
                      height: 40,
                      borderRadius: 2,
                      bgcolor: alpha(card.color, 0.1),
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      color: card.color,
                    }}
                  >
                    {card.icon}
                  </Box>
                </Box>
                {loading ? (
                  <Skeleton width={60} height={40} />
                ) : (
                  <Typography variant="h4" sx={{ fontWeight: 900, lineHeight: 1 }}>
                    {card.value}
                  </Typography>
                )}
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Fraud Metrics Grid */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="subtitle1" sx={{ fontWeight: 800, mb: 0.5, display: "flex", alignItems: "center", gap: 1 }}>
          <PsychologyIcon color="primary" /> Métricas del Modelo de Fraude (LightGBM)
        </Typography>
        <Typography variant="caption" sx={{ color: "text.secondary", display: "block", mb: 2 }}>
          Calculadas sobre los {fraudMetrics?.reviewed_count ?? 0} pedidos ya
          revisados y etiquetados, de {fraudMetrics?.total_evaluations ?? 0}{" "}
          evaluados. Un pedido bloqueado nunca llega a cobrarse, así que nunca
          tendrá un contracargo que lo confirme: los aciertos más valiosos del
          modelo son también los más difíciles de etiquetar.
        </Typography>

        <Grid container spacing={3} sx={{ mb: 3 }}>
          <Grid size={{ xs: 12, md: 4 }}>
            <TarjetaMetrica
              titulo="Precisión"
              valor={`${fraudMetrics?.precision ?? 0}%`}
              pie="De cada alerta, cuántas eran fraude de verdad"
              icono={<DoneAllIcon color="success" />}
              color="success.main"
              cargando={loading}
            />
          </Grid>
          <Grid size={{ xs: 12, md: 4 }}>
            <TarjetaMetrica
              titulo="Exhaustividad (recall)"
              valor={`${fraudMetrics?.recall ?? 0}%`}
              pie="De los fraudes reales, cuántos alcanzó a detectar"
              icono={<RuleIcon color="primary" />}
              color="primary.main"
              cargando={loading}
            />
          </Grid>
          <Grid size={{ xs: 12, md: 4 }}>
            <TarjetaMetrica
              titulo="F1"
              valor={`${fraudMetrics?.f1_score ?? 0}%`}
              pie="El equilibrio entre las dos anteriores"
              icono={<PsychologyIcon color="secondary" />}
              color="text.primary"
              cargando={loading}
            />
          </Grid>
        </Grid>

        <Grid container spacing={3}>
          <Grid size={{ xs: 12, md: 4 }}>
            <Card elevation={0} sx={{ borderRadius: 3, border: "1px solid", borderColor: "divider", height: "100%" }}>
              <CardContent sx={{ p: 3 }}>
                <Typography variant="body2" sx={{ color: "text.secondary", fontWeight: 600, textTransform: "uppercase", fontSize: "0.72rem", mb: 2 }}>
                  Matriz de confusión
                </Typography>
                {[
                  { etiqueta: "Fraudes detectados", valor: fraudMetrics?.true_positives ?? 0, color: "success.main" },
                  { etiqueta: "Fraudes que se escaparon", valor: fraudMetrics?.false_negatives ?? 0, color: "error.main" },
                  { etiqueta: "Falsas alarmas", valor: fraudMetrics?.false_positives ?? 0, color: "warning.main" },
                  { etiqueta: "Compras buenas bien aprobadas", valor: fraudMetrics?.true_negatives ?? 0, color: "text.primary" },
                ].map((fila) => (
                  <Box key={fila.etiqueta} sx={{ display: "flex", justifyContent: "space-between", py: 0.75 }}>
                    <Typography variant="body2" sx={{ color: "text.secondary" }}>{fila.etiqueta}</Typography>
                    <Typography variant="body2" sx={{ fontWeight: 800, color: fila.color }}>{fila.valor}</Typography>
                  </Box>
                ))}
              </CardContent>
            </Card>
          </Grid>

          <Grid size={{ xs: 12, md: 4 }}>
            <Card elevation={0} sx={{ borderRadius: 3, border: "1px solid", borderColor: "divider", height: "100%" }}>
              <CardContent sx={{ p: 3 }}>
                <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
                  <Typography variant="body2" sx={{ color: "text.secondary", fontWeight: 600, textTransform: "uppercase", fontSize: "0.72rem" }}>
                    Impacto en dinero
                  </Typography>
                  <PaidOutlinedIcon color="success" />
                </Box>
                {[
                  { etiqueta: "Pérdida evitada", valor: soles(fraudMetrics?.loss_prevented ?? 0), color: "success.main" },
                  { etiqueta: "Pérdida asumida", valor: soles(fraudMetrics?.loss_absorbed ?? 0), color: "error.main" },
                  { etiqueta: "Ganancia no realizada", valor: soles(fraudMetrics?.revenue_lost ?? 0), color: "warning.main" },
                ].map((fila) => (
                  <Box key={fila.etiqueta} sx={{ display: "flex", justifyContent: "space-between", py: 0.75 }}>
                    <Typography variant="body2" sx={{ color: "text.secondary" }}>{fila.etiqueta}</Typography>
                    <Typography variant="body2" sx={{ fontWeight: 800, color: fila.color }}>{fila.valor}</Typography>
                  </Box>
                ))}
                <Typography variant="caption" sx={{ color: "text.secondary", display: "block", mt: 1 }}>
                  Frenar una compra buena no cuesta el pedido entero: cuesta el
                  margen de esa venta.
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid size={{ xs: 12, md: 4 }}>
            <TarjetaMetrica
              titulo="Tiempo de evaluación"
              valor={`${fraudMetrics?.average_detection_time_ms.toFixed(1) ?? 0} ms`}
              pie={`Promedio sobre ${fraudMetrics?.total_evaluations ?? 0} evaluaciones`}
              icono={<TimerIcon color="info" />}
              color="info.main"
              cargando={loading}
            />
          </Grid>
        </Grid>
      </Box>

      {/* Quick Info Cards */}
      <Grid container spacing={3}>

        {/* System Info */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Card
            elevation={0}
            sx={{
              borderRadius: 3,
              border: "1px solid",
              borderColor: "divider",
              height: "100%",
            }}
          >
            <CardContent sx={{ p: 3 }}>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, mb: 2 }}>
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
                  <SettingsIcon />
                </Box>
                <Box>
                  <Typography variant="subtitle1" sx={{ fontWeight: 800, lineHeight: 1.2 }}>
                    Info del Sistema
                  </Typography>
                  <Typography variant="caption" sx={{ color: "text.secondary" }}>
                    Estado de los componentes
                  </Typography>
                </Box>
              </Box>

              <Box sx={{ display: "flex", flexDirection: "column", gap: 0 }}>
                {[
                  { label: "Backend API", status: health ? "Activo" : "Error", chipColor: health ? "success" as const : "error" as const },
                  { label: "Base de Datos", status: health?.database === "connected" ? "Activa" : "Pendiente", chipColor: health?.database === "connected" ? "info" as const : "warning" as const },
                  { label: "Modelo ML", status: health?.ml_model === "loaded" ? "Cargado" : "Pendiente", chipColor: health?.ml_model === "loaded" ? "success" as const : "warning" as const },
                  { label: "Pasarela de Pago", status: "MercadoPago (Sandbox)", chipColor: "primary" as const },
                ].map((item, i, arr) => (
                  <Box
                    key={i}
                    sx={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      py: 1.5,
                      borderBottom: i < arr.length - 1 ? "1px solid" : "none",
                      borderColor: "divider",
                    }}
                  >
                    <Typography variant="body2" sx={{ color: "text.secondary" }}>
                      {item.label}
                    </Typography>
                    <Chip
                      label={item.status}
                      size="small"
                      color={item.chipColor}
                      variant="outlined"
                      sx={{ fontWeight: 700, fontSize: "0.7rem" }}
                    />
                  </Box>
                ))}
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </>
  );
}
