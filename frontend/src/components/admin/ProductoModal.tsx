"use client";

/**
 * Formulario para crear y editar un producto del catálogo.
 *
 * Vivía dentro de `app/admin/products/page.tsx`, que así mezclaba la
 * pantalla con el formulario. Separado, cada archivo hace una sola cosa.
 */

import { useState } from "react";
import { type ProductResponse, type CategoryResponse, type ProductCreate } from "@/lib/api";
import ImageUploadField from "@/components/ui/ImageUploadField";
import {
  Button,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Grid,
  FormControlLabel,
  Switch,
} from "@mui/material";

export default function ProductModal({
  product,
  categories,
  onSave,
  onClose,
}: {
  product: ProductResponse | null;
  categories: CategoryResponse[];
  onSave: (data: ProductCreate) => void;
  onClose: () => void;
}) {
  const [form, setForm] = useState<ProductCreate>({
    name: product?.name || "",
    description: product?.description || "",
    price: product?.price || 0,
    discount_price: product?.discount_price ?? null,
    stock: product?.stock || 0,
    image_url: product?.image_url || "",
    category_id: product?.category_id || (categories[0]?.id ?? 1),
    is_active: product?.is_active ?? true,
  });

  const set = (field: keyof ProductCreate, value: unknown) =>
    setForm((f) => ({ ...f, [field]: value }));

  return (
    <Dialog open onClose={onClose} maxWidth="sm" fullWidth sx={{ '& .MuiDialog-paper': { borderRadius: 3 } }}>
      <DialogTitle sx={{ fontWeight: 800, pb: 1 }}>
        {product ? "Editar Producto" : "Nuevo Producto"}
      </DialogTitle>
      <form onSubmit={(e) => { e.preventDefault(); onSave(form); }}>
        <DialogContent sx={{ pt: 1 }}>
          <Grid container spacing={2}>
            <Grid size={12}>
              <TextField
                label="Nombre del producto"
                fullWidth
                required
                value={form.name}
                onChange={(e) => set("name", e.target.value)}
              />
            </Grid>
            <Grid size={12}>
              <TextField
                label="Descripción"
                fullWidth
                multiline
                rows={2}
                value={form.description || ""}
                onChange={(e) => set("description", e.target.value)}
              />
            </Grid>
            <Grid size={6}>
              <TextField
                label="Precio (S/)"
                type="number"
                fullWidth
                required
                slotProps={{ htmlInput: { min: 0, step: 0.01 } }}
                value={form.price}
                onChange={(e) => set("price", Number(e.target.value))}
              />
            </Grid>
            <Grid size={6}>
              <TextField
                label="Precio Oferta (S/) — opcional"
                type="number"
                fullWidth
                slotProps={{ htmlInput: { min: 0, step: 0.01 } }}
                value={form.discount_price ?? ""}
                onChange={(e) => set("discount_price", e.target.value === "" ? null : Number(e.target.value))}
                helperText="Si hay oferta, pon el precio con descuento"
              />
            </Grid>
            <Grid size={6}>
              <TextField
                label="Stock"
                type="number"
                fullWidth
                required
                slotProps={{ htmlInput: { min: 0 } }}
                value={form.stock}
                onChange={(e) => set("stock", Number(e.target.value))}
              />
            </Grid>
            <Grid size={12}>
              <FormControl fullWidth>
                <InputLabel>Categoría</InputLabel>
                <Select
                  label="Categoría"
                  value={form.category_id}
                  onChange={(e) => set("category_id", Number(e.target.value))}
                >
                  {categories.map((c) => (
                    <MenuItem key={c.id} value={c.id}>
                      {c.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid size={12}>
              <ImageUploadField
                label="Imagen del producto"
                value={form.image_url || ""}
                onChange={(url) => set("image_url", url)}
              />
            </Grid>
            <Grid size={12}>
              <FormControlLabel
                control={
                  <Switch
                    checked={form.is_active}
                    onChange={(e) => set("is_active", e.target.checked)}
                    color="success"
                  />
                }
                label="Producto activo (visible en la tienda)"
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 3, gap: 1 }}>
          <Button onClick={onClose} variant="outlined" sx={{ textTransform: "none" }}>
            Cancelar
          </Button>
          <Button type="submit" variant="contained" sx={{ textTransform: "none", fontWeight: 700, bgcolor: "#0C3A6E" }}>
            {product ? "Guardar Cambios" : "Crear Producto"}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}
