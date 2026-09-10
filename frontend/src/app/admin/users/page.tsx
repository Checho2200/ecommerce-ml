"use client";

/**
 * Usuarios: quién tiene cuenta y quién puede administrar la tienda.
 *
 * Antes, el único administrador era el que había creado un script de consola
 * al desplegar, y no había forma de nombrar a otro sin entrar al servidor. Eso
 * deja la tienda colgando de una sola persona: si pierde el acceso, nadie
 * puede atender la cola de revisión ni tocar el catálogo.
 *
 * La pantalla avisa antes de romper algo, no después. Cuando queda un solo
 * administrador activo, sus acciones peligrosas salen deshabilitadas y con el
 * motivo escrito — el backend también lo rechaza, pero enterarse por un error
 * es peor que no poder pulsarlo.
 */

import { useCallback, useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  MenuItem,
  Skeleton,
  Snackbar,
  Stack,
  Switch,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import PersonAddAlt1Icon from "@mui/icons-material/PersonAddAlt1";
import SearchIcon from "@mui/icons-material/Search";
import DeleteIcon from "@mui/icons-material/Delete";

import {
  api,
  type CambiosDeCuenta,
  type UserListResponse,
  type UserResponse,
} from "@/lib/api";
import { useAuth } from "@/lib/auth";

const ROLES = [
  { valor: "CLIENTE" as const, etiqueta: "Cliente" },
  { valor: "ADMIN" as const, etiqueta: "Administrador" },
];

const FORMULARIO_VACIO = {
  email: "",
  password: "",
  full_name: "",
  phone: "",
  role: "CLIENTE" as "CLIENTE" | "ADMIN",
};

export default function AdminUsersPage() {
  const { user: yo } = useAuth();
  const [datos, setDatos] = useState<UserListResponse | null>(null);
  const [cargando, setCargando] = useState(true);
  const [fallo, setFallo] = useState(false);
  const [busqueda, setBusqueda] = useState("");
  const [aviso, setAviso] = useState<{ texto: string; tipo: "success" | "error" } | null>(null);

  const [abierto, setAbierto] = useState(false);
  const [formulario, setFormulario] = useState(FORMULARIO_VACIO);
  const [guardando, setGuardando] = useState(false);
  const [errorDeAlta, setErrorDeAlta] = useState("");
  // La cuenta que se va a eliminar, mientras se confirma. Eliminar no se hace
  // de un clic: es la única acción de esta pantalla que no se puede deshacer.
  const [porEliminar, setPorEliminar] = useState<UserResponse | null>(null);
  const [eliminando, setEliminando] = useState(false);

  const avisar = (texto: string, tipo: "success" | "error" = "success") =>
    setAviso({ texto, tipo });

  const cargar = useCallback(async (texto: string) => {
    try {
      const pagina = await api.users.list({
        per_page: 100,
        search: texto || undefined,
      });
      setDatos(pagina);
      setFallo(false);
    } catch {
      setFallo(true);
    } finally {
      setCargando(false);
    }
  }, []);

  // La búsqueda espera a que se deje de teclear: sin eso, escribir un nombre
  // de ocho letras dispara ocho consultas y las respuestas pueden llegar
  // desordenadas, dejando en pantalla el resultado de una búsqueda vieja.
  useEffect(() => {
    const temporizador = setTimeout(() => cargar(busqueda), 300);
    return () => clearTimeout(temporizador);
  }, [busqueda, cargar]);

  const soloQuedaUnAdmin = (datos?.active_admins ?? 0) <= 1;

  /** Por qué no se puede tocar a esta persona, o cadena vacía si sí se puede. */
  const motivoParaNoTocar = (persona: UserResponse): string => {
    if (persona.id === yo?.id) {
      return "No puedes cambiarte el rol ni desactivar tu propia cuenta.";
    }
    if (persona.role === "ADMIN" && persona.is_active && soloQuedaUnAdmin) {
      return "Es el único administrador activo. Nombra a otro antes de tocarlo.";
    }
    return "";
  };

  const cambiar = async (persona: UserResponse, cambios: CambiosDeCuenta) => {
    try {
      await api.users.update(persona.id, cambios);
      avisar("Cuenta actualizada");
      await cargar(busqueda);
    } catch (error: unknown) {
      avisar(
        error instanceof Error ? error.message : "No se pudo actualizar la cuenta",
        "error"
      );
    }
  };

  const crear = async () => {
    setGuardando(true);
    setErrorDeAlta("");
    try {
      await api.users.create({
        email: formulario.email.trim(),
        password: formulario.password,
        full_name: formulario.full_name.trim(),
        phone: formulario.phone.trim() || undefined,
        role: formulario.role,
      });
      setAbierto(false);
      setFormulario(FORMULARIO_VACIO);
      avisar(
        formulario.role === "ADMIN"
          ? "Administrador creado: ya puede entrar al panel"
          : "Cuenta creada"
      );
      await cargar(busqueda);
    } catch (error: unknown) {
      setErrorDeAlta(
        error instanceof Error ? error.message : "No se pudo crear la cuenta"
      );
    } finally {
      setGuardando(false);
    }
  };

  const personas = datos?.items ?? [];

  return (
    <>
      <Stack
        direction={{ xs: "column", sm: "row" }}
        spacing={2}
        sx={{ justifyContent: "space-between", alignItems: { sm: "center" }, mb: 3 }}
      >
        <Box>
          <Typography variant="h5" sx={{ fontWeight: 800 }}>
            Usuarios
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            Quién tiene cuenta en la tienda y quién puede administrarla.
          </Typography>
        </Box>
        <Button
          variant="contained"
          startIcon={<PersonAddAlt1Icon />}
          onClick={() => {
            setFormulario(FORMULARIO_VACIO);
            setErrorDeAlta("");
            setAbierto(true);
          }}
          sx={{ textTransform: "none", fontWeight: 700, borderRadius: 2, whiteSpace: "nowrap" }}
        >
          Crear cuenta
        </Button>
      </Stack>

      {soloQuedaUnAdmin && !cargando && (
        <Alert severity="warning" sx={{ mb: 3, borderRadius: 2 }}>
          Solo hay <strong>un administrador activo</strong>. Si esa cuenta pierde el
          acceso, nadie podrá entrar al panel ni atender la cola de revisión. Crea un
          segundo administrador.
        </Alert>
      )}

      {fallo && (
        <Alert severity="error" sx={{ mb: 3, borderRadius: 2 }}>
          No se pudo cargar la lista de usuarios.
        </Alert>
      )}

      <TextField
        size="small"
        placeholder="Buscar por nombre o correo"
        value={busqueda}
        onChange={(e) => setBusqueda(e.target.value)}
        slotProps={{
          input: { startAdornment: <SearchIcon sx={{ mr: 1, fontSize: 18, color: "text.secondary" }} /> },
        }}
        sx={{ mb: 2, width: { xs: "100%", sm: 320 } }}
      />

      {/* La tabla se desliza dentro de su caja: en un teléfono no cabe, y
          recortarla escondería la columna de acciones. */}
      <Box sx={{ overflowX: "auto", border: "1px solid", borderColor: "divider", borderRadius: 3 }}>
        <Table size="small" sx={{ minWidth: 720 }}>
          <TableHead>
            <TableRow>
              {["Nombre", "Correo", "Rol", "Activa", "Alta", ""].map((titulo, i) => (
                <TableCell
                  key={titulo}
                  align={i > 1 ? "center" : "left"}
                  sx={{
                    fontWeight: 700,
                    fontSize: "0.7rem",
                    textTransform: "uppercase",
                    color: "text.secondary",
                    whiteSpace: "nowrap",
                  }}
                >
                  {titulo}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {cargando ? (
              [0, 1, 2].map((i) => (
                <TableRow key={i}>
                  <TableCell colSpan={5}>
                    <Skeleton height={28} />
                  </TableCell>
                </TableRow>
              ))
            ) : personas.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} sx={{ textAlign: "center", py: 5, color: "text.secondary" }}>
                  {busqueda ? "Nadie coincide con esa búsqueda." : "Todavía no hay cuentas."}
                </TableCell>
              </TableRow>
            ) : (
              personas.map((persona) => {
                const motivo = motivoParaNoTocar(persona);
                const esYo = persona.id === yo?.id;

                return (
                  <TableRow key={persona.id} hover>
                    <TableCell sx={{ fontWeight: 600, whiteSpace: "nowrap" }}>
                      {persona.full_name}
                      {esYo && (
                        <Chip label="tú" size="small" sx={{ ml: 1, height: 18, fontSize: "0.65rem" }} />
                      )}
                    </TableCell>
                    <TableCell sx={{ color: "text.secondary" }}>{persona.email}</TableCell>
                    <TableCell align="center">
                      <Tooltip title={motivo}>
                        {/* El span hace falta: un control deshabilitado no
                            emite los eventos que el tooltip necesita. */}
                        <span>
                          <TextField
                            select
                            size="small"
                            value={persona.role}
                            disabled={!!motivo}
                            onChange={(e) =>
                              cambiar(persona, { role: e.target.value as "CLIENTE" | "ADMIN" })
                            }
                            sx={{ minWidth: 150 }}
                          >
                            {ROLES.map((r) => (
                              <MenuItem key={r.valor} value={r.valor}>
                                {r.etiqueta}
                              </MenuItem>
                            ))}
                          </TextField>
                        </span>
                      </Tooltip>
                    </TableCell>
                    <TableCell align="center">
                      <Tooltip title={motivo}>
                        <span>
                          <Switch
                            checked={persona.is_active}
                            disabled={!!motivo}
                            onChange={(e) => cambiar(persona, { is_active: e.target.checked })}
                          />
                        </span>
                      </Tooltip>
                    </TableCell>
                    <TableCell align="center" sx={{ color: "text.secondary", whiteSpace: "nowrap" }}>
                      {new Date(persona.created_at).toLocaleDateString("es-PE")}
                    </TableCell>
                    {/* Eliminar comparte las guardas del interruptor de
                        «Activa»: no puedes eliminarte a ti mismo ni al último
                        administrador que queda. `motivo` ya las resuelve. */}
                    <TableCell align="center">
                      <Tooltip title={motivo || "Eliminar la cuenta"}>
                        <span>
                          <IconButton
                            size="small"
                            color="error"
                            disabled={!!motivo}
                            onClick={() => setPorEliminar(persona)}
                          >
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                        </span>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </Box>

      <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 1.5 }}>
        {datos?.total ?? 0} cuenta(s) · {datos?.active_admins ?? 0} administrador(es) activo(s).
        Para cambiar la contraseña de alguien, esa persona debe pedir el enlace de
        recuperación desde «Olvidé mi contraseña»: nadie puede cambiársela por ella.
      </Typography>

      {/* ── Alta de cuenta ───────────────────────────────────────────── */}
      <Dialog open={abierto} onClose={() => setAbierto(false)} maxWidth="xs" fullWidth>
        <DialogTitle sx={{ fontWeight: 800 }}>Crear cuenta</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            {errorDeAlta && <Alert severity="error">{errorDeAlta}</Alert>}
            <TextField
              label="Nombre completo"
              size="small"
              fullWidth
              value={formulario.full_name}
              onChange={(e) => setFormulario({ ...formulario, full_name: e.target.value })}
            />
            <TextField
              label="Correo"
              type="email"
              size="small"
              fullWidth
              value={formulario.email}
              onChange={(e) => setFormulario({ ...formulario, email: e.target.value })}
            />
            <TextField
              label="Teléfono (opcional)"
              size="small"
              fullWidth
              value={formulario.phone}
              onChange={(e) => setFormulario({ ...formulario, phone: e.target.value })}
            />
            <TextField
              label="Contraseña"
              type="password"
              size="small"
              fullWidth
              value={formulario.password}
              onChange={(e) => setFormulario({ ...formulario, password: e.target.value })}
              helperText="Mínimo 8 caracteres. Rige la misma política que en el registro."
            />
            <TextField
              select
              label="Rol"
              size="small"
              fullWidth
              value={formulario.role}
              onChange={(e) =>
                setFormulario({ ...formulario, role: e.target.value as "CLIENTE" | "ADMIN" })
              }
            >
              {ROLES.map((r) => (
                <MenuItem key={r.valor} value={r.valor}>
                  {r.etiqueta}
                </MenuItem>
              ))}
            </TextField>
            {formulario.role === "ADMIN" && (
              <Alert severity="info" sx={{ borderRadius: 2 }}>
                Un administrador ve y decide sobre todos los pedidos, el catálogo y la
                cola de revisión del antifraude.
              </Alert>
            )}
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2.5 }}>
          <Button onClick={() => setAbierto(false)} sx={{ textTransform: "none" }}>
            Cancelar
          </Button>
          <Button
            variant="contained"
            onClick={crear}
            disabled={
              guardando ||
              !formulario.email.trim() ||
              !formulario.full_name.trim() ||
              !formulario.password
            }
            startIcon={guardando ? <CircularProgress size={16} /> : undefined}
            sx={{ textTransform: "none", fontWeight: 700 }}
          >
            {guardando ? "Creando…" : "Crear"}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Confirmación de la baja. Dice exactamente qué desaparece y qué no:
          «eliminar» a secas hace pensar que se borran también sus compras, y
          entonces nadie se atreve a pulsarlo o lo pulsa creyendo otra cosa. */}
      <Dialog open={!!porEliminar} onClose={() => setPorEliminar(null)} maxWidth="xs" fullWidth>
        <DialogTitle sx={{ fontWeight: 800 }}>Eliminar la cuenta</DialogTitle>
        <DialogContent>
          <Typography variant="body2" sx={{ mb: 2 }}>
            Se van a borrar el correo, el nombre y el teléfono de{" "}
            <Box component="span" sx={{ fontWeight: 700 }}>
              {porEliminar?.full_name || porEliminar?.email}
            </Box>
            , y la cuenta dejará de poder entrar a la tienda.
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Sus pedidos y sus evaluaciones <b>se conservan</b>, sin nombre detrás.
            Tienen que quedarse: son parte de lo que la tienda vendió y de los
            fraudes confirmados con los que se mide el modelo.
          </Typography>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2.5 }}>
          <Button onClick={() => setPorEliminar(null)} sx={{ textTransform: "none" }}>
            Cancelar
          </Button>
          <Button
            variant="contained"
            color="error"
            disabled={eliminando}
            onClick={async () => {
              if (!porEliminar) return;
              setEliminando(true);
              try {
                await api.users.remove(porEliminar.id);
                avisar("Cuenta eliminada");
                setPorEliminar(null);
                await cargar(busqueda);
              } catch (error: unknown) {
                avisar(
                  error instanceof Error ? error.message : "No se pudo eliminar la cuenta",
                  "error"
                );
              } finally {
                setEliminando(false);
              }
            }}
            sx={{ textTransform: "none", fontWeight: 700 }}
          >
            {eliminando ? "Eliminando…" : "Eliminar"}
          </Button>
        </DialogActions>
      </Dialog>

      <Snackbar
        open={!!aviso}
        autoHideDuration={3000}
        onClose={() => setAviso(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
      >
        <Alert severity={aviso?.tipo} variant="filled" onClose={() => setAviso(null)} sx={{ width: "100%" }}>
          {aviso?.texto}
        </Alert>
      </Snackbar>
    </>
  );
}
