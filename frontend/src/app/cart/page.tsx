"use client";

import { useCartStore } from "@/lib/stores/cart";
import Header from "@/components/ui/Header";
import Link from "next/link";

// MUI
import {
  Container,
  Typography,
  Box,
  Button,
  IconButton,
  Card,
  CardContent,
  Divider,
} from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import ShoppingBagOutlinedIcon from "@mui/icons-material/ShoppingBagOutlined";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import AddIcon from "@mui/icons-material/Add";
import RemoveIcon from "@mui/icons-material/Remove";

export default function CartPage() {
  const { items, updateQuantity, removeFromCart, totalPrice, totalItems } = useCartStore();

  return (
    <Box sx={{ minHeight: "100dvh", bgcolor: "background.default" }}>
      <Header />

      <Container maxWidth="lg" sx={{ py: { xs: 4, md: 6 } }}>
        <Typography variant="h4" sx={{ fontWeight: 900, mb: 4 }}>
          Mi Carrito
        </Typography>

        {items.length === 0 ? (
          /* ── Estado vacío ────────────────────────────── */
          <Card
            elevation={0}
            sx={{
              border: "1px solid",
              borderColor: "divider",
              borderRadius: 3,
              p: { xs: 6, md: 8 },
              textAlign: "center",
            }}
          >
            <ShoppingBagOutlinedIcon sx={{ fontSize: 64, color: "text.disabled", mb: 2 }} />
            <Typography variant="h6" sx={{ fontWeight: 700, mb: 1 }}>
              Tu carrito está vacío
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 4, maxWidth: 360, mx: "auto" }}>
              No tienes ningún producto en tu carrito. Explora nuestro catálogo y encuentra lo que buscas.
            </Typography>
            <Button
              component={Link}
              href="/catalog"
              variant="contained"
              size="large"
              sx={{ textTransform: "none", fontWeight: 700, borderRadius: 2, px: 4 }}
            >
              Ver Catálogo
            </Button>
          </Card>
        ) : (
          /* ── Con productos ──────────────────────────── */
          <Box className="flex flex-col lg:flex-row gap-6">
            {/* Lista de productos */}
            <Box sx={{ flex: 1 }}>
              <Card
                elevation={0}
                sx={{
                  border: "1px solid",
                  borderColor: "divider",
                  borderRadius: 3,
                  overflow: "hidden",
                }}
              >
                {/* Header */}
                <Box sx={{ px: 3, py: 2, bgcolor: "action.hover" }}>
                  <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                    Productos ({totalItems})
                  </Typography>
                </Box>

                {/* Items */}
                {items.map((item, index) => (
                  <Box key={item.product.id}>
                    {index > 0 && <Divider />}
                    <Box sx={{ p: 3 }} className="flex flex-col sm:flex-row gap-4">
                      {/* Imagen */}
                      <Box
                        sx={{
                          width: { xs: 80, sm: 100 },
                          height: { xs: 80, sm: 100 },
                          borderRadius: 2,
                          bgcolor: "grey.100",
                          flexShrink: 0,
                          overflow: "hidden",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                        }}
                      >
                        {item.product.image_url ? (
                          <img
                            src={item.product.image_url}
                            alt={item.product.name}
                            className="w-full h-full object-contain"
                          />
                        ) : (
                          <Typography variant="caption" color="text.secondary">
                            Sin imagen
                          </Typography>
                        )}
                      </Box>

                      {/* Detalles */}
                      <Box sx={{ flex: 1, display: "flex", flexDirection: "column" }}>
                        <Box className="flex justify-between items-start gap-3">
                          <Box>
                            <Typography
                              component={Link}
                              href={`/producto/${item.product.id}`}
                              variant="subtitle1"
                              sx={{
                                fontWeight: 700,
                                textDecoration: "none",
                                color: "text.primary",
                                "&:hover": { color: "primary.main" },
                              }}
                            >
                              {item.product.name}
                            </Typography>
                            <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 0.25 }}>
                              {item.product.category?.name || "Hardware"}
                            </Typography>
                          </Box>
                          <Typography variant="subtitle1" sx={{ fontWeight: 800, whiteSpace: "nowrap" }}>
                            S/{(item.product.price * item.quantity).toFixed(2)}
                          </Typography>
                        </Box>

                        <Box sx={{ mt: "auto", pt: 2 }} className="flex justify-between items-center">
                          {/* Cantidad */}
                          <Box
                            sx={{
                              display: "flex",
                              alignItems: "center",
                              border: "1px solid",
                              borderColor: "divider",
                              borderRadius: 2,
                            }}
                          >
                            <IconButton
                              size="small"
                              onClick={() => updateQuantity(item.product.id, Math.max(1, item.quantity - 1))}
                              disabled={item.quantity <= 1}
                            >
                              <RemoveIcon fontSize="small" />
                            </IconButton>
                            <Typography
                              variant="body2"
                              sx={{ width: 32, textAlign: "center", fontWeight: 700 }}
                            >
                              {item.quantity}
                            </Typography>
                            <IconButton
                              size="small"
                              onClick={() => updateQuantity(item.product.id, Math.min(item.product.stock, item.quantity + 1))}
                              disabled={item.quantity >= item.product.stock}
                            >
                              <AddIcon fontSize="small" />
                            </IconButton>
                          </Box>

                          {/* Eliminar */}
                          <Button
                            size="small"
                            color="error"
                            startIcon={<DeleteIcon />}
                            onClick={() => removeFromCart(item.product.id)}
                            sx={{ textTransform: "none", fontWeight: 600 }}
                          >
                            Eliminar
                          </Button>
                        </Box>
                      </Box>
                    </Box>
                  </Box>
                ))}
              </Card>
            </Box>

            {/* Resumen */}
            <Box sx={{ width: { xs: "100%", lg: 320 }, flexShrink: 0 }}>
              <Card
                elevation={0}
                sx={{
                  border: "1px solid",
                  borderColor: "divider",
                  borderRadius: 3,
                  p: 3,
                  position: "sticky",
                  top: 96,
                }}
              >
                <Typography variant="h6" sx={{ fontWeight: 700, mb: 3 }}>
                  Resumen de Orden
                </Typography>

                <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5, mb: 3 }}>
                  <Box className="flex justify-between">
                    <Typography variant="body2" color="text.secondary">
                      Subtotal ({totalItems} productos)
                    </Typography>
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>
                      S/{totalPrice.toFixed(2)}
                    </Typography>
                  </Box>
                  <Box className="flex justify-between">
                    <Typography variant="body2" color="text.secondary">
                      Envío
                    </Typography>
                    <Typography variant="body2" sx={{ fontWeight: 600, color: "success.main" }}>
                      Gratis
                    </Typography>
                  </Box>
                </Box>

                <Divider sx={{ mb: 3 }} />

                <Box className="flex justify-between items-end" sx={{ mb: 3 }}>
                  <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                    Total
                  </Typography>
                  <Typography variant="h5" sx={{ fontWeight: 900, color: "primary.main" }}>
                    S/{totalPrice.toFixed(2)}
                  </Typography>
                </Box>

                <Button
                  component={Link}
                  href="/checkout"
                  variant="contained"
                  fullWidth
                  size="large"
                  endIcon={<ArrowForwardIcon />}
                  sx={{
                    textTransform: "none",
                    fontWeight: 700,
                    borderRadius: 2,
                    py: 1.5,
                  }}
                >
                  Ir al Checkout
                </Button>

                <Box sx={{ textAlign: "center", mt: 2 }}>
                  <Button
                    component={Link}
                    href="/catalog"
                    size="small"
                    sx={{ textTransform: "none", fontWeight: 600 }}
                  >
                    Seguir comprando
                  </Button>
                </Box>
              </Card>
            </Box>
          </Box>
        )}
      </Container>
    </Box>
  );
}
