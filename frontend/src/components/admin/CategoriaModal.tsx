"use client";

/**
 * Formulario para crear y editar una categoría del catálogo.
 *
 * Vivía dentro de `app/admin/categories/page.tsx`, que así mezclaba la
 * pantalla con el formulario. Separado, cada archivo hace una sola cosa.
 */

import { useMemo, useState } from "react";
import { type CategoryResponse } from "@/lib/api";
import ImageUploadField from "@/components/ui/ImageUploadField";
import {
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  Grid,
  InputLabel,
  MenuItem,
  Select,
  TextField,
} from "@mui/material";

export type CategoryFormData = {
  name: string;
  slug: string;
  is_high_risk: boolean;
  image_url: string;
  parent_id: number | null;
};

export default function CategoryModal({
  category,
  categories,
  onSave,
  onClose,
}: {
  category: CategoryResponse | null;
  categories: CategoryResponse[];
  onSave: (data: CategoryFormData) => void;
  onClose: () => void;
}) {
  const [form, setForm] = useState<CategoryFormData>({
    name: category?.name || "",
    slug: category?.slug || "",
    is_high_risk: category?.is_high_risk ?? false,
    image_url: category?.image_url || "",
    parent_id: category?.parent_id ?? null,
  });

  // Solo las raíces pueden ser padre (el árbol es de dos niveles). Y una
  // categoría no puede ser su propia madre.
  const posiblesPadres = useMemo(
    () =>
      categories.filter(
        (c) => c.parent_id === null && c.id !== category?.id
      ),
    [categories, category]
  );

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
              <FormControl fullWidth>
                <InputLabel>Categoría padre</InputLabel>
                <Select
                  label="Categoría padre"
                  value={form.parent_id === null ? "" : String(form.parent_id)}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      parent_id: e.target.value === "" ? null : Number(e.target.value),
                    })
                  }
                >
                  <MenuItem value="">
                    <em>Ninguna (es una categoría principal)</em>
                  </MenuItem>
                  {posiblesPadres.map((c) => (
                    <MenuItem key={c.id} value={String(c.id)}>
                      {c.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
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
          <Button type="submit" variant="contained" sx={{ textTransform: "none", fontWeight: 700, bgcolor: "#0C3A6E" }}>
            {category ? "Guardar Cambios" : "Crear Categoría"}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}
