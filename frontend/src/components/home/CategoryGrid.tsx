"use client";

/**
 * Portada: acceso a las familias del catálogo.
 *
 * Enseña solo las primeras categorías raíz, en el mismo orden que el menú de la
 * cabecera. Antes se volcaba aquí la lista completa que devuelve el backend
 * —raíces y subcategorías juntas, cerca de cuarenta cajas— y la portada
 * terminaba siendo un índice del catálogo en vez de una entrada a él. Quien
 * quiera el detalle (DDR4, Intel Core i7, SSD NVMe) lo encuentra en el
 * catálogo, que es donde sirve para filtrar.
 */

import Link from "next/link";
import { Box, Container, Grid, Typography } from "@mui/material";
import SectionHeading from "@/components/home/SectionHeading";
import { categoriasRaiz } from "@/lib/categorias";
import type { CategoryResponse } from "@/lib/api";
import type { SvgIconComponent } from "@mui/icons-material";

import MemoryIcon from "@mui/icons-material/Memory";
import VideogameAssetIcon from "@mui/icons-material/VideogameAsset";
import DeveloperBoardIcon from "@mui/icons-material/DeveloperBoard";
import StorageIcon from "@mui/icons-material/Storage";
import MonitorIcon from "@mui/icons-material/Monitor";
import KeyboardIcon from "@mui/icons-material/Keyboard";
import PowerIcon from "@mui/icons-material/Power";
import HeadphonesIcon from "@mui/icons-material/Headphones";
import RouterIcon from "@mui/icons-material/Router";
import CategoryIcon from "@mui/icons-material/Category";

/** Cuántas familias caben sin que la fila deje de leerse de un vistazo. */
const VISIBLES = 6;

const ICONOS: Record<string, SvgIconComponent> = {
  procesadores: MemoryIcon,
  "tarjetas-de-video": VideogameAssetIcon,
  "memorias-ram": DeveloperBoardIcon,
  almacenamiento: StorageIcon,
  monitores: MonitorIcon,
  perifericos: KeyboardIcon,
  "cases-y-fuentes": PowerIcon,
  "placas-madre": DeveloperBoardIcon,
  audio: HeadphonesIcon,
  redes: RouterIcon,
};

const CAJA = {
  height: { xs: 116, md: 132 },
  border: "1px solid",
  borderColor: "divider",
  bgcolor: "background.paper",
  display: "flex",
  flexDirection: "column" as const,
  alignItems: "center",
  justifyContent: "center",
  gap: 0.9,
  px: 1.5,
  textAlign: "center" as const,
};

export default function CategoryGrid({
  categories,
  loading,
}: {
  categories: CategoryResponse[];
  loading: boolean;
}) {
  const visibles = categoriasRaiz(categories).slice(0, VISIBLES);

  // Sin categorías que enseñar la sección sobra: una fila de cajas vacías es
  // peor que no tener sección.
  if (!loading && visibles.length === 0) return null;

  return (
    <Container component="section" maxWidth="lg" sx={{ pt: { xs: 6, md: 8 } }}>
      <SectionHeading
        title="Categorías"
        action={{ label: "Ver todo el catálogo", href: "/catalog" }}
      />

      <Grid container spacing={{ xs: 1.5, md: 2 }}>
        {/* El esqueleto trae tantas casillas como tendrá la fila cargada, así
            que el contenido de abajo no salta cuando llega la respuesta. */}
        {(loading ? Array.from({ length: VISIBLES }) : visibles).map((cat, i) => {
          if (loading || !cat) {
            return (
              <Grid size={{ xs: 6, sm: 4, md: 2 }} key={`cat-sk-${i}`}>
                <Box sx={{ ...CAJA, bgcolor: "action.hover", borderColor: "transparent" }} />
              </Grid>
            );
          }

          const c = cat as (typeof visibles)[number];
          const Icon = ICONOS[c.slug] ?? CategoryIcon;

          return (
            <Grid size={{ xs: 6, sm: 4, md: 2 }} key={c.id}>
              <Box
                component={Link}
                href={`/catalog?category_id=${c.id}`}
                sx={{
                  ...CAJA,
                  textDecoration: "none",
                  transition: "border-color 0.2s, background-color 0.2s",
                  "@media (hover: hover)": {
                    "&:hover": {
                      borderColor: "acento.main",
                      "& .cat-nombre": { color: "acento.main" },
                    },
                  },
                  "&:active": { borderColor: "acento.main" },
                }}
              >
                <Icon sx={{ fontSize: { xs: 26, md: 29 }, color: "acento.main" }} />
                <Typography
                  className="cat-nombre"
                  sx={{
                    fontSize: { xs: "0.76rem", md: "0.82rem" },
                    fontWeight: 700,
                    color: "text.primary",
                    lineHeight: 1.25,
                    transition: "color 0.2s",
                  }}
                >
                  {c.name}
                </Typography>
                <Typography sx={{ fontSize: "0.68rem", color: "text.secondary" }}>
                  {c.total_products} {c.total_products === 1 ? "producto" : "productos"}
                </Typography>
              </Box>
            </Grid>
          );
        })}
      </Grid>
    </Container>
  );
}
