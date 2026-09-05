"use client";

/**
 * Portada: la rejilla de productos.
 *
 * El título dice "Novedades" y no "Lo más vendido" porque es lo que la consulta
 * pide de verdad: el listado ordenado por fecha. La tienda no lleva la cuenta
 * de unidades vendidas, así que el rótulo anterior prometía un criterio que
 * nadie calculaba.
 */

import { Alert, Box, Button, Container, Grid, Typography } from "@mui/material";
import RefreshIcon from "@mui/icons-material/Refresh";
import ProductCard, { ProductCardSkeleton } from "@/components/ui/ProductCard";
import SectionHeading from "@/components/home/SectionHeading";
import type { ProductResponse } from "@/lib/api";

export default function FeaturedProducts({
  products,
  loading,
  failed,
  slow,
  cantidad,
  onReintentar,
  onAgregado,
}: {
  products: ProductResponse[];
  loading: boolean;
  failed: boolean;
  /** El backend gratuito duerme: avisamos si la primera carga se alarga. */
  slow: boolean;
  cantidad: number;
  onReintentar: () => void;
  onAgregado: (product: ProductResponse) => void;
}) {
  return (
    // El espacio superior es propio y no heredado de la sección de arriba:
    // cuando el catálogo no responde, esa sección desaparece y ésta quedaría
    // pegada al bloque azul.
    <Container
      component="section"
      maxWidth="lg"
      sx={{ pt: { xs: 6, md: 8 }, pb: { xs: 6, md: 9 } }}
    >
      <SectionHeading title="Novedades" action={{ label: "Ver todo", href: "/catalog" }} />

      {slow && !failed && (
        <Alert severity="info" sx={{ mb: 3 }}>
          Estamos activando el servidor. La primera carga puede tardar hasta 50 segundos.
        </Alert>
      )}

      {failed ? (
        <Box
          sx={{
            textAlign: "center",
            py: { xs: 5, md: 7 },
            px: 2,
            border: "1px dashed",
            borderColor: "divider",
          }}
        >
          <Typography sx={{ fontWeight: 700, fontSize: "1.05rem" }}>
            No pudimos cargar los productos
          </Typography>
          <Typography color="text.secondary" sx={{ mt: 1, mb: 3 }}>
            El servidor puede estar despertando. Vuelve a intentarlo en unos segundos.
          </Typography>
          <Button variant="contained" startIcon={<RefreshIcon />} onClick={onReintentar}>
            Reintentar
          </Button>
        </Box>
      ) : (
        <Grid container spacing={{ xs: 1.5, sm: 2 }}>
          {loading
            ? Array.from({ length: cantidad }).map((_, i) => (
                <Grid size={{ xs: 6, md: 3 }} key={`p-sk-${i}`}>
                  <ProductCardSkeleton />
                </Grid>
              ))
            : products.map((p, i) => (
                <Grid size={{ xs: 6, md: 3 }} key={p.id}>
                  <ProductCard product={p} index={i} onAdded={onAgregado} />
                </Grid>
              ))}
        </Grid>
      )}
    </Container>
  );
}
