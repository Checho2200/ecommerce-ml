"use client";

/**
 * Cabecera de la tienda.
 *
 * Tres franjas, como en el comercio electrónico al que el cliente ya está
 * acostumbrado: una cinta con los datos que deciden la compra, la fila de
 * marca y búsqueda, y el menú de categorías (que sale del backend, no de una
 * lista fija en el código).
 */

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { useCartStore } from "@/lib/stores/cart";
import { useThemeStore } from "@/lib/stores/theme";
import { api, CategoryResponse } from "@/lib/api";
import { DISPLAY_FONT } from "@/components/ThemeProvider";

import {
  Box,
  Container,
  Typography,
  IconButton,
  Badge,
  InputBase,
  Menu,
  MenuItem,
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Divider,
  Stack,
  useTheme,
  useMediaQuery,
} from "@mui/material";

import SearchIcon from "@mui/icons-material/Search";
import ShoppingCartOutlinedIcon from "@mui/icons-material/ShoppingCartOutlined";
import MenuIcon from "@mui/icons-material/Menu";
import SecurityIcon from "@mui/icons-material/Security";
import LocalShippingIcon from "@mui/icons-material/LocalShipping";
import LogoutIcon from "@mui/icons-material/Logout";
import LightModeIcon from "@mui/icons-material/LightMode";
import DarkModeIcon from "@mui/icons-material/DarkMode";
import PersonOutlineIcon from "@mui/icons-material/PersonOutlined";
import BuildOutlinedIcon from "@mui/icons-material/BuildOutlined";

const AVISOS = [
  "Envíos a todo el Perú",
  "Garantía de 12 meses en todo el catálogo",
  "Jr. Alfonso Ugarte 493 · Lun a Sáb 9:00–21:00",
];

export default function Header() {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("md"));
  const router = useRouter();

  const { user, isAdmin, logout } = useAuth();
  const itemCount = useCartStore((s) => s.items.reduce((n, i) => n + i.quantity, 0));
  const { mode, toggleTheme } = useThemeStore();

  const [search, setSearch] = useState("");
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [categories, setCategories] = useState<CategoryResponse[]>([]);

  useEffect(() => {
    api.categories.list().then(setCategories).catch(() => setCategories([]));
  }, []);

  // El menú muestra solo las categorías raíz; las subcategorías (DDR4, Intel
  // Core i7…) se ven al entrar a la categoría, no en la barra de navegación.
  const categoriasRaiz = useMemo(
    () => categories.filter((c) => c.parent_id === null),
    [categories]
  );

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (search.trim()) router.push(`/catalog?q=${encodeURIComponent(search.trim())}`);
  };

  const go = (href: string) => {
    setAnchorEl(null);
    setMobileOpen(false);
    router.push(href);
  };

  const searchField = (
    <Box
      component="form"
      onSubmit={handleSearch}
      sx={{
        display: "flex",
        alignItems: "center",
        gap: 1.2,
        flexGrow: 1,
        bgcolor: "background.default",
        border: "2px solid",
        borderColor: "divider",
        px: 1.8,
        py: { xs: 0.9, md: 1.15 },
        transition: "border-color 0.2s",
        "&:focus-within": { borderColor: "primary.main" },
      }}
    >
      <SearchIcon sx={{ fontSize: 19, color: "text.secondary" }} />
      <InputBase
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        placeholder="Busca tu procesador, tarjeta de video o laptop…"
        inputProps={{ "aria-label": "Buscar productos" }}
        sx={{ flexGrow: 1, fontSize: { xs: 14, md: 15 } }}
      />
    </Box>
  );

  return (
    <>
      {/* ── Cinta de avisos ─────────────────────────────── */}
      <Box sx={{ bgcolor: "primary.main", color: "#FFFFFF" }}>
        <Container maxWidth="lg">
          <Stack
            direction="row"
            sx={{ alignItems: "center", justifyContent: "space-between", py: 0.9 }}
          >
            <Stack
              direction="row"
              spacing={{ xs: 1.5, md: 4 }}
              sx={{ alignItems: "center", overflow: "hidden" }}
            >
              {AVISOS.map((a, i) => (
                <React.Fragment key={a}>
                  {i > 0 && (
                    <Box
                      sx={{
                        opacity: 0.4,
                        display: { xs: "none", md: "block" },
                        fontSize: 13,
                      }}
                    >
                      |
                    </Box>
                  )}
                  <Typography
                    sx={{
                      fontSize: { xs: 11.5, md: 13 },
                      fontWeight: 600,
                      whiteSpace: "nowrap",
                      // En un teléfono solo cabe el primero
                      display: i === 0 ? "block" : { xs: "none", md: "block" },
                    }}
                  >
                    {a}
                  </Typography>
                </React.Fragment>
              ))}
            </Stack>

            <IconButton
              onClick={toggleTheme}
              size="small"
              aria-label="Cambiar tema"
              sx={{ color: "rgba(255,255,255,0.85)", p: 0.5 }}
            >
              {mode === "light" ? (
                <DarkModeIcon sx={{ fontSize: 17 }} />
              ) : (
                <LightModeIcon sx={{ fontSize: 17 }} />
              )}
            </IconButton>
          </Stack>
        </Container>
      </Box>

      {/* ── Fila principal ──────────────────────────────── */}
      <Box
        sx={{
          position: "sticky",
          top: 0,
          zIndex: (t) => t.zIndex.appBar,
          bgcolor: "background.paper",
          borderBottom: "1px solid",
          borderColor: "divider",
        }}
      >
        <Container maxWidth="lg">
          <Stack
            direction="row"
            spacing={{ xs: 1.5, md: 3.5 }}
            sx={{ alignItems: "center", py: { xs: 1.4, md: 1.8 } }}
          >
            {isMobile && (
              <IconButton
                edge="start"
                onClick={() => setMobileOpen(true)}
                aria-label="Abrir menú"
                sx={{ color: "text.primary", ml: -1 }}
              >
                <MenuIcon />
              </IconButton>
            )}

            <Stack
              component={Link}
              href="/"
              direction="row"
              spacing={1.3}
              sx={{ alignItems: "center", textDecoration: "none", flexShrink: 0 }}
            >
              <Box
                sx={{
                  bgcolor: "primary.main",
                  p: 0.9,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <Box
                  component="img"
                  src="/brand/isotipo-sts.png"
                  alt="Grupo STS"
                  sx={{ height: { xs: 22, md: 26 }, width: "auto", display: "block" }}
                />
              </Box>
              <Typography
                sx={{
                  fontFamily: DISPLAY_FONT,
                  fontSize: { xs: 15, md: 18 },
                  color: "primary.main",
                  lineHeight: 1,
                }}
              >
                GRUPO STS
              </Typography>
            </Stack>

            {!isMobile && searchField}

            <Box sx={{ flexGrow: { xs: 1, md: 0 } }} />

            {!isMobile && (
              <Stack
                direction="row"
                spacing={1}
                onClick={(e) => (user ? setAnchorEl(e.currentTarget) : router.push("/login"))}
                sx={{ alignItems: "center", cursor: "pointer" }}
              >
                <PersonOutlineIcon sx={{ fontSize: 22, color: "primary.main" }} />
                <Typography sx={{ fontSize: 14, fontWeight: 600 }}>
                  {user ? user.full_name.split(" ")[0] : "Mi cuenta"}
                </Typography>
              </Stack>
            )}

            <Stack
              component={Link}
              href="/cart"
              direction="row"
              spacing={1}
              sx={{ alignItems: "center", textDecoration: "none", color: "text.primary" }}
            >
              <Badge badgeContent={itemCount} color="error">
                <ShoppingCartOutlinedIcon sx={{ fontSize: 22, color: "primary.main" }} />
              </Badge>
              {!isMobile && (
                <Typography sx={{ fontSize: 14, fontWeight: 600 }}>Carrito</Typography>
              )}
            </Stack>
          </Stack>

          {/* Buscador en móvil: va debajo, a todo el ancho */}
          {isMobile && <Box sx={{ pb: 1.4 }}>{searchField}</Box>}
        </Container>

        {/* ── Menú de categorías (escritorio) ───────────── */}
        {!isMobile && categoriasRaiz.length > 0 && (
          <Box sx={{ borderTop: "1px solid", borderColor: "divider" }}>
            <Container maxWidth="lg">
              <Stack direction="row" spacing={3.5} sx={{ alignItems: "center" }}>
                {categoriasRaiz.slice(0, 7).map((c) => (
                  <Typography
                    key={c.id}
                    component={Link}
                    href={`/catalog?category_id=${c.id}`}
                    sx={{
                      py: 1.5,
                      fontSize: 14,
                      fontWeight: 600,
                      color: "text.secondary",
                      textDecoration: "none",
                      borderBottom: "3px solid transparent",
                      transition: "all 0.2s",
                      "&:hover": { color: "primary.main", borderBottomColor: "secondary.main" },
                    }}
                  >
                    {c.name}
                  </Typography>
                ))}
                <Box sx={{ flexGrow: 1 }} />
                <Typography
                  component={Link}
                  href="/services"
                  sx={{
                    py: 1.5,
                    fontSize: 14,
                    fontWeight: 700,
                    color: "error.main",
                    textDecoration: "none",
                    display: "flex",
                    alignItems: "center",
                    gap: 0.7,
                  }}
                >
                  <BuildOutlinedIcon sx={{ fontSize: 17 }} />
                  Servicio técnico
                </Typography>
              </Stack>
            </Container>
          </Box>
        )}
      </Box>

      {/* ── Menú de cuenta ──────────────────────────────── */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={() => setAnchorEl(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
        transformOrigin={{ vertical: "top", horizontal: "right" }}
        sx={{ mt: 1 }}
      >
        <Box sx={{ px: 2, py: 1.5, borderBottom: "1px solid", borderColor: "divider" }}>
          <Typography sx={{ fontWeight: 700 }}>{user?.full_name}</Typography>
          <Typography variant="body2" color="text.secondary">
            {user?.email}
          </Typography>
        </Box>
        <MenuItem onClick={() => go("/profile")}>
          <ListItemIcon><PersonOutlineIcon fontSize="small" /></ListItemIcon>
          Mi perfil
        </MenuItem>
        {isAdmin && (
          <MenuItem onClick={() => go("/admin")}>
            <ListItemIcon><SecurityIcon fontSize="small" /></ListItemIcon>
            Panel de administración
          </MenuItem>
        )}
        <MenuItem onClick={() => go("/orders")}>
          <ListItemIcon><LocalShippingIcon fontSize="small" /></ListItemIcon>
          Mis compras
        </MenuItem>
        <Divider />
        <MenuItem onClick={() => { setAnchorEl(null); logout(); }}>
          <ListItemIcon><LogoutIcon fontSize="small" color="error" /></ListItemIcon>
          <Typography color="error">Cerrar sesión</Typography>
        </MenuItem>
      </Menu>

      {/* ── Menú lateral (móvil) ────────────────────────── */}
      <Drawer open={mobileOpen} onClose={() => setMobileOpen(false)}>
        <Box sx={{ width: 274 }}>
          <Stack
            direction="row"
            spacing={1.3}
            sx={{ alignItems: "center", p: 2, bgcolor: "primary.main" }}
          >
            <Box
              component="img"
              src="/brand/isotipo-sts.png"
              alt=""
              sx={{ height: 24, width: "auto" }}
            />
            <Typography sx={{ fontFamily: DISPLAY_FONT, fontSize: 16, color: "#FFFFFF" }}>
              GRUPO STS
            </Typography>
          </Stack>

          <List sx={{ pt: 0 }}>
            <ListItem disablePadding>
              <ListItemButton onClick={() => go("/catalog")}>
                <ListItemText primary={<Typography sx={{ fontWeight: 700 }}>Todo el catálogo</Typography>} />
              </ListItemButton>
            </ListItem>
            <ListItem disablePadding>
              <ListItemButton onClick={() => go("/services")}>
                <ListItemText
                  primary={<Typography sx={{ fontWeight: 700, color: "error.main" }}>Servicio técnico</Typography>}
                />
              </ListItemButton>
            </ListItem>
          </List>

          <Divider />
          <Typography
            variant="overline"
            sx={{ px: 2, pt: 1.5, display: "block", color: "text.secondary", fontWeight: 700 }}
          >
            Categorías
          </Typography>
          <List dense>
            {categoriasRaiz.map((c) => (
              <ListItem disablePadding key={c.id}>
                <ListItemButton onClick={() => go(`/catalog?category_id=${c.id}`)}>
                  <ListItemText primary={c.name} />
                </ListItemButton>
              </ListItem>
            ))}
          </List>

          <Divider />
          <List>
            {user ? (
              <>
                <ListItem disablePadding>
                  <ListItemButton onClick={() => go("/profile")}>
                    <ListItemText primary="Mi perfil" />
                  </ListItemButton>
                </ListItem>
                <ListItem disablePadding>
                  <ListItemButton onClick={() => go("/orders")}>
                    <ListItemText primary="Mis compras" />
                  </ListItemButton>
                </ListItem>
                {isAdmin && (
                  <ListItem disablePadding>
                    <ListItemButton onClick={() => go("/admin")}>
                      <ListItemText primary="Panel de administración" />
                    </ListItemButton>
                  </ListItem>
                )}
                <ListItem disablePadding>
                  <ListItemButton onClick={() => { setMobileOpen(false); logout(); }}>
                    <ListItemText primary="Cerrar sesión" sx={{ color: "error.main" }} />
                  </ListItemButton>
                </ListItem>
              </>
            ) : (
              <>
                <ListItem disablePadding>
                  <ListItemButton onClick={() => go("/login")}>
                    <ListItemText primary="Iniciar sesión" />
                  </ListItemButton>
                </ListItem>
                <ListItem disablePadding>
                  <ListItemButton onClick={() => go("/register")}>
                    <ListItemText
                      primary={<Typography sx={{ fontWeight: 700, color: "primary.main" }}>Crear cuenta</Typography>}
                    />
                  </ListItemButton>
                </ListItem>
              </>
            )}
          </List>
        </Box>
      </Drawer>
    </>
  );
}
