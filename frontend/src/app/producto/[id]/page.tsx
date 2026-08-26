"use client";

/**
 * Ficha de producto.
 *
 * Estaba escrita en Tailwind puro con paleta índigo, fuera del sistema de
 * diseño del resto del sitio, y su modo oscuro (clases `dark:`) nunca se
 * activaba porque el tema se controla desde un store de Zustand, no desde una
 * clase en el <html>. Ahora usa MUI y el mismo theme que las demás páginas.
 */

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";

import Header from "@/components/ui/Header";
import ProductCard, { ProductCardSkeleton } from "@/components/ui/ProductCard";
import SafeImage from "@/components/ui/SafeImage";
import { api, ProductResponse, ProductReviewResponse, ApiError } from "@/lib/api";
import { useCart } from "@/lib/cart";
import { useAuth } from "@/lib/auth";

import {
  Box,
  Container,
  Grid,
  Paper,
  Typography,
  Button,
  IconButton,
  Chip,
  Rating,
  Divider,
  TextField,
  Alert,
  Avatar,
  Stack,
  Skeleton,
  Breadcrumbs,
} from "@mui/material";
import ArrowBackIosNewIcon from "@mui/icons-material/ArrowBackIosNew";
import ShoppingCartIcon from "@mui/icons-material/ShoppingCart";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import AddIcon from "@mui/icons-material/Add";
import RemoveIcon from "@mui/icons-material/Remove";
import VerifiedUserOutlinedIcon from "@mui/icons-material/VerifiedUserOutlined";
import LocalShippingOutlinedIcon from "@mui/icons-material/LocalShippingOutlined";
import AutorenewOutlinedIcon from "@mui/icons-material/AutorenewOutlined";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutlined";
import StarBorderIcon from "@mui/icons-material/StarBorder";

const TRUST = [
  { icon: VerifiedUserOutlinedIcon, title: "Garantía", desc: "12 meses", color: "#16a34a" },
  { icon: LocalShippingOutlinedIcon, title: "Envío a todo el Perú", desc: "24-48 h útiles", color: "#2563eb" },
  { icon: AutorenewOutlinedIcon, title: "Devoluciones", desc: "7 días para cambios", color: "#ea580c" },
];

function DetailSkeleton() {
  return (
    <Container maxWidth="lg" sx={{ py: 5 }}>
      <Paper elevation={0} sx={{ borderRadius: 4, border: "1px solid", borderColor: "divider", overflow: "hidden" }}>
        <Grid container>
          <Grid size={{ xs: 12, md: 6 }}>
            <Skeleton variant="rectangular" sx={{ aspectRatio: "1/1" }} />
          </Grid>
          <Grid size={{ xs: 12, md: 6 }}>
            <Box sx={{ p: { xs: 3, md: 6 } }}>
              <Skeleton width={110} height={26} />
              <Skeleton width="90%" height={52} sx={{ mt: 2 }} />
              <Skeleton width="45%" height={28} sx={{ mt: 2 }} />
              <Skeleton width="35%" height={56} sx={{ mt: 3 }} />
              <Skeleton width="100%" height={90} sx={{ mt: 3 }} />
              <Skeleton width="100%" height={52} sx={{ mt: 3 }} />
            </Box>
          </Grid>
        </Grid>
      </Paper>
    </Container>
  );
}

export default function ProductDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { id } = params;

  const { isAuthenticated } = useAuth();
  const { addToCart } = useCart();

  const [product, setProduct] = useState<ProductResponse | null>(null);
  const [reviews, setReviews] = useState<ProductReviewResponse[]>([]);
  const [related, setRelated] = useState<ProductResponse[]>([]);
  const [relatedLoading, setRelatedLoading] = useState(true);
  const [loading, setLoading] = useState(true);
  // Separar "no existe" de "no se pudo cargar": antes ambos casos mostraban
  // "Producto no encontrado", lo que confunde cuando el backend está dormido.
  const [notFound, setNotFound] = useState(false);
  const [loadError, setLoadError] = useState(false);

  const [quantity, setQuantity] = useState(1);
  const [added, setAdded] = useState(false);

  const [rating, setRating] = useState<number | null>(5);
  const [comment, setComment] = useState("");
  const [reviewLoading, setReviewLoading] = useState(false);
  const [reviewError, setReviewError] = useState("");
  const [reviewSuccess, setReviewSuccess] = useState("");

  useEffect(() => {
    if (!id) return;
    let cancelled = false;

    const load = async () => {
      setLoading(true);
      setNotFound(false);
      setLoadError(false);
      try {
        const [prodRes, reviewsRes] = await Promise.all([
          api.products.get(id as string),
          api.reviews.getProductReviews(id as string),
        ]);
        if (cancelled) return;
        setProduct(prodRes);
        setReviews(reviewsRes);
      } catch (err) {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 404) setNotFound(true);
        else setLoadError(true);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    load();
    return () => {
      cancelled = true;
    };
  }, [id]);

  // Productos relacionados de la misma categoría
  useEffect(() => {
    if (!product) return;
    let cancelled = false;
    setRelatedLoading(true);

    api.products
      .list({ category_id: product.category_id, per_page: 5, active_only: true })
      .then((res) => {
        if (cancelled) return;
        setRelated(res.items.filter((p) => p.id !== product.id).slice(0, 4));
      })
      .catch(() => {
        if (!cancelled) setRelated([]);
      })
      .finally(() => {
        if (!cancelled) setRelatedLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [product]);

  const handleAddToCart = () => {
    if (!product) return;
    addToCart(product, quantity);
    setAdded(true);
    setTimeout(() => setAdded(false), 2000);
  };

  const handleSubmitReview = async (e: React.FormEvent) => {
    e.preventDefault();
    setReviewError("");
    setReviewSuccess("");
    setReviewLoading(true);
    try {
      const newReview = await api.reviews.create({
        product_id: id as string,
        rating: rating ?? 5,
        comment: comment.trim() || undefined,
      });
      setReviews([newReview, ...reviews]);
      setReviewSuccess("¡Tu reseña ha sido publicada!");
      setComment("");
      setRating(5);
    } catch (err) {
      // El backend rechaza reseñas de quien no compró el producto; ese mensaje
      // es útil para el cliente, así que se muestra tal cual.
      setReviewError(err instanceof ApiError ? err.message : "Error al publicar la reseña");
    } finally {
      setReviewLoading(false);
    }
  };

  if (loading) {
    return (
      <Box sx={{ bgcolor: "background.default", minHeight: "100vh" }}>
        <Header />
        <DetailSkeleton />
      </Box>
    );
  }

  if (notFound || loadError || !product) {
    return (
      <Box sx={{ bgcolor: "background.default", minHeight: "100vh" }}>
        <Header />
        <Container maxWidth="sm" sx={{ py: 12, textAlign: "center" }}>
          <ErrorOutlineIcon sx={{ fontSize: 64, color: "text.disabled", mb: 2 }} />
          <Typography variant="h5" sx={{ fontWeight: 800, mb: 1 }}>
            {notFound ? "Producto no encontrado" : "No pudimos cargar el producto"}
          </Typography>
          <Typography color="text.secondary" sx={{ mb: 4 }}>
            {notFound
              ? "El producto que buscas no existe o fue retirado del catálogo."
              : "Puede que el servidor esté despertando. Inténtalo de nuevo en unos segundos."}
          </Typography>
          <Stack direction="row" spacing={2} sx={{ justifyContent: "center" }}>
            {!notFound && (
              <Button variant="contained" onClick={() => router.refresh()}>
                Reintentar
              </Button>
            )}
            <Button variant={notFound ? "contained" : "outlined"} component={Link} href="/catalog">
              Ir al catálogo
            </Button>
          </Stack>
        </Container>
      </Box>
    );
  }

  const averageRating =
    reviews.length > 0 ? reviews.reduce((acc, r) => acc + r.rating, 0) / reviews.length : 0;
  const hasDiscount = !!product.discount_price;
  const discountPct = hasDiscount
    ? Math.round(((product.price - product.discount_price!) / product.price) * 100)
    : 0;

  return (
    <Box sx={{ bgcolor: "background.default", minHeight: "100vh" }}>
      <Header />

      <Container maxWidth="lg" sx={{ py: { xs: 3, md: 5 } }}>
        <Breadcrumbs sx={{ mb: 3 }}>
          <Typography
            component={Link}
            href="/catalog"
            variant="body2"
            sx={{ color: "text.secondary", textDecoration: "none", "&:hover": { color: "primary.main" } }}
          >
            Catálogo
          </Typography>
          {product.category?.name && (
            <Typography
              component={Link}
              href={`/catalog?category_id=${product.category_id}`}
              variant="body2"
              sx={{ color: "text.secondary", textDecoration: "none", "&:hover": { color: "primary.main" } }}
            >
              {product.category.name}
            </Typography>
          )}
          <Typography variant="body2" color="text.primary" sx={{ fontWeight: 600 }}>
            {product.name}
          </Typography>
        </Breadcrumbs>

        <Button
          onClick={() => router.back()}
          startIcon={<ArrowBackIosNewIcon sx={{ fontSize: 14 }} />}
          size="small"
          sx={{ mb: 2.5, color: "text.secondary" }}
        >
          Volver
        </Button>

        {/* ── Producto ─────────────────────────────────────── */}
        <Paper
          elevation={0}
          sx={{ borderRadius: 4, border: "1px solid", borderColor: "divider", overflow: "hidden", mb: 6 }}
        >
          <Grid container>
            <Grid size={{ xs: 12, md: 6 }}>
              <Box
                sx={{
                  position: "relative",
                  aspectRatio: "1/1",
                  bgcolor: "action.hover",
                  overflow: "hidden",
                }}
              >
                <SafeImage src={product.image_url} alt={product.name} objectFit="cover" />
                {hasDiscount && (
                  <Box
                    sx={{
                      position: "absolute", top: 16, left: 16,
                      bgcolor: "#dc2626", color: "white", px: 1.4, py: 0.5,
                      borderRadius: 1.5, fontWeight: 800, fontSize: "0.8rem",
                    }}
                  >
                    -{discountPct}%
                  </Box>
                )}
              </Box>
            </Grid>

            <Grid size={{ xs: 12, md: 6 }}>
              <Box sx={{ p: { xs: 3, md: 5 }, display: "flex", flexDirection: "column", height: "100%" }}>
                <Stack direction="row" spacing={1} sx={{ mb: 2, flexWrap: "wrap", gap: 1 }}>
                  <Chip
                    label={product.category?.name || "Hardware"}
                    size="small"
                    color="primary"
                    variant="outlined"
                    sx={{ fontWeight: 700 }}
                  />
                  {product.stock > 0 && product.stock <= 5 && (
                    <Chip
                      label={`¡Solo quedan ${product.stock}!`}
                      size="small"
                      sx={{ bgcolor: "#fff7ed", color: "#c2410c", fontWeight: 700, border: "1px solid #fed7aa" }}
                    />
                  )}
                </Stack>

                <Typography
                  variant="h4"
                  sx={{ fontWeight: 900, lineHeight: 1.2, fontSize: { xs: "1.6rem", md: "2.1rem" } }}
                >
                  {product.name}
                </Typography>

                <Stack direction="row" spacing={1.2} sx={{ alignItems: "center", mt: 2 }}>
                  <Rating value={averageRating} precision={0.5} readOnly size="small" />
                  <Typography variant="body2" color="text.secondary">
                    {reviews.length} {reviews.length === 1 ? "reseña" : "reseñas"}
                  </Typography>
                </Stack>

                <Stack direction="row" spacing={1.5} sx={{ alignItems: "flex-end", mt: 3 }}>
                  <Typography
                    variant="h3"
                    sx={{
                      fontWeight: 900, lineHeight: 1,
                      color: hasDiscount ? "#dc2626" : "primary.main",
                      fontSize: { xs: "2rem", md: "2.6rem" },
                    }}
                  >
                    S/{(hasDiscount ? product.discount_price! : product.price).toFixed(2)}
                  </Typography>
                  {hasDiscount && (
                    <Typography
                      variant="h6"
                      sx={{ color: "text.disabled", textDecoration: "line-through", pb: 0.4 }}
                    >
                      S/{product.price.toFixed(2)}
                    </Typography>
                  )}
                </Stack>

                <Typography color="text.secondary" sx={{ mt: 3, lineHeight: 1.85 }}>
                  {product.description || "Sin descripción detallada para este producto."}
                </Typography>

                <Box sx={{ mt: "auto", pt: 4 }}>
                  {product.stock > 0 ? (
                    <Stack direction={{ xs: "column", sm: "row" }} spacing={2} sx={{ mb: 3 }}>
                      <Stack
                        direction="row"
                        sx={{
                          alignItems: "center",
                          border: "1px solid", borderColor: "divider",
                          borderRadius: 99, width: "fit-content",
                        }}
                      >
                        <IconButton
                          onClick={() => setQuantity((q) => Math.max(1, q - 1))}
                          disabled={quantity <= 1}
                          aria-label="Disminuir cantidad"
                        >
                          <RemoveIcon fontSize="small" />
                        </IconButton>
                        <Typography sx={{ width: 36, textAlign: "center", fontWeight: 800 }}>
                          {quantity}
                        </Typography>
                        <IconButton
                          onClick={() => setQuantity((q) => Math.min(product.stock, q + 1))}
                          disabled={quantity >= product.stock}
                          aria-label="Aumentar cantidad"
                        >
                          <AddIcon fontSize="small" />
                        </IconButton>
                      </Stack>

                      <Button
                        onClick={handleAddToCart}
                        variant="contained"
                        size="large"
                        color={added ? "success" : "primary"}
                        startIcon={added ? <CheckCircleIcon /> : <ShoppingCartIcon />}
                        sx={{ flex: 1, py: 1.4, fontWeight: 800, borderRadius: 99 }}
                      >
                        {added ? "Agregado al carrito" : "Agregar al carrito"}
                      </Button>
                    </Stack>
                  ) : (
                    <Box
                      sx={{
                        py: 2, mb: 3, textAlign: "center", borderRadius: 2,
                        bgcolor: "action.hover", color: "text.secondary", fontWeight: 800,
                      }}
                    >
                      Producto agotado
                    </Box>
                  )}

                  <Divider sx={{ mb: 3 }} />

                  <Grid container spacing={2}>
                    {TRUST.map((t) => (
                      <Grid size={{ xs: 12, sm: 4 }} key={t.title}>
                        <Stack direction="row" spacing={1.5} sx={{ alignItems: "center" }}>
                          <Box
                            sx={{
                              width: 40, height: 40, borderRadius: "50%", flexShrink: 0,
                              display: "flex", alignItems: "center", justifyContent: "center",
                              bgcolor: `${t.color}1A`, color: t.color,
                            }}
                          >
                            <t.icon fontSize="small" />
                          </Box>
                          <Box>
                            <Typography variant="caption" sx={{ fontWeight: 800, display: "block" }}>
                              {t.title}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              {t.desc}
                            </Typography>
                          </Box>
                        </Stack>
                      </Grid>
                    ))}
                  </Grid>
                </Box>
              </Box>
            </Grid>
          </Grid>
        </Paper>

        {/* ── Reseñas ──────────────────────────────────────── */}
        <Paper
          elevation={0}
          sx={{ borderRadius: 4, border: "1px solid", borderColor: "divider", p: { xs: 3, md: 5 }, mb: 6 }}
        >
          <Typography variant="h5" sx={{ fontWeight: 900, mb: 4 }}>
            Opiniones de clientes
          </Typography>

          <Grid container spacing={{ xs: 4, md: 6 }}>
            <Grid size={{ xs: 12, md: 4 }}>
              <Box
                sx={{
                  p: 3, borderRadius: 3, bgcolor: "action.hover", textAlign: "center", mb: 3,
                }}
              >
                <Typography variant="h2" sx={{ fontWeight: 900, lineHeight: 1 }}>
                  {averageRating.toFixed(1)}
                </Typography>
                <Rating value={averageRating} precision={0.5} readOnly sx={{ my: 1.5 }} />
                <Typography variant="body2" color="text.secondary">
                  Basado en {reviews.length} {reviews.length === 1 ? "reseña" : "reseñas"}
                </Typography>
              </Box>

              <Divider sx={{ mb: 3 }} />

              <Typography variant="subtitle1" sx={{ fontWeight: 800, mb: 2 }}>
                ¿Compraste este producto?
              </Typography>

              {isAuthenticated ? (
                <Box component="form" onSubmit={handleSubmitReview}>
                  {reviewError && (
                    <Alert severity="error" sx={{ mb: 2 }}>
                      {reviewError}
                    </Alert>
                  )}
                  {reviewSuccess && (
                    <Alert severity="success" sx={{ mb: 2 }}>
                      {reviewSuccess}
                    </Alert>
                  )}

                  <Typography variant="body2" sx={{ fontWeight: 600, mb: 1 }}>
                    Tu calificación
                  </Typography>
                  <Rating
                    value={rating}
                    onChange={(_, v) => setRating(v)}
                    size="large"
                    sx={{ mb: 2.5 }}
                  />

                  <TextField
                    fullWidth
                    multiline
                    rows={3}
                    label="Comentario (opcional)"
                    placeholder="Cuéntanos qué te pareció…"
                    value={comment}
                    onChange={(e) => setComment(e.target.value)}
                    sx={{ mb: 2.5 }}
                  />

                  <Button
                    type="submit"
                    fullWidth
                    variant="contained"
                    disabled={reviewLoading}
                    sx={{ py: 1.2, fontWeight: 700 }}
                  >
                    {reviewLoading ? "Publicando…" : "Publicar reseña"}
                  </Button>
                </Box>
              ) : (
                <Box sx={{ p: 3, borderRadius: 3, bgcolor: "action.hover", textAlign: "center" }}>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    Inicia sesión para compartir tu experiencia con otros clientes.
                  </Typography>
                  <Button component={Link} href="/login" variant="contained" size="small">
                    Iniciar sesión
                  </Button>
                </Box>
              )}
            </Grid>

            <Grid size={{ xs: 12, md: 8 }}>
              {reviews.length === 0 ? (
                <Box sx={{ py: 8, textAlign: "center", color: "text.secondary" }}>
                  <StarBorderIcon sx={{ fontSize: 48, color: "text.disabled", mb: 1.5 }} />
                  <Typography sx={{ fontWeight: 700 }}>Aún no hay reseñas</Typography>
                  <Typography variant="body2">
                    Sé el primero en opinar sobre este producto.
                  </Typography>
                </Box>
              ) : (
                <Stack spacing={2.5}>
                  {reviews.map((review) => (
                    <Box key={review.id} sx={{ p: 3, borderRadius: 3, bgcolor: "action.hover" }}>
                      <Stack
                        direction="row"
                        sx={{ justifyContent: "space-between", alignItems: "flex-start", mb: 1.5 }}
                      >
                        <Stack direction="row" spacing={1.5} sx={{ alignItems: "center" }}>
                          <Avatar sx={{ bgcolor: "primary.main", width: 40, height: 40, fontWeight: 800 }}>
                            {review.user_name?.charAt(0).toUpperCase()}
                          </Avatar>
                          <Box>
                            <Typography variant="body2" sx={{ fontWeight: 800 }}>
                              {review.user_name}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              Comprador verificado
                            </Typography>
                          </Box>
                        </Stack>
                        <Typography variant="caption" color="text.secondary">
                          {new Date(review.created_at).toLocaleDateString("es-PE")}
                        </Typography>
                      </Stack>
                      <Rating value={review.rating} readOnly size="small" sx={{ mb: 1.5 }} />
                      {review.comment && (
                        <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.75 }}>
                          {review.comment}
                        </Typography>
                      )}
                    </Box>
                  ))}
                </Stack>
              )}
            </Grid>
          </Grid>
        </Paper>

        {/* ── Relacionados ─────────────────────────────────── */}
        {(relatedLoading || related.length > 0) && (
          <Box sx={{ mb: 4 }}>
            <Typography variant="h5" sx={{ fontWeight: 900, mb: 3 }}>
              También te puede interesar
            </Typography>
            <Grid container spacing={2.5}>
              {relatedLoading
                ? Array.from({ length: 4 }).map((_, i) => (
                    <Grid size={{ xs: 6, sm: 6, md: 3 }} key={`rel-skeleton-${i}`}>
                      <ProductCardSkeleton />
                    </Grid>
                  ))
                : related.map((p, i) => (
                    <Grid size={{ xs: 6, sm: 6, md: 3 }} key={p.id}>
                      <ProductCard product={p} index={i} />
                    </Grid>
                  ))}
            </Grid>
          </Box>
        )}
      </Container>
    </Box>
  );
}
