"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { useCartStore } from "@/lib/stores/cart";
import { useThemeStore } from "@/lib/stores/theme";

// MUI Components
import {
  AppBar,
  Toolbar,
  Typography,
  IconButton,
  Badge,
  InputBase,
  Box,
  Button,
  Menu,
  MenuItem,
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Divider,
  Avatar,
  alpha,
  styled,
  useTheme,
  useMediaQuery,
} from "@mui/material";

// MUI Icons
import SearchIcon from "@mui/icons-material/Search";
import ShoppingCartIcon from "@mui/icons-material/ShoppingCart";
import MenuIcon from "@mui/icons-material/Menu";
import SecurityIcon from "@mui/icons-material/Security";
import LocalShippingIcon from "@mui/icons-material/LocalShipping";
import LogoutIcon from "@mui/icons-material/Logout";
import LightModeIcon from "@mui/icons-material/LightMode";
import DarkModeIcon from "@mui/icons-material/DarkMode";
import PersonIcon from "@mui/icons-material/Person";

const Search = styled("div")(({ theme }) => ({
  position: "relative",
  borderRadius: theme.shape.borderRadius,
  backgroundColor: alpha(theme.palette.common.white, 0.15),
  "&:hover": { backgroundColor: alpha(theme.palette.common.white, 0.25) },
  marginRight: theme.spacing(2),
  marginLeft: 0,
  width: "100%",
  [theme.breakpoints.up("sm")]: {
    marginLeft: theme.spacing(3),
    width: "auto",
  },
}));

const SearchIconWrapper = styled("div")(({ theme }) => ({
  padding: theme.spacing(0, 2),
  height: "100%",
  position: "absolute",
  pointerEvents: "none",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
}));

const StyledInputBase = styled(InputBase)(({ theme }) => ({
  color: "inherit",
  "& .MuiInputBase-input": {
    padding: theme.spacing(1, 1, 1, 0),
    paddingLeft: `calc(1em + ${theme.spacing(4)})`,
    transition: theme.transitions.create("width"),
    width: "100%",
    [theme.breakpoints.up("md")]: { width: "40ch" },
  },
}));

export default function Header() {
  const { user, logout, isAdmin } = useAuth();
  const totalItems = useCartStore((s) => s.totalItems);
  const { mode, toggleTheme } = useThemeStore();
  const router = useRouter();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("md"));

  const [search, setSearch] = useState("");
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [mobileOpen, setMobileOpen] = useState(false);

  const handleProfileMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };
  const handleMenuClose = () => setAnchorEl(null);
  const handleDrawerToggle = () => setMobileOpen(!mobileOpen);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (search.trim()) {
      router.push(`/catalog?q=${encodeURIComponent(search.trim())}`);
    }
  };

  const renderMenu = (
    <Menu
      anchorEl={anchorEl}
      anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
      keepMounted
      transformOrigin={{ vertical: "top", horizontal: "right" }}
      open={Boolean(anchorEl)}
      onClose={handleMenuClose}
      sx={{ mt: 1 }}
    >
      <Box sx={{ px: 2, py: 1.5, borderBottom: "1px solid", borderColor: "divider" }}>
        <Typography variant="subtitle1" sx={{ fontWeight: "bold" }}>
          {user?.full_name}
        </Typography>
        <Typography variant="body2" sx={{ color: "text.secondary" }}>
          {user?.email}
        </Typography>
      </Box>
      <MenuItem
        onClick={() => { handleMenuClose(); router.push("/profile"); }}
      >
        <ListItemIcon><PersonIcon fontSize="small" /></ListItemIcon>
        Mi Perfil
      </MenuItem>
      {isAdmin && (
        <MenuItem onClick={() => { handleMenuClose(); router.push("/admin"); }}>
          <ListItemIcon><SecurityIcon fontSize="small" /></ListItemIcon>
          Panel Admin
        </MenuItem>
      )}
      <MenuItem onClick={() => { handleMenuClose(); router.push("/orders"); }}>
        <ListItemIcon><LocalShippingIcon fontSize="small" /></ListItemIcon>
        Mis Compras
      </MenuItem>
      <Divider />
      <MenuItem onClick={() => { handleMenuClose(); logout(); }}>
        <ListItemIcon><LogoutIcon fontSize="small" color="error" /></ListItemIcon>
        <Typography color="error">Cerrar Sesión</Typography>
      </MenuItem>
    </Menu>
  );

  const drawerContent = (
    <Box onClick={handleDrawerToggle} sx={{ textAlign: "center", pt: 2 }}>
      <Typography variant="h6" sx={{ my: 2, fontWeight: "black", color: "primary.main" }}>
        GRUPO STS SAC
      </Typography>
      <Divider />
      <List>
        <ListItem disablePadding>
          <ListItemButton component={Link} href="/catalog">
            <ListItemText primary="Catálogo" />
          </ListItemButton>
        </ListItem>
        {user ? (
          <>
            <ListItem disablePadding>
              <ListItemButton component={Link} href="/profile">
                <ListItemText primary="Mi Perfil" />
              </ListItemButton>
            </ListItem>
            <ListItem disablePadding>
              <ListItemButton component={Link} href="/orders">
                <ListItemText primary="Mis Compras" />
              </ListItemButton>
            </ListItem>
            <ListItem disablePadding>
              <ListItemButton onClick={logout}>
                <ListItemText primary="Cerrar Sesión" sx={{ color: "error.main" }} />
              </ListItemButton>
            </ListItem>
          </>
        ) : (
          <>
            <ListItem disablePadding>
              <ListItemButton component={Link} href="/login">
                <ListItemText primary="Ingresar" />
              </ListItemButton>
            </ListItem>
            <ListItem disablePadding>
              <ListItemButton component={Link} href="/register">
                <ListItemText primary="Regístrate" sx={{ color: "primary.main", fontWeight: "bold" }} />
              </ListItemButton>
            </ListItem>
          </>
        )}
      </List>
    </Box>
  );

  return (
    <>
      <AppBar position="sticky" sx={{ bgcolor: "primary.main", boxShadow: 1 }}>
        <Toolbar sx={{ minHeight: { xs: 64, md: 72 } }}>
          {isMobile && (
            <IconButton
              color="inherit"
              aria-label="open drawer"
              edge="start"
              onClick={handleDrawerToggle}
              sx={{ mr: 2 }}
            >
              <MenuIcon />
            </IconButton>
          )}

          {/* Logo */}
          <Box
            component={Link}
            href="/"
            sx={{ display: "flex", alignItems: "center", textDecoration: "none", color: "inherit", mr: 2 }}
          >
            {/* Isotipo real de Grupo STS, recortado del logo de la empresa */}
            <Box
              component="img"
              src="/brand/isotipo-sts.png"
              alt="Grupo STS"
              sx={{ height: 34, width: "auto", mr: 1.5, display: "block" }}
            />
            {!isMobile && (
              <Box>
                <Typography variant="h6" noWrap sx={{ fontWeight: 900, lineHeight: 1, letterSpacing: "-0.5px" }}>
                  GRUPO STS
                </Typography>
                <Typography variant="caption" noWrap sx={{ fontWeight: 700, letterSpacing: "2px", color: "rgba(255,255,255,0.7)" }}>
                  SAC
                </Typography>
              </Box>
            )}
          </Box>

          {/* Search */}
          {!isMobile && (
            <Box component="form" onSubmit={handleSearch} sx={{ flexGrow: 1, mx: 2 }}>
              <Search>
                <SearchIconWrapper>
                  <SearchIcon />
                </SearchIconWrapper>
                <StyledInputBase
                  placeholder="Buscar productos..."
                  inputProps={{ "aria-label": "search" }}
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
              </Search>
            </Box>
          )}

          <Box sx={{ flexGrow: 1 }} />

          {/* Right Actions */}
          <Box sx={{ display: "flex", alignItems: "center", gap: { xs: 0.5, sm: 1.5 } }}>
            {!isMobile && (
              <Button
                component={Link}
                href="/catalog"
                sx={{ color: "white", fontWeight: 600, "&:hover": { color: "#facc15" } }}
              >
                Catálogo
              </Button>
            )}

            <IconButton onClick={toggleTheme} color="inherit" title="Cambiar tema">
              {mode === "dark" ? <LightModeIcon /> : <DarkModeIcon />}
            </IconButton>

            <IconButton
              component={Link}
              href="/cart"
              size="large"
              aria-label={`carrito con ${totalItems} productos`}
              color="inherit"
            >
              <Badge badgeContent={totalItems} color="error">
                <ShoppingCartIcon />
              </Badge>
            </IconButton>

            {user ? (
              <IconButton
                size="large"
                edge="end"
                aria-label="perfil de usuario"
                aria-haspopup="true"
                onClick={handleProfileMenuOpen}
                color="inherit"
              >
                <Avatar
                  src={user.avatar_url || undefined}
                  sx={{ bgcolor: "secondary.main", color: "secondary.contrastText", width: 36, height: 36, fontSize: "1rem" }}
                >
                  {user.full_name.charAt(0).toUpperCase()}
                </Avatar>
              </IconButton>
            ) : (
              !isMobile && (
                <Box sx={{ display: "flex", gap: 1 }}>
                  <Button component={Link} href="/login" sx={{ color: "white" }}>
                    Ingresar
                  </Button>
                  <Button
                    component={Link}
                    href="/register"
                    variant="contained"
                    sx={{ bgcolor: "#facc15", color: "#003366", fontWeight: "bold", "&:hover": { bgcolor: "#fde047" } }}
                  >
                    Regístrate
                  </Button>
                </Box>
              )
            )}
          </Box>
        </Toolbar>

        {/* Mobile Search */}
        {isMobile && (
          <Box component="form" onSubmit={handleSearch} sx={{ px: 2, pb: 1.5 }}>
            <InputBase
              fullWidth
              placeholder="Buscar productos..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              sx={{ bgcolor: "white", borderRadius: 1.5, px: 2, py: 0.5, color: "text.primary" }}
              endAdornment={
                <IconButton type="submit" sx={{ p: 0.5 }}>
                  <SearchIcon />
                </IconButton>
              }
            />
          </Box>
        )}
      </AppBar>

      {renderMenu}

      <Drawer
        variant="temporary"
        open={mobileOpen}
        onClose={handleDrawerToggle}
        ModalProps={{ keepMounted: true }}
        sx={{
          display: { xs: "block", md: "none" },
          "& .MuiDrawer-paper": { boxSizing: "border-box", width: 280 },
        }}
      >
        {drawerContent}
      </Drawer>
    </>
  );
}
