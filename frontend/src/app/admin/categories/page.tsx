"use client";

import { useEffect, useState, useCallback } from "react";
import CategoryModal from "@/components/admin/CategoriaModal";
import { api, type CategoryResponse } from "@/lib/api";

// MUI
import {
  Box,
  Button,
  Grid,
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
import CategoryIcon from "@mui/icons-material/Category";

export default function CategoriesPage() {
  const [categories, setCategories] = useState<CategoryResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editCat, setEditCat] = useState<CategoryResponse | null>(null);
  const [snack, setSnack] = useState<{ msg: string; severity: "success" | "error" } | null>(null);

  // La carga inicial va dentro del efecto y guarda el resultado en el callback
  // de la promesa. Dos razones: el estado de `loading` ya empieza en true, asi
  // que marcarlo otra vez encadenaria un render de mas; y el interruptor
  // `vigente` descarta la respuesta si el componente se desmonto mientras el
  // servidor contestaba.
  useEffect(() => {
    let vigente = true;
    api.categories
      .list()
      .then((datos) => {
        if (!vigente) return;
        setCategories(datos);
        setLoading(false);
      })
      .catch((err) => {
        if (!vigente) return;
        console.error(err);
        setLoading(false);
      });
    return () => { vigente = false; };
  }, []);

  // Las recargas que vienen de guardar o borrar una categoria si muestran el
  // indicador de carga: ahi el usuario acaba de pedir la accion.
  const recargarCategorias = useCallback(async () => {
    setLoading(true);
    try {
      setCategories(await api.categories.list());
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);


  const showSnack = (msg: string, severity: "success" | "error" = "success") =>
    setSnack({ msg, severity });

  const handleSave = async (data: { name: string; slug: string; is_high_risk: boolean; image_url: string; parent_id: number | null }) => {
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
      recargarCategorias();
    } catch (err: unknown) {
      showSnack(err instanceof Error ? err.message : "Error al guardar", "error");
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("¿Eliminar esta categoría?")) return;
    try {
      await api.categories.delete(id);
      showSnack("Categoría eliminada");
      recargarCategorias();
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
            sx={{ bgcolor: "#0C3A6E", textTransform: "none", fontWeight: 700, borderRadius: 2 }}
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
                    {cat.parent_id !== null && (
                      <Typography variant="caption" sx={{ display: "block", color: "text.secondary", mb: 1 }}>
                        Subcategoría de{" "}
                        <strong>
                          {categories.find((p) => p.id === cat.parent_id)?.name ?? "—"}
                        </strong>
                      </Typography>
                    )}
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
          categories={categories}
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
