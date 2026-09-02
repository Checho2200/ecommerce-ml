"use client";

/**
 * Las opiniones de un producto: el resumen, la lista y el formulario.
 *
 * Vivía dentro de `app/producto/[id]/page.tsx`, que así cargaba con tres
 * asuntos a la vez. Aquí las reseñas se administran solas —su estado, su
 * validación y su envío— y la página solo le pasa el producto y recibe aviso
 * cuando hay una reseña nueva, para no tener que recargarlo todo.
 */

import { useState } from "react";
import Link from "next/link";
import { api, ApiError, ProductReviewResponse } from "@/lib/api";
import { useAuth } from "@/lib/auth";

import {
  Alert,
  Avatar,
  Box,
  Button,
  Divider,
  Grid,
  Paper,
  Rating,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import StarBorderIcon from "@mui/icons-material/StarBorder";

export default function SeccionDeResenas({
  productoId,
  resenas,
  promedio,
  onNuevaResena,
}: {
  productoId: string;
  resenas: ProductReviewResponse[];
  promedio: number;
  onNuevaResena: (resena: ProductReviewResponse) => void;
}) {
  const { isAuthenticated } = useAuth();

  const [rating, setRating] = useState<number | null>(5);
  const [comment, setComment] = useState("");
  const [reviewLoading, setReviewLoading] = useState(false);
  const [reviewError, setReviewError] = useState("");
  const [reviewSuccess, setReviewSuccess] = useState("");

  const handleSubmitReview = async (e: React.FormEvent) => {
    e.preventDefault();
    setReviewError("");
    setReviewSuccess("");
    setReviewLoading(true);
    try {
      const nueva = await api.reviews.create({
        product_id: productoId,
        rating: rating ?? 5,
        comment: comment.trim() || undefined,
      });
      onNuevaResena(nueva);
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

  return (
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
              {promedio.toFixed(1)}
            </Typography>
            <Rating value={promedio} precision={0.5} readOnly sx={{ my: 1.5 }} />
            <Typography variant="body2" color="text.secondary">
              Basado en {resenas.length} {resenas.length === 1 ? "reseña" : "reseñas"}
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
          {resenas.length === 0 ? (
            <Box sx={{ py: 8, textAlign: "center", color: "text.secondary" }}>
              <StarBorderIcon sx={{ fontSize: 48, color: "text.disabled", mb: 1.5 }} />
              <Typography sx={{ fontWeight: 700 }}>Aún no hay reseñas</Typography>
              <Typography variant="body2">
                Sé el primero en opinar sobre este producto.
              </Typography>
            </Box>
          ) : (
            <Stack spacing={2.5}>
              {resenas.map((review) => (
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
  );
}
