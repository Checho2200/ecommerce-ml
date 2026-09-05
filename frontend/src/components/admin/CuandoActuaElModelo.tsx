"use client";

/**
 * En qué momento exacto del checkout decide el modelo.
 *
 * Es la pregunta que el panel no respondía en ninguna parte: se veía el
 * puntaje de cada pedido, pero no cuándo se había calculado ni qué pasaba
 * después. Sin eso, "score 0.82" no dice si la compra se cobró igual.
 *
 * El dato que ordena todo lo demás es que el modelo corre ANTES de que exista
 * un cobro: un pedido bloqueado nunca llega a MercadoPago, así que no hay nada
 * que devolver. Los pasos siguen el orden de `order_service.crear_pedido`.
 */

import { Box, Card, CardContent, Chip, Stack, Typography } from "@mui/material";
import ShoppingCartCheckoutIcon from "@mui/icons-material/ShoppingCartCheckout";
import Inventory2OutlinedIcon from "@mui/icons-material/Inventory2Outlined";
import PsychologyIcon from "@mui/icons-material/Psychology";
import CallSplitIcon from "@mui/icons-material/CallSplit";
import CreditCardIcon from "@mui/icons-material/CreditCard";
import type { SvgIconComponent } from "@mui/icons-material";

const PASOS: {
  icono: SvgIconComponent;
  titulo: string;
  detalle: string;
  esElModelo?: boolean;
}[] = [
  {
    icono: ShoppingCartCheckoutIcon,
    titulo: "El cliente confirma",
    detalle: "Envía el carrito y la dirección desde el checkout.",
  },
  {
    icono: Inventory2OutlinedIcon,
    titulo: "Se reserva el stock",
    detalle: "Primero se aparta, para que dos compras del último artículo no lo vendan dos veces.",
  },
  {
    icono: PsychologyIcon,
    titulo: "El modelo evalúa",
    detalle: "Lee el monto, los artículos de alto riesgo, cuánto tardó el checkout y si la dirección es nueva.",
    esElModelo: true,
  },
  {
    icono: CallSplitIcon,
    titulo: "Se decide el estado",
    detalle: "Aprobada sigue al cobro; en revisión queda retenida; bloqueada se rechaza y devuelve el stock.",
  },
  {
    icono: CreditCardIcon,
    titulo: "Recién aquí se cobra",
    detalle: "Solo las aprobadas reciben un enlace de MercadoPago. El pago confirma después por webhook.",
  },
];

export default function CuandoActuaElModelo({
  milisegundos,
}: {
  /** Tiempo medio de evaluación, para poner una cifra al paso del modelo. */
  milisegundos?: number;
}) {
  return (
    <Card elevation={0} sx={{ border: "1px solid", borderColor: "divider", borderRadius: 3 }}>
      <CardContent sx={{ p: 3 }}>
        <Typography variant="subtitle1" sx={{ fontWeight: 800 }}>
          Cuándo actúa el modelo
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, mb: 3, maxWidth: 760 }}>
          La evaluación ocurre <strong>antes de que exista un cobro</strong>, dentro de la
          misma petición que crea el pedido. Un pedido bloqueado nunca llega a la pasarela
          de pago, así que no hay nada que reembolsar ni contracargo que esperar.
        </Typography>

        <Stack
          direction={{ xs: "column", lg: "row" }}
          spacing={{ xs: 2, lg: 0 }}
          sx={{ alignItems: "stretch" }}
        >
          {PASOS.map((paso, i) => (
            <Stack
              key={paso.titulo}
              direction={{ xs: "row", lg: "column" }}
              spacing={{ xs: 2, lg: 1.2 }}
              sx={{
                flex: 1,
                alignItems: { xs: "flex-start", lg: "flex-start" },
                px: { lg: 2 },
                // El primero no lleva separador a su izquierda: una línea
                // antes del paso 1 sugiere que viene de algún sitio anterior.
                borderLeft: { xs: "none", lg: i === 0 ? "none" : "1px solid" },
                borderColor: { lg: "divider" },
              }}
            >
              <Box
                sx={{
                  width: 40,
                  height: 40,
                  flexShrink: 0,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  border: "1px solid",
                  borderColor: paso.esElModelo ? "acento.main" : "divider",
                  bgcolor: paso.esElModelo ? "acento.main" : "transparent",
                  color: paso.esElModelo ? "acento.contrastText" : "text.secondary",
                  borderRadius: 2,
                }}
              >
                <paso.icono sx={{ fontSize: 21 }} />
              </Box>

              <Box>
                <Typography
                  variant="caption"
                  sx={{ color: "text.disabled", fontWeight: 700, display: "block" }}
                >
                  PASO {i + 1}
                </Typography>
                <Typography variant="body2" sx={{ fontWeight: 700, mt: 0.2 }}>
                  {paso.titulo}
                </Typography>
                <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 0.5, lineHeight: 1.6 }}>
                  {paso.detalle}
                </Typography>
                {paso.esElModelo && milisegundos !== undefined && (
                  <Chip
                    label={`≈ ${milisegundos.toFixed(1)} ms`}
                    size="small"
                    sx={{ mt: 1, fontWeight: 700, fontSize: "0.68rem" }}
                  />
                )}
              </Box>
            </Stack>
          ))}
        </Stack>
      </CardContent>
    </Card>
  );
}
