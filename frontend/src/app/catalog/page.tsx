"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { api, ProductResponse, CategoryResponse } from "@/lib/api";
import { useCart } from "@/lib/cart";
import Header from "@/components/ui/Header";
import ProductCard, { ProductCardSkeleton } from "@/components/ui/ProductCard";

// MUI
import {
  Box,
  Container,
  Typography,
  Grid,
  Card,
  CardMedia,
  CardContent,
  CardActions,
  Button,
  IconButton,
  Chip,
  Drawer,
  List,
  ListItemButton,
  ListItemText,
  Divider,
  TextField,
  InputAdornment,
  Skeleton,
  Pagination,
  Badge,
  alpha,
  useTheme,
  useMediaQuery,
} from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";
import ShoppingCartIcon from "@mui/icons-material/ShoppingCart";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import FilterListIcon from "@mui/icons-material/FilterList";
import CloseIcon from "@mui/icons-material/Close";
import TuneIcon from "@mui/icons-material/Tune";
import ImageNotSupportedIcon from "@mui/icons-material/ImageNotSupported";
import PackageIcon from "@mui/icons-material/Inventory2Outlined";
import { keyframes } from "@mui/system";

function CatalogContent() {
  const searchParams = useSearchParams();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("md"));

  const [products, setProducts] = useState<ProductResponse[]>([]);
  const [categories, setCategories] = useState<CategoryResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [categoryFilter, setCategoryFilter] = useState<number | null>(() => {
    const raw = Number(searchParams.get("category_id"));
    return Number.isInteger(raw) && raw > 0 ? raw : null;
  });
  const [search, setSearch] = useState(searchParams.get("q") || "");
  const [mobileFilterOpen, setMobileFilterOpen] = useState(false);

  useEffect(() => {
    api.categories.list().then(setCategories).catch(console.error);
  }, []);

  // El componente no se remonta al navegar dentro de /catalog, así que hay que
  // reaccionar a los cambios de la URL a mano.
  useEffect(() => {
    const raw = Number(searchParams.get("category_id"));
    setCategoryFilter(Number.isInteger(raw) && raw > 0 ? raw : null);
    setSearch(searchParams.get("q") || "");
    setPage(1);
  }, [searchParams]);

  useEffect(() => {
    const fetchProducts = async () => {
      setLoading(true);
      try {
        const res = await api.products.list({
          page,
          per_page: 12,
          search: search || undefined,
          category_id: categoryFilter || undefined,
          active_only: true,
        });
        setProducts(res.items);
        setTotal(res.total);
        setPages(res.pages);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    const t = setTimeout(fetchProducts, 300);
    return () => clearTimeout(t);
  }, [search, categoryFilter, page]);

  const handleCategoryChange = (id: number | null) => {
    setCategoryFilter(id);
    setPage(1);
    setMobileFilterOpen(false);
  };

  const handleSearch = (val: string) => {
    setSearch(val);
    setPage(1);
  };

  const FilterPanel = () => (
    <Box>
      {/* Search (mobile) */}
      {isMobile && (
        <TextField
          fullWidth
          size="small"
          placeholder="Buscar productos..."
          value={search}
          onChange={(e) => handleSearch(e.target.value)}
          sx={{ mb: 3 }}
          slotProps={{
            input: { startAdornment: <InputAdornment position="start"><SearchIcon sx={{ fontSize: 18 }} /></InputAdornment> }
          }}
        />
      )}

      <Typography variant="subtitle2" sx={{ fontWeight: 800, mb: 2, textTransform: "uppercase", letterSpacing: 1, fontSize: "0.72rem", color: "text.secondary" }}>
        Categorías
      </Typography>
      <List dense disablePadding>
        <ListItemButton
          selected={categoryFilter === null}
          onClick={() => handleCategoryChange(null)}
          sx={{
            borderRadius: 2,
            mb: 0.5,
            "&.Mui-selected": { bgcolor: alpha("#2563eb", 0.08), color: "#1e40af", fontWeight: 800 },
            "&.Mui-selected:hover": { bgcolor: alpha("#2563eb", 0.12) },
          }}
        >
          <ListItemText
            primary={<Typography sx={{ fontWeight: categoryFilter === null ? 800 : 500, fontSize: "0.875rem" }}>Todas las categorías</Typography>}
          />
          {categoryFilter === null && <CheckCircleIcon sx={{ fontSize: 16, color: "#2563eb" }} />}
        </ListItemButton>

        {categories.map((cat) => (
          <ListItemButton
            key={cat.id}
            selected={categoryFilter === cat.id}
            onClick={() => handleCategoryChange(cat.id)}
            sx={{
              borderRadius: 2,
              mb: 0.5,
              "&.Mui-selected": { bgcolor: alpha("#2563eb", 0.08), color: "#1e40af" },
              "&.Mui-selected:hover": { bgcolor: alpha("#2563eb", 0.12) },
            }}
          >
            <ListItemText
              primary={<Typography sx={{ fontWeight: categoryFilter === cat.id ? 800 : 500, fontSize: "0.875rem" }}>{cat.name}</Typography>}
            />
            <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
              {cat.is_high_risk && (
                <Chip label="⚠" size="small" color="error" variant="outlined" sx={{ fontSize: "0.6rem", height: 18, "& .MuiChip-label": { px: 0.5 } }} />
              )}
              {categoryFilter === cat.id && <CheckCircleIcon sx={{ fontSize: 16, color: "#2563eb" }} />}
            </Box>
          </ListItemButton>
        ))}
      </List>
    </Box>
  );

  return (
    <Container maxWidth="xl" sx={{ py: { xs: 3, md: 6 } }}>
      <Grid container spacing={4}>
        {/* Sidebar — desktop */}
        {!isMobile && (
          <Grid size={{ md: 3, lg: 2 }}>
            <Box
              sx={{
                position: "sticky",
                top: 100,
                bgcolor: "background.paper",
                borderRadius: 3,
                border: "1px solid",
                borderColor: "divider",
                p: 3,
              }}
            >
              <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 3 }}>
                <FilterListIcon sx={{ color: "#2563eb", fontSize: 20 }} />
                <Typography variant="subtitle1" sx={{ fontWeight: 800 }}>Filtros</Typography>
              </Box>
              <FilterPanel />
            </Box>
          </Grid>
        )}

        {/* Main content */}
        <Grid size={{ xs: 12, md: 9, lg: 10 }}>
          {/* Header bar */}
          <Box sx={{ display: "flex", flexDirection: { xs: "column", sm: "row" }, gap: 2, mb: 4, alignItems: { sm: "center" } }}>
            <Box sx={{ flexGrow: 1 }}>
              <Typography variant="h4" sx={{ fontWeight: 900, color: "text.primary", letterSpacing: "-0.02em", lineHeight: 1.15 }}>
                {search
                  ? `Resultados para "${search}"`
                  : categoryFilter
                  ? categories.find((c) => c.id === categoryFilter)?.name || "Productos"
                  : "Todos los Productos"}
              </Typography>
              {!loading && (
                <Typography variant="body2" sx={{ color: "text.secondary", mt: 0.5 }}>
                  {total} {total === 1 ? "producto" : "productos"} encontrados
                </Typography>
              )}
            </Box>

            <Box sx={{ display: "flex", gap: 2 }}>
              {/* Search — desktop */}
              {!isMobile && (
                <TextField
                  size="small"
                  placeholder="Buscar..."
                  value={search}
                  onChange={(e) => handleSearch(e.target.value)}
                  sx={{ minWidth: 240, bgcolor: "background.paper" }}
                  slotProps={{
                    input: { startAdornment: <InputAdornment position="start"><SearchIcon sx={{ fontSize: 18 }} /></InputAdornment> }
                  }}
                />
              )}
              {/* Filter button — mobile */}
              {isMobile && (
                <Button
                  variant="outlined"
                  startIcon={<TuneIcon />}
                  onClick={() => setMobileFilterOpen(true)}
                  sx={{ textTransform: "none", fontWeight: 700, borderRadius: 2 }}
                >
                  Filtros {categoryFilter ? `(1)` : ""}
                </Button>
              )}
            </Box>
          </Box>

          {/* Active filter chip */}
          {categoryFilter && (
            <Box sx={{ mb: 3 }}>
              <Chip
                label={categories.find((c) => c.id === categoryFilter)?.name}
                onDelete={() => handleCategoryChange(null)}
                deleteIcon={<CloseIcon />}
                variant="outlined"
                color="primary"
                sx={{ fontWeight: 700 }}
              />
            </Box>
          )}

          {/* Products Grid */}
          {loading ? (
            <Grid container spacing={3}>
              {[...Array(12)].map((_, i) => (
                <Grid size={{ xs: 6, sm: 4, lg: 3 }} key={i}>
                  <ProductCardSkeleton />
                </Grid>
              ))}
            </Grid>
          ) : products.length === 0 ? (
            <Box
              sx={{
                bgcolor: "background.paper",
                borderRadius: 4,
                p: { xs: 4, md: 8 },
                textAlign: "center",
                border: "1px dashed",
                borderColor: "divider",
              }}
            >
              <PackageIcon sx={{ fontSize: 72, color: "grey.300", mb: 2 }} />
              <Typography variant="h5" sx={{ fontWeight: 800, color: "text.primary", mb: 1 }}>
                Sin resultados
              </Typography>
              <Typography variant="body2" sx={{ color: "text.secondary", mb: 4, maxWidth: 400, mx: "auto" }}>
                No encontramos productos que coincidan con tu búsqueda. Intenta con otros términos o categorías.
              </Typography>
              <Button
                variant="contained"
                onClick={() => { setSearch(""); handleCategoryChange(null); }}
                sx={{ textTransform: "none", fontWeight: 700, bgcolor: "#2563eb", borderRadius: 2 }}
              >
                Ver todos los productos
              </Button>
            </Box>
          ) : (
            <>
              <Grid container spacing={3}>
                {products.map((p, i) => (
                  <Grid size={{ xs: 6, sm: 4, lg: 3 }} key={p.id}>
                    <ProductCard product={p} index={i} />
                  </Grid>
                ))}
              </Grid>

              {/* Pagination */}
              {pages > 1 && (
                <Box sx={{ display: "flex", justifyContent: "center", mt: 6 }}>
                  <Pagination
                    count={pages}
                    page={page}
                    onChange={(_, v) => { setPage(v); window.scrollTo({ top: 0, behavior: "smooth" }); }}
                    color="primary"
                    shape="rounded"
                    size={isMobile ? "small" : "medium"}
                  />
                </Box>
              )}
            </>
          )}
        </Grid>
      </Grid>

      {/* Mobile Filter Drawer */}
      <Drawer
        anchor="left"
        open={mobileFilterOpen}
        onClose={() => setMobileFilterOpen(false)}
        sx={{ '& .MuiDrawer-paper': { width: 300, p: 3 } }}
      >
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 3 }}>
          <Typography variant="h6" sx={{ fontWeight: 800 }}>Filtros</Typography>
          <IconButton onClick={() => setMobileFilterOpen(false)}>
            <CloseIcon />
          </IconButton>
        </Box>
        <Divider sx={{ mb: 3 }} />
        <FilterPanel />
      </Drawer>
    </Container>
  );
}

export default function CatalogPage() {
  return (
    <Box sx={{ minHeight: "100dvh", display: "flex", flexDirection: "column", bgcolor: "background.default" }}>
      <Header />
      <Suspense
        fallback={
          <Container maxWidth="xl" sx={{ py: 6 }}>
            <Grid container spacing={3}>
              {[...Array(12)].map((_, i) => (
                <Grid size={{ xs: 6, sm: 4, md: 3 }} key={i}>
                  <ProductCardSkeleton />
                </Grid>
              ))}
            </Grid>
          </Container>
        }
      >
        <CatalogContent />
      </Suspense>
    </Box>
  );
}
