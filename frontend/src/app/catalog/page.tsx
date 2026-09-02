"use client";

import { useEffect, useMemo, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { api, ProductResponse, CategoryResponse } from "@/lib/api";
import Header from "@/components/ui/Header";
import ProductCard, { ProductCardSkeleton } from "@/components/ui/ProductCard";

// MUI
import {
  Box,
  Container,
  Typography,
  Grid,
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
  Pagination,
  alpha,
  useTheme,
  useMediaQuery,
} from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import FilterListIcon from "@mui/icons-material/FilterList";
import CloseIcon from "@mui/icons-material/Close";
import TuneIcon from "@mui/icons-material/Tune";
import PackageIcon from "@mui/icons-material/Inventory2Outlined";

/**
 * Panel de filtros del catálogo.
 *
 * Vive fuera de CatalogContent a propósito: definido dentro del render, cada
 * repintado creaba un componente distinto, React desmontaba el anterior y el
 * panel perdía su estado interno (y el foco del buscador en móvil).
 */
function FilterPanel({
  isMobile,
  search,
  categories,
  categoryFilter,
  onSearch,
  onCategoryChange,
}: {
  isMobile: boolean;
  search: string;
  categories: CategoryResponse[];
  categoryFilter: number | null;
  onSearch: (valor: string) => void;
  onCategoryChange: (id: number | null) => void;
}) {
  return (

    <Box>
      {/* Search (mobile) */}
      {isMobile && (
        <TextField
          fullWidth
          size="small"
          placeholder="Buscar productos..."
          value={search}
          onChange={(e) => onSearch(e.target.value)}
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
          onClick={() => onCategoryChange(null)}
          sx={{
            borderRadius: 2,
            mb: 0.5,
            "&.Mui-selected": { bgcolor: alpha("#0C3A6E", 0.08), color: "#082A52", fontWeight: 800 },
            "&.Mui-selected:hover": { bgcolor: alpha("#0C3A6E", 0.12) },
          }}
        >
          <ListItemText
            primary={<Typography sx={{ fontWeight: categoryFilter === null ? 800 : 500, fontSize: "0.875rem" }}>Todas las categorías</Typography>}
          />
          {categoryFilter === null && <CheckCircleIcon sx={{ fontSize: 16, color: "#0C3A6E" }} />}
        </ListItemButton>

        {categories.map((cat) => (
          <ListItemButton
            key={cat.id}
            selected={categoryFilter === cat.id}
            onClick={() => onCategoryChange(cat.id)}
            sx={{
              borderRadius: 2,
              mb: 0.5,
              "&.Mui-selected": { bgcolor: alpha("#0C3A6E", 0.08), color: "#082A52" },
              "&.Mui-selected:hover": { bgcolor: alpha("#0C3A6E", 0.12) },
            }}
          >
            <ListItemText
              primary={<Typography sx={{ fontWeight: categoryFilter === cat.id ? 800 : 500, fontSize: "0.875rem" }}>{cat.name}</Typography>}
            />
            <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
              {cat.is_high_risk && (
                <Chip label="⚠" size="small" color="error" variant="outlined" sx={{ fontSize: "0.6rem", height: 18, "& .MuiChip-label": { px: 0.5 } }} />
              )}
              {categoryFilter === cat.id && <CheckCircleIcon sx={{ fontSize: 16, color: "#0C3A6E" }} />}
            </Box>
          </ListItemButton>
        ))}
      </List>
    </Box>
  );
}

function CatalogContent() {
  const searchParams = useSearchParams();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("md"));

  const [products, setProducts] = useState<ProductResponse[]>([]);
  const [categories, setCategories] = useState<CategoryResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [pages, setPages] = useState(1);
  const [mobileFilterOpen, setMobileFilterOpen] = useState(false);

  useEffect(() => {
    api.categories.list().then(setCategories).catch(console.error);
  }, []);

  // Los filtros tienen dos orígenes: la URL (el menú del header entra con
  // ?category_id=…, y el buscador con ?q=…) y lo que la persona toca aquí
  // dentro. El componente no se remonta al navegar dentro de /catalog, así
  // que antes hacía falta un efecto que copiara la URL al estado cada vez que
  // cambiaba; ese efecto encadenaba un render y, entre uno y otro, la lista se
  // pedía con los filtros viejos.
  //
  // Ahora no se copia nada: lo que manda es la URL, y encima de ella se aplica
  // el ajuste local, que solo vale mientras la URL siga siendo la misma. Al
  // navegar a otra dirección el ajuste deja de coincidir y los filtros
  // vuelven solos a lo que dice la URL, con la paginación en 1.
  const claveUrl = searchParams.toString();

  const desdeUrl = useMemo(() => {
    const raw = Number(searchParams.get("category_id"));
    return {
      categoria: Number.isInteger(raw) && raw > 0 ? raw : null,
      busqueda: searchParams.get("q") || "",
    };
  }, [searchParams]);

  const [ajuste, setAjuste] = useState<{
    clave: string;
    categoria: number | null;
    busqueda: string;
    pagina: number;
  } | null>(null);

  const vigente = ajuste && ajuste.clave === claveUrl ? ajuste : null;
  const categoryFilter = vigente ? vigente.categoria : desdeUrl.categoria;
  const search = vigente ? vigente.busqueda : desdeUrl.busqueda;
  const page = vigente ? vigente.pagina : 1;

  const ajustarFiltros = (cambios: Partial<Omit<NonNullable<typeof ajuste>, "clave">>) =>
    setAjuste({
      clave: claveUrl,
      categoria: categoryFilter,
      busqueda: search,
      pagina: page,
      ...cambios,
    });

  const setPage = (valor: number) => ajustarFiltros({ pagina: valor });

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
    ajustarFiltros({ categoria: id, pagina: 1 });
    setMobileFilterOpen(false);
  };

  const handleSearch = (val: string) => {
    ajustarFiltros({ busqueda: val, pagina: 1 });
  };


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
                <FilterListIcon sx={{ color: "#0C3A6E", fontSize: 20 }} />
                <Typography variant="subtitle1" sx={{ fontWeight: 800 }}>Filtros</Typography>
              </Box>
              <FilterPanel
                isMobile={isMobile}
                search={search}
                categories={categories}
                categoryFilter={categoryFilter}
                onSearch={handleSearch}
                onCategoryChange={handleCategoryChange}
              />
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
                onClick={() => ajustarFiltros({ busqueda: "", categoria: null, pagina: 1 })}
                sx={{ textTransform: "none", fontWeight: 700, bgcolor: "#0C3A6E", borderRadius: 2 }}
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
        <FilterPanel
          isMobile={isMobile}
          search={search}
          categories={categories}
          categoryFilter={categoryFilter}
          onSearch={handleSearch}
          onCategoryChange={handleCategoryChange}
        />
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
