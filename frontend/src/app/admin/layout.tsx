"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import {
  Box,
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Typography,
  Divider,
  Button,
  Avatar,
  IconButton,
  AppBar,
  Toolbar,
  useTheme,
  useMediaQuery,
  CircularProgress
} from "@mui/material";

// Icons
import LayoutDashboardIcon from "@mui/icons-material/Dashboard";
import PackageIcon from "@mui/icons-material/Inventory";
import TagsIcon from "@mui/icons-material/Label";
import ShoppingCartIcon from "@mui/icons-material/ShoppingCart";
import HomeIcon from "@mui/icons-material/Home";
import LogoutIcon from "@mui/icons-material/Logout";
import MenuIcon from "@mui/icons-material/Menu";
import SettingsIcon from "@mui/icons-material/Settings";
import BuildIcon from "@mui/icons-material/Build";
import PsychologyIcon from "@mui/icons-material/Psychology";

const drawerWidth = 260;

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { user, loading, isAdmin, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("md"));
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    if (loading) return;
    // Antes solo se comprobaba que hubiera sesión: cualquier cliente logueado
    // veía el panel completo (aunque la API le rechazara las peticiones).
    if (!user) router.push("/login");
    else if (!isAdmin) router.push("/");
  }, [loading, user, isAdmin, router]);

  if (loading) {
    return (
      <Box sx={{ display: "flex", height: "100dvh", alignItems: "center", justifyContent: "center", bgcolor: "background.default", gap: 2 }}>
        <CircularProgress />
        <Typography color="text.secondary">Cargando panel...</Typography>
      </Box>
    );
  }

  if (!user) return null;

  const NAV_ITEMS = [
    { href: "/admin", icon: <LayoutDashboardIcon />, label: "Dashboard" },
    { href: "/admin/products", icon: <PackageIcon />, label: "Productos" },
    { href: "/admin/categories", icon: <TagsIcon />, label: "Categorías" },
    { href: "/admin/orders", icon: <ShoppingCartIcon />, label: "Órdenes" },
    // El modelo tiene su propia entrada: repartido entre el Dashboard y
    // Órdenes no se podía ni revisar una cola ni leer una tendencia.
    { href: "/admin/fraud", icon: <PsychologyIcon />, label: "Antifraude" },
    { href: "/admin/services", icon: <BuildIcon />, label: "Servicios" },
    { href: "/admin/settings", icon: <SettingsIcon />, label: "Configuración" },
  ];

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  const drawer = (
    <Box sx={{ display: "flex", flexDirection: "column", height: "100%", bgcolor: "background.paper" }}>
      {/* Logo */}
      <Box sx={{ p: 3, display: "flex", alignItems: "center", gap: 2 }}>
        <Avatar sx={{ bgcolor: "primary.main", width: 40, height: 40 }} variant="rounded">
          ST
        </Avatar>
        <Box>
          <Typography variant="subtitle1" sx={{ fontWeight: 800, lineHeight: 1.2 }}>GRUPO STS SAC</Typography>
          <Typography variant="caption" sx={{ color: "text.secondary", fontWeight: 600 }}>{isAdmin ? "Panel Admin" : "Mi Cuenta"}</Typography>
        </Box>
      </Box>
      <Divider />

      {/* Nav */}
      <List sx={{ px: 2, flexGrow: 1, py: 2 }}>
        <ListItem disablePadding sx={{ mb: 1 }}>
          <ListItemButton component={Link} href="/" sx={{ borderRadius: 2 }}>
            <ListItemIcon sx={{ minWidth: 40 }}><HomeIcon /></ListItemIcon>
            <ListItemText primary={<Typography variant="body2" sx={{ fontWeight: 600 }}>Ir a Tienda</Typography>} />
          </ListItemButton>
        </ListItem>
        <Divider sx={{ mb: 1 }} />
        {NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href || (item.href !== "/admin" && pathname.startsWith(item.href));
          return (
            <ListItem key={item.href} disablePadding sx={{ mb: 0.5 }}>
              <ListItemButton
                component={Link}
                href={item.href}
                selected={isActive}
                onClick={() => isMobile && setMobileOpen(false)}
                sx={{
                  borderRadius: 2,
                  "&.Mui-selected": { bgcolor: "primary.main", color: "white", "&:hover": { bgcolor: "primary.dark" } },
                  "&.Mui-selected .MuiListItemIcon-root": { color: "white" }
                }}
              >
                <ListItemIcon sx={{ minWidth: 40, color: isActive ? "white" : "inherit" }}>
                  {item.icon}
                </ListItemIcon>
                <ListItemText primary={<Typography variant="body2" sx={{ fontWeight: 600 }}>{item.label}</Typography>} />
              </ListItemButton>
            </ListItem>
          );
        })}
      </List>

      <Divider />
      {/* User info */}
      <Box sx={{ p: 2 }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, mb: 2 }}>
          <Avatar sx={{ width: 36, height: 36, bgcolor: "secondary.main", color: "secondary.contrastText", fontSize: "1rem" }}>
            {user.full_name.charAt(0).toUpperCase()}
          </Avatar>
          <Box sx={{ overflow: "hidden" }}>
            <Typography variant="body2" sx={{ fontWeight: 700, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
              {user.full_name}
            </Typography>
            <Typography variant="caption" sx={{ color: "text.secondary" }}>{user.role}</Typography>
          </Box>
        </Box>
        <Button
          fullWidth
          variant="outlined"
          color="error"
          startIcon={<LogoutIcon />}
          onClick={logout}
          sx={{ borderRadius: 2, textTransform: "none", fontWeight: 700 }}
        >
          Cerrar Sesión
        </Button>
      </Box>
    </Box>
  );

  return (
    <Box sx={{ display: "flex", minHeight: "100dvh", bgcolor: "background.default" }}>
      {/* Mobile AppBar */}
      {isMobile && (
        <AppBar position="fixed" sx={{ bgcolor: "background.paper", color: "text.primary", boxShadow: 1 }}>
          <Toolbar>
            <IconButton edge="start" color="inherit" aria-label="open drawer" onClick={handleDrawerToggle} sx={{ mr: 2 }}>
              <MenuIcon />
            </IconButton>
            <Typography variant="h6" noWrap component="div" sx={{ fontWeight: 800 }}>
              Panel Admin
            </Typography>
          </Toolbar>
        </AppBar>
      )}

      {/* Sidebar */}
      <Box component="nav" sx={{ width: { md: drawerWidth }, flexShrink: { md: 0 } }}>
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{ keepMounted: true }}
          sx={{
            display: { xs: "block", md: "none" },
            "& .MuiDrawer-paper": { boxSizing: "border-box", width: drawerWidth },
          }}
        >
          {drawer}
        </Drawer>
        <Drawer
          variant="permanent"
          sx={{
            display: { xs: "none", md: "block" },
            "& .MuiDrawer-paper": { boxSizing: "border-box", width: drawerWidth, borderRight: "1px solid", borderColor: "divider" },
          }}
          open
        >
          {drawer}
        </Drawer>
      </Box>

      {/* Main Content */}
      <Box component="main" sx={{ flexGrow: 1, p: { xs: 2, md: 4 }, mt: { xs: 8, md: 0 }, width: { md: `calc(100% - ${drawerWidth}px)` } }}>
        {children}
      </Box>
    </Box>
  );
}
