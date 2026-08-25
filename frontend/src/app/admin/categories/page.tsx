"use client";

import { useEffect, useState, useCallback } from "react";
import { api, type CategoryResponse } from "@/lib/api";
import ImageUploadField from "@/components/ui/ImageUploadField";

// MUI
import {
  Box,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Grid,
  TextField,
  Chip,
  IconButton,
  Tooltip,
  Card,
  CardContent,
  CardActions,
  CardMedia,
  Skeleton,
  Snackbar,
  Alert,
  Typography,
  alpha,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import CategoryIcon from "@mui/icons-material/Category";

export default function CategoriesPage() {
  const [categories, setCategories] = useState<CategoryResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editCat, setEditCat] = useState<CategoryResponse | null>(null);
  const [snack, setSnack] = useState<{ msg: string; severity: "success" | "error" } | null>(null);

  const fetchCategories = useCallback(async () => {
    setLoading(true);
    try {
      setCategories(await api.categories.list());
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchCategories(); }, [fetchCategories]);

  const showSnack = (msg: string, severity: "success" | "error" = "success") =>
    setSnack({ msg, severity });

  const handleSave = async (data: { name: string; slug: string; is_high_risk: boolean; image_url: string }) => {
    try {
      if (editCat) {
        await api.categories.update(editCat.id, data);
        showSnack("Categoría actualizada");
      } else {
        await api.categories.create(data);
        showSnack("Categoría creada");
      }
      setShowModal(false);
      setEditCat(null);
      fetchCategories();
    } catch (err: unknown) {
      showSnack(err instanceof Error ? err.message : "Error al guardar", "error");
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("¿Eliminar esta categoría?")) return;
    try {
      await api.categories.delete(id);
      showSnack("Categoría eliminada");
      fetchCategories();
    } catch (err: unknown) {
      showSnack(err instanceof Error ? err.message : "Error al eliminar", "error");
    }
  };

  return (
    <>
      {/* Header */}
      <div className="page-header">
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <Box>
            <Typography variant="h5" sx={{ fontWeight: 800 }}>Categorías</Typography>
            <Typography variant="body2" sx={{ color: "text.secondary", mt: 0.5 }}>
              {categories.length} categorías registradas
            </Typography>
          </Box>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => { setEditCat(null); setShowModal(true); }}
            sx={{ bgcolor: "#2563eb", textTransform: "none", fontWeight: 700, borderRadius: 2 }}
          >
            Nueva Categoría
          </Button>
        </Box>
      </div>

      <div className="page-body">
        <Grid container spacing={3}>
          {loading ? (
            [...Array(6)].map((_, i) => (
              <Grid size={{ xs: 12, sm: 6, md: 4 }} key={i}>
                <Skeleton variant="rounded" height={220} sx={{ borderRadius: 3 }} />
              </Grid>
            ))
          ) : categories.length === 0 ? (
            <Grid size={12}>
              <Box sx={{ textAlign: "center", py: 8, color: "text.disabled" }}>
                <CategoryIcon sx={{ fontSize: 64, mb: 2 }} />
                <Typography>No hay categorías todavía</Typography>
              </Box>
            </Grid>
          ) : (
            categories.map((cat) => (
              <Grid size={{ xs: 12, sm: 6, md: 4 }} key={cat.id}>
                <Card
                  elevation={0}
                  sx={{
                    borderRadius: 3,
                    border: "1px solid",
                    borderColor: cat.is_high_risk ? "error.main" : "divider",
                    overflow: "hidden",
                    transition: "all 0.2s",
                    "&:hover": {
                      boxShadow: "0 8px 24px -8px rgba(0,0,0,0.15)",
                      transform: "translateY(-2px)",
                    },
                  }}
                >
                  {/* Image */}
                  {cat.image_url ? (
                    <CardMedia
                      component="img"
                      height={140}
                      image={cat.image_url}
                      alt={cat.name}
                      sx={{ objectFit: "cover" }}
                    />
                  ) : (
                    <Box
                      sx={{
                        height: 140,
                        bgcolor: cat.is_high_risk ? alpha("#ef4444", 0.08) : "background.default",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        borderBottom: "1px solid",
                        borderColor: "divider",
                      }}
                    >
                      <Box sx={{ textAlign: "center", color: "text.disabled" }}>
                        <CategoryIcon sx={{ fontSize: 40, mb: 0.5 }} />
                        <Typography variant="caption" sx={{ display: "block" }}>Sin imagen</Typography>
                      </Box>
                    </Box>
                  )}

                  <CardContent sx={{ pb: 1 }}>
                    <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", mb: 1 }}>
                      <Typography variant="subtitle1" sx={{ fontWeight: 800, lineHeight: 1.2 }}>
                        {cat.name}
                      </Typography>
                    </Box>
                    <Box
                      sx={{
                        display: "inline-block",
                        bgcolor: "action.hover",
                        px: 1,
                        py: 0.2,
                        borderRadius: 1,
                        fontFamily: "monospace",
                        fontSize: "0.72rem",
                        color: "text.secondary",
                      }}
                    >
                      /{cat.slug}
                    </Box>
                  </CardContent>

                  <CardActions sx={{ px: 2, pb: 2, pt: 0, gap: 1 }}>
                    <Button
                      size="small"
                      startIcon={<EditIcon />}
                      variant="outlined"
                      onClick={() => { setEditCat(cat); setShowModal(true); }}
                      sx={{ textTransform: "none", fontWeight: 700, flex: 1, borderRadius: 2 }}
                    >
                      Editar
                    </Button>
                    <Tooltip title="Eliminar categoría">
                      <IconButton
                        size="small"
                        color="error"
                        onClick={() => handleDelete(cat.id)}
                        sx={{ "&:hover": { bgcolor: alpha("#ef4444", 0.08) } }}
                      >
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </CardActions>
                </Card>
              </Grid>
            ))
          )}
        </Grid>
      </div>

      {/* Modal */}
      {showModal && (
        <CategoryModal
          category={editCat}
          onSave={handleSave}
          onClose={() => { setShowModal(false); setEditCat(null); }}
        />
      )}

      {/* Snackbar */}
      <Snackbar
        open={!!snack}
        autoHideDuration={3000}
        onClose={() => setSnack(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
      >
        <Alert severity={snack?.severity} onClose={() => setSnack(null)} variant="filled">
          {snack?.msg}
        </Alert>
      </Snackbar>
    </>
  );
}

function CategoryModal({
  category,
  onSave,
  onClose,
}: {
  category: CategoryResponse | null;
  onSave: (data: { name: string; slug: string; is_high_risk: boolean; image_url: string }) => void;
  onClose: () => void;
}) {
  const [form, setForm] = useState({
    name: category?.name || "",
    slug: category?.slug || "",
    is_high_risk: category?.is_high_risk ?? false,
    image_url: category?.image_url || "",
  });

  const autoSlug = (name: string) =>
    name.toLowerCase()
      .normalize("NFD").replace(/[\u0300-\u036f]/g, "")
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/(^-|-$)/g, "");

  return (
    <Dialog open onClose={onClose} maxWidth="sm" fullWidth sx={{ '& .MuiDialog-paper': { borderRadius: 3 } }}>
      <DialogTitle sx={{ fontWeight: 800, pb: 1 }}>
        {category ? "Editar Categoría" : "Nueva Categoría"}
      </DialogTitle>
      <form onSubmit={(e) => { e.preventDefault(); onSave(form); }}>
        <DialogContent sx={{ pt: 1 }}>
          <Grid container spacing={2}>
            <Grid size={12}>
              <TextField
                label="Nombre"
                fullWidth
                required
                value={form.name}
                onChange={(e) => setForm({
                  ...form,
                  name: e.target.value,
                  slug: category ? form.slug : autoSlug(e.target.value),
                })}
              />
            </Grid>
            <Grid size={12}>
              <TextField
                label="Slug (URL)"
                fullWidth
                required
                value={form.slug}
                onChange={(e) => setForm({ ...form, slug: e.target.value })}
                slotProps={{ htmlInput: { pattern: "^[a-z0-9\\-]+$" } }}
                helperText="Solo minúsculas, números y guiones"
              />
            </Grid>
            <Grid size={12}>
              <ImageUploadField
                label="Imagen de la categoría"
                value={form.image_url}
                onChange={(url) => setForm({ ...form, image_url: url })}
              />
            </Grid>
            <Grid size={12}>
              {/* is_high_risk se mantiene internamente (relevante para el sistema antifraude) */}
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 3, gap: 1 }}>
          <Button onClick={onClose} variant="outlined" sx={{ textTransform: "none" }}>
            Cancelar
          </Button>
          <Button type="submit" variant="contained" sx={{ textTransform: "none", fontWeight: 700, bgcolor: "#2563eb" }}>
            {category ? "Guardar Cambios" : "Crear Categoría"}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}
