"use client";

/**
 * Tarjeta de producto compartida.
 *
 * Única implementación del sitio: la usan la portada, el catálogo y los
 * productos relacionados de la ficha de producto. Antes existían dos copias
 * distintas (portada y catálogo) que se habían ido desincronizando.
 */

import { useState } from "react";
import Link from "next/link";
import { ProductResponse } from "@/lib/api";
import { useCart } from "@/lib/cart";
import SafeImage from "@/components/ui/SafeImage";

import {
  Box,
  Card,
  CardContent,
  CardActions,
  Typography,
  IconButton,
  Chip,
  Skeleton,
} from "@mui/material";
import ShoppingCartIcon from "@mui/icons-material/ShoppingCart";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import { keyframes } from "@mui/system";

const fadeIn = keyframes`
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
`;

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
  const displayPrice = hasDiscount ? product.discount_price! : product.price;
  const discountPct = hasDiscount
    ? Math.round(((product.price - product.discount_price!) / product.price) * 100)
    : 0;

  return (
    <Card
      component={Link}
      href={`/producto/${product.id}`}
      elevation={0}
      sx={{
        textDecoration: "none",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        borderRadius: 3,
        border: "1px solid",
        borderColor: "divider",
        transition: "all 0.35s cubic-bezier(0.4,0,0.2,1)",
        animation: `${fadeIn} 0.5s ease-out ${index * 0.04}s both`,
        "&:hover": {
          transform: "translateY(-8px)",
          boxShadow: "0 20px 40px -12px rgba(0,0,0,0.14)",
          borderColor: "primary.main",
          "& .product-img": { transform: "scale(1.08)" },
        },
      }}
    >
      <Box
        sx={{
          position: "relative",
          overflow: "hidden",
          aspectRatio: "1/1",
          bgcolor: "action.hover",
        }}
      >
        <SafeImage
          src={product.image_url}
          alt={product.name}
          className="product-img"
          objectFit="cover"
          sx={{ transition: "transform 0.5s cubic-bezier(0.4,0,0.2,1)" }}
        />

        {hasDiscount && (
          <Box
            sx={{
              position: "absolute", top: 10, left: 10, zIndex: 2,
              bgcolor: "#dc2626", color: "white",
              borderRadius: 1.5, px: 1, py: 0.3,
              fontSize: "0.68rem", fontWeight: 800, letterSpacing: 0.5,
            }}
          >
            -{discountPct}%
          </Box>
        )}
        {product.stock === 0 ? (
          <Chip
            label="Agotado"
            size="small"
            color="error"
            sx={{ position: "absolute", top: hasDiscount ? 38 : 10, left: 10, fontWeight: 700, fontSize: "0.68rem" }}
          />
        ) : product.stock <= 5 ? (
          <Chip
            label={`¡Solo ${product.stock}!`}
            size="small"
            sx={{
              position: "absolute", top: hasDiscount ? 38 : 10, left: 10,
              bgcolor: "#fff7ed", color: "#c2410c", fontWeight: 700,
              fontSize: "0.68rem", border: "1px solid #fed7aa",
            }}
          />
        ) : null}
      </Box>

      <CardContent sx={{ flexGrow: 1, pb: 1 }}>
        <Typography variant="caption" sx={{ color: "text.secondary", fontWeight: 600 }}>
          {product.category?.name || "Hardware"}
        </Typography>
        <Typography
          variant="subtitle2"
          sx={{
            fontWeight: 800, color: "text.primary", lineHeight: 1.35, mt: 0.5,
            display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical",
            overflow: "hidden",
          }}
        >
          {product.name}
        </Typography>
        {product.description && (
          <Typography
            variant="caption"
            sx={{
              color: "text.secondary", mt: 0.75,
              display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical",
              overflow: "hidden",
            }}
          >
            {product.description}
          </Typography>
        )}
      </CardContent>

      <CardActions sx={{ px: 2, pb: 2, pt: 0, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <Box>
          {hasDiscount ? (
            <>
              <Typography variant="caption" sx={{ color: "text.disabled", textDecoration: "line-through", display: "block", lineHeight: 1 }}>
                S/{product.price.toFixed(2)}
              </Typography>
              <Typography variant="h6" sx={{ fontWeight: 900, color: "#dc2626", lineHeight: 1 }}>
                S/{displayPrice.toFixed(2)}
              </Typography>
            </>
          ) : (
            <Typography variant="h6" sx={{ fontWeight: 900, color: "primary.dark", lineHeight: 1 }}>
              S/{displayPrice.toFixed(2)}
            </Typography>
          )}
        </Box>
        <IconButton
          onClick={handleAdd}
          disabled={product.stock === 0}
          size="small"
          aria-label={`Agregar ${product.name} al carrito`}
          sx={{
            bgcolor: added ? "success.main" : "text.primary",
            color: "white", width: 42, height: 42,
            "&:hover": { bgcolor: added ? "success.main" : "primary.main" },
            "&.Mui-disabled": { bgcolor: "action.disabledBackground", color: "action.disabled" },
            transition: "all 0.2s",
          }}
        >
          {added ? <CheckCircleIcon sx={{ fontSize: 20 }} /> : <ShoppingCartIcon sx={{ fontSize: 18 }} />}
        </IconButton>
      </CardActions>
    </Card>
  );
}

/** Esqueleto de carga con la misma silueta que la tarjeta real (evita saltos). */
export function ProductCardSkeleton() {
  return (
    <Card elevation={0} sx={{ borderRadius: 3, border: "1px solid", borderColor: "divider" }}>
      <Skeleton variant="rectangular" sx={{ aspectRatio: "1/1" }} />
      <CardContent>
        <Skeleton width="40%" height={14} sx={{ mb: 1 }} />
        <Skeleton width="85%" height={18} sx={{ mb: 0.5 }} />
        <Skeleton width="60%" height={18} sx={{ mb: 1 }} />
        <Skeleton width="70%" height={14} />
      </CardContent>
      <CardActions sx={{ px: 2, pb: 2 }}>
        <Skeleton width="35%" height={28} />
        <Box sx={{ flexGrow: 1 }} />
        <Skeleton variant="circular" width={42} height={42} />
      </CardActions>
    </Card>
  );
}
