"use client";

import { useEffect, useState, useCallback } from "react";
import { api, type ProductResponse, type CategoryResponse, type ProductCreate } from "@/lib/api";
import ImageUploadField from "@/components/ui/ImageUploadField";

// MUI
import {
  Box,
  Button,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Paper,
  Chip,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Grid,
  Avatar,
  FormControlLabel,
  Switch,
  Pagination,
  Skeleton,
  Snackbar,
  Alert,
  Typography,
  InputAdornment,
  alpha,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import EditIcon from "@mui/icons-material/Edit";
import SearchIcon from "@mui/icons-material/Search";
import BlockIcon from "@mui/icons-material/Block";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import ImageNotSupportedIcon from "@mui/icons-material/ImageNotSupported";

export default function ProductsPage() {
  const [products, setProducts] = useState<ProductResponse[]>([]);
  const [categories, setCategories] = useState<CategoryResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<number | "">("");
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editProduct, setEditProduct] = useState<ProductResponse | null>(null);
  const [snack, setSnack] = useState<{ msg: string; severity: "success" | "error" } | null>(null);

  const fetchProducts = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.products.list({
        page,
        per_page: 10,
        search: search || undefined,
        category_id: categoryFilter || undefined,
        active_only: false,
      });
      setProducts(data.items);
      setTotal(data.total);
      setPages(data.pages);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [page, search, categoryFilter]);

  useEffect(() => { fetchProducts(); }, [fetchProducts]);
  useEffect(() => { api.categories.list().then(setCategories).catch(console.error); }, []);

  const showSnack = (msg: string, severity: "success" | "error" = "success") => {
    setSnack({ msg, severity });
  };

  const handleToggle = async (id: string) => {
    try {
      await api.products.toggle(id);
      showSnack("Estado actualizado");
      fetchProducts();
    } catch {
      showSnack("Error al actualizar", "error");
    }
  };

  const handleSave = async (data: ProductCreate) => {
    try {
      if (editProduct) {
        await api.products.update(editProduct.id, data);
        showSnack("Producto actualizado");
      } else {
        await api.products.create(data);
        showSnack("Producto creado");
      }
      setShowModal(false);
      setEditProduct(null);
      fetchProducts();
    } catch (err: unknown) {
      showSnack(err instanceof Error ? err.message : "Error al guardar", "error");
    }
  };

  return (
    <>
      {/* Header */}
      <div className="page-header">
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <Box>
            <Typography variant="h5" sx={{ fontWeight: 800 }}>Productos</Typography>
            <Typography variant="body2" sx={{ color: "text.secondary", mt: 0.5 }}>
              {total} productos registrados
            </Typography>
          </Box>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => { setEditProduct(null); setShowModal(true); }}
            sx={{ bgcolor: "#0C3A6E", textTransform: "none", fontWeight: 700, borderRadius: 2 }}
          >
            Nuevo Producto
          </Button>
        </Box>
      </div>

      <div className="page-body">
        {/* Filters */}
        <Box sx={{ display: "flex", gap: 2, mb: 3, flexWrap: "wrap" }}>
          <TextField
            size="small"
            placeholder="Buscar productos..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            sx={{ minWidth: 280, bgcolor: "background.paper", borderRadius: 1 }}
            slotProps={{ input: { startAdornment: <InputAdornment position="start"><SearchIcon sx={{ fontSize: 18, color: "text.secondary" }} /></InputAdornment> } }}
          />
          <FormControl size="small" sx={{ minWidth: 200, bgcolor: "background.paper", borderRadius: 1 }}>
            <InputLabel>Categoría</InputLabel>
            <Select
              label="Categoría"
              value={categoryFilter}
              onChange={(e) => { setCategoryFilter(e.target.value as number | ""); setPage(1); }}
            >
              <MenuItem value="">Todas</MenuItem>
              {categories.map((c) => (
                <MenuItem key={c.id} value={c.id}>{c.name}</MenuItem>
              ))}
            </Select>
          </FormControl>
        </Box>

        {/* Table */}
        <Paper elevation={0} sx={{ border: "1px solid", borderColor: "divider", borderRadius: 2, overflow: "hidden", bgcolor: "background.paper" }}>
          <Table>
            <TableHead sx={{ bgcolor: "background.default" }}>
              <TableRow>
                <TableCell sx={{ fontWeight: 700, fontSize: "0.75rem", textTransform: "uppercase", color: "text.secondary" }}>Producto</TableCell>
                <TableCell sx={{ fontWeight: 700, fontSize: "0.75rem", textTransform: "uppercase", color: "text.secondary" }}>Categoría</TableCell>
                <TableCell sx={{ fontWeight: 700, fontSize: "0.75rem", textTransform: "uppercase", color: "text.secondary" }}>Precio (S/)</TableCell>
                <TableCell sx={{ fontWeight: 700, fontSize: "0.75rem", textTransform: "uppercase", color: "text.secondary" }}>Stock</TableCell>
                <TableCell sx={{ fontWeight: 700, fontSize: "0.75rem", textTransform: "uppercase", color: "text.secondary" }}>Estado</TableCell>
                <TableCell align="right" sx={{ fontWeight: 700, fontSize: "0.75rem", textTransform: "uppercase", color: "text.secondary" }}>Acciones</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {loading ? (
                [...Array(5)].map((_, i) => (
                  <TableRow key={i}>
                    {[...Array(6)].map((_, j) => (
                      <TableCell key={j}><Skeleton height={40} /></TableCell>
                    ))}
                  </TableRow>
                ))
              ) : products.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} align="center" sx={{ py: 6, color: "text.disabled" }}>
                    No se encontraron productos
                  </TableCell>
                </TableRow>
              ) : (
                products.map((p) => (
                  <TableRow key={p.id} hover sx={{ "&:last-child td": { borderBottom: 0 } }}>
                    {/* Producto */}
                    <TableCell>
                      <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
                        <Avatar
                          src={p.image_url || ""}
                          variant="rounded"
                          sx={{ width: 44, height: 44, bgcolor: "action.hover", border: "1px solid", borderColor: "divider" }}
                        >
                          <ImageNotSupportedIcon sx={{ fontSize: 20, color: "text.disabled" }} />
                        </Avatar>
                        <Box>
                          <Typography variant="body2" sx={{ fontWeight: 700, lineHeight: 1.2 }}>
                            {p.name}
                          </Typography>
                          <Typography variant="caption" sx={{ color: "text.secondary", display: "-webkit-box", WebkitLineClamp: 1, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
                            {p.description || "Sin descripción"}
                          </Typography>
                        </Box>
                      </Box>
                    </TableCell>
                    {/* Categoría */}
                    <TableCell>
                      <Chip
                        label={p.category?.name || "N/A"}
                        size="small"
                        color="default"
                        variant="outlined"
                        sx={{ fontSize: "0.7rem", fontWeight: 700 }}
                      />
                    </TableCell>
                    {/* Precio */}
                    <TableCell>
                      <Box>
                        {p.discount_price ? (
                          <>
                            <Typography variant="caption" sx={{ color: "text.disabled", textDecoration: "line-through", display: "block", lineHeight: 1 }}>
                              S/{p.price.toFixed(2)}
                            </Typography>
                            <Typography variant="body2" sx={{ fontWeight: 700, fontFamily: "monospace", color: "error.main" }}>
                              S/{p.discount_price.toFixed(2)}
                            </Typography>
                          </>
                        ) : (
                          <Typography variant="body2" sx={{ fontWeight: 700, fontFamily: "monospace" }}>
                            S/{p.price.toFixed(2)}
                          </Typography>
                        )}
                      </Box>
                    </TableCell>
                    {/* Stock */}
                    <TableCell>
                      <Chip
                        label={`${p.stock} uds`}
                        size="small"
                        color={p.stock > 10 ? "success" : p.stock > 0 ? "warning" : "error"}
                        variant="filled"
                        sx={{ fontSize: "0.7rem", fontWeight: 700 }}
                      />
                    </TableCell>
                    {/* Estado */}
                    <TableCell>
                      <Chip
                        label={p.is_active ? "Activo" : "Inactivo"}
                        size="small"
                        color={p.is_active ? "success" : "default"}
                        variant="outlined"
                        sx={{ fontSize: "0.7rem", fontWeight: 700 }}
                      />
                    </TableCell>
                    {/* Acciones */}
                    <TableCell align="right">
                      <Box sx={{ display: "flex", gap: 0.5, justifyContent: "flex-end" }}>
                        <Tooltip title="Editar">
                          <IconButton
                            size="small"
                            onClick={() => { setEditProduct(p); setShowModal(true); }}
                            sx={{ color: "#0C3A6E", "&:hover": { bgcolor: alpha("#0C3A6E", 0.08) } }}
                          >
                            <EditIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title={p.is_active ? "Desactivar" : "Activar"}>
                          <IconButton
                            size="small"
                            onClick={() => handleToggle(p.id)}
                            sx={{ color: p.is_active ? "error.main" : "success.main" }}
                          >
                            {p.is_active ? <BlockIcon fontSize="small" /> : <CheckCircleIcon fontSize="small" />}
                          </IconButton>
                        </Tooltip>
                      </Box>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </Paper>

        {/* Pagination */}
        {pages > 1 && (
          <Box sx={{ display: "flex", justifyContent: "center", mt: 3 }}>
            <Pagination
              count={pages}
              page={page}
              onChange={(_, v) => setPage(v)}
              color="primary"
              shape="rounded"
            />
          </Box>
        )}
      </div>

      {/* Modal */}
      {showModal && (
        <ProductModal
          product={editProduct}
          categories={categories}
          onSave={handleSave}
          onClose={() => { setShowModal(false); setEditProduct(null); }}
        />
      )}

      {/* Snackbar */}
      <Snackbar
        open={!!snack}
        autoHideDuration={3000}
        onClose={() => setSnack(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
      >
        <Alert severity={snack?.severity} onClose={() => setSnack(null)} variant="filled" sx={{ width: "100%" }}>
          {snack?.msg}
        </Alert>
      </Snackbar>
    </>
  );
}

function ProductModal({
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
