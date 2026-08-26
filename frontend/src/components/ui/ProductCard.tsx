"use client";

/**
 * Tarjeta de producto compartida — la usan la portada, el catálogo y los
 * productos relacionados de la ficha.
 *
 * Sigue el patrón del comercio electrónico que el cliente ya conoce: precio
 * grande y legible, estado del stock explícito y un botón de agregar a todo el
 * ancho, en lugar de un ícono pequeño en una esquina.
 */

import { useState } from "react";
import Link from "next/link";
import { ProductResponse } from "@/lib/api";
import { useCart } from "@/lib/cart";
import SafeImage from "@/components/ui/SafeImage";
import { DISPLAY_FONT } from "@/components/ThemeProvider";

import { Box, Card, Typography, Button, Skeleton, Stack } from "@mui/material";
import ShoppingCartIcon from "@mui/icons-material/ShoppingCart";
import CheckIcon from "@mui/icons-material/Check";
import { keyframes } from "@mui/system";

const fadeIn = keyframes`
  from { opacity: 0; transform: translateY(14px); }
  to { opacity: 1; transform: translateY(0); }
`;

/** Separador de miles a la peruana: S/ 1 899.00 */
function precio(n: number) {
  const [ent, dec] = n.toFixed(2).split(".");
  return { entero: ent.replace(/\B(?=(\d{3})+(?!\d))/g, " "), decimal: dec };
}

export default function ProductCard({
  product,
  index = 0,
  onAdded,
}: {
  product: ProductResponse;
  /** Posición en la grilla; escalona la animación de entrada. */
  index?: number;
  /** Aviso opcional al padre (la portada lo usa para su Snackbar). */
  onAdded?: (product: ProductResponse) => void;
}) {
  const { addToCart } = useCart();
  const [added, setAdded] = useState(false);

  const handleAdd = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    addToCart(product);
    setAdded(true);
    onAdded?.(product);
    setTimeout(() => setAdded(false), 2000);
  };

  const hasDiscount = !!product.discount_price;
  const shown = hasDiscount ? product.discount_price! : product.price;
  const discountPct = hasDiscount
    ? Math.round(((product.price - product.discount_price!) / product.price) * 100)
    : 0;
  const { entero, decimal } = precio(shown);

  const agotado = product.stock === 0;
  const pocas = product.stock > 0 && product.stock <= 5;

  return (
    <Card
      component={Link}
      href={`/producto/${product.id}`}
      elevation={0}
      sx={{
        position: "relative",
        textDecoration: "none",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        border: "1px solid",
        borderColor: "divider",
        bgcolor: "background.paper",
        transition: "border-color 0.25s, box-shadow 0.25s",
        animation: `${fadeIn} 0.45s ease-out ${index * 0.04}s both`,
        "@media (hover: hover)": {
          "&:hover": {
            borderColor: "primary.main",
            boxShadow: "0 14px 28px -18px rgba(12,58,110,0.55)",
            "& .product-img": { transform: "scale(1.05)" },
          },
        },
        "&:active": { borderColor: "primary.main" },
      }}
    >
      {/* Etiqueta de oferta o de stock bajo */}
      {hasDiscount ? (
        <Box
          sx={{
            position: "absolute", top: 10, left: 10, zIndex: 2,
            bgcolor: "error.main", color: "#FFFFFF",
            px: 1.1, py: 0.4, fontSize: "0.7rem", fontWeight: 800,
          }}
        >
          −{discountPct}%
        </Box>
      ) : pocas ? (
        <Box
          sx={{
            position: "absolute", top: 10, left: 10, zIndex: 2,
            bgcolor: "#F97316", color: "#FFFFFF",
            px: 1.1, py: 0.4, fontSize: "0.7rem", fontWeight: 800,
          }}
        >
          ÚLTIMAS {product.stock}
        </Box>
      ) : null}

      <Box sx={{ position: "relative", overflow: "hidden", aspectRatio: "1/1", bgcolor: "background.default" }}>
        <SafeImage
          src={product.image_url}
          alt={product.name}
          className="product-img"
          objectFit="cover"
          sx={{ transition: "transform 0.45s cubic-bezier(0.4,0,0.2,1)", opacity: agotado ? 0.55 : 1 }}
        />
      </Box>

      <Box sx={{ p: { xs: 1.5, sm: 2 }, display: "flex", flexDirection: "column", flexGrow: 1 }}>
        <Typography
          sx={{
            fontSize: "0.66rem", fontWeight: 700, letterSpacing: "0.05em",
            color: "text.secondary", textTransform: "uppercase",
          }}
        >
          {product.category?.name || "Hardware"}
        </Typography>

        <Typography
          sx={{
            fontSize: { xs: "0.85rem", sm: "0.92rem" }, fontWeight: 600, mt: 0.6, lineHeight: 1.35,
            display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden",
          }}
        >
          {product.name}
        </Typography>

        <Box sx={{ flexGrow: 1 }} />

        <Typography
          sx={{
            fontSize: "0.78rem", fontWeight: 700, mt: 1.4,
            color: agotado ? "text.disabled" : pocas ? "#F97316" : "#16A34A",
          }}
        >
          {agotado ? "Sin stock" : pocas ? `Quedan ${product.stock}` : "Disponible"}
        </Typography>

        {hasDiscount && (
          <Typography
            sx={{ fontSize: "0.78rem", color: "text.disabled", textDecoration: "line-through", mt: 0.3 }}
          >
            S/ {precio(product.price).entero}.{precio(product.price).decimal}
          </Typography>
        )}

        <Stack direction="row" sx={{ alignItems: "baseline", mt: hasDiscount ? 0 : 0.4 }}>
          <Typography
            sx={{
              fontFamily: DISPLAY_FONT,
              fontSize: { xs: "1.25rem", sm: "1.5rem" },
              color: hasDiscount ? "error.main" : "primary.main",
              lineHeight: 1.05,
            }}
          >
            S/ {entero}
          </Typography>
          <Typography
            sx={{
              fontFamily: DISPLAY_FONT,
              fontSize: { xs: "0.8rem", sm: "0.92rem" },
              color: hasDiscount ? "error.main" : "primary.main",
            }}
          >
            .{decimal}
          </Typography>
        </Stack>

        <Button
          onClick={handleAdd}
          disabled={agotado}
          fullWidth
          variant="contained"
          color={added ? "success" : "secondary"}
          startIcon={added ? <CheckIcon /> : <ShoppingCartIcon sx={{ fontSize: 18 }} />}
          sx={{
            mt: 1.6,
            py: { xs: 1, sm: 1.2 },
            fontWeight: 800,
            fontSize: { xs: "0.8rem", sm: "0.88rem" },
            "&:active": { transform: "scale(0.98)" },
          }}
        >
          {added ? "Agregado" : "Agregar"}
        </Button>
      </Box>
    </Card>
  );
}

/** Esqueleto con la misma silueta que la tarjeta real (evita saltos). */
export function ProductCardSkeleton() {
  return (
    <Card elevation={0} sx={{ border: "1px solid", borderColor: "divider" }}>
      <Skeleton variant="rectangular" sx={{ aspectRatio: "1/1" }} />
      <Box sx={{ p: { xs: 1.5, sm: 2 } }}>
        <Skeleton width="45%" height={12} />
        <Skeleton width="90%" height={18} sx={{ mt: 0.8 }} />
        <Skeleton width="65%" height={18} />
        <Skeleton width="40%" height={14} sx={{ mt: 1.4 }} />
        <Skeleton width="55%" height={30} sx={{ mt: 0.5 }} />
        <Skeleton variant="rectangular" height={40} sx={{ mt: 1.6 }} />
      </Box>
    </Card>
  );
}
