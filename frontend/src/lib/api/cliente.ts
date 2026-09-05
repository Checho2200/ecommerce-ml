/**
 * El cliente HTTP: una sola puerta hacia el backend.
 *
 * Todo lo que sale de la aplicación pasa por `request`, y por eso el token, el
 * manejo del 401 y el formato de los errores se resuelven en un único sitio en
 * lugar de repetirse en cada pantalla.
 *
 * Los recursos concretos (productos, pedidos, fraude…) viven cada uno en su
 * archivo dentro de esta carpeta y se apoyan en esto.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

interface FetchOptions extends RequestInit {
  skipAuth?: boolean;
}

class ApiError extends Error {
  status: number;
  data: Record<string, unknown>;

  constructor(message: string, status: number, data: Record<string, unknown> = {}) {
    super(message);
    this.status = status;
    this.data = data;
    this.name = "ApiError";
  }
}

/**
 * El texto que se le enseña a la persona cuando el backend rechaza algo.
 *
 * FastAPI usa `detail` para dos cosas distintas: en un error de negocio es una
 * frase ("El email ya está registrado"), pero en un 422 de validación es la
 * lista de campos que fallaron. Pasar esa lista tal cual a la pantalla
 * mostraba "[object Object]", que era justo el caso en el que el usuario más
 * necesitaba leer qué corregir —por ejemplo, qué le falta a su contraseña—.
 */
function mensajeDeError(data: { detail?: unknown }): string {
  const detalle = data?.detail;

  if (typeof detalle === "string") return detalle;

  if (Array.isArray(detalle)) {
    const frases = detalle
      .map((e) => {
        const msg = typeof e?.msg === "string" ? e.msg : null;
        // Pydantic antepone "Value error, " a lo que lanza un validador
        // propio; el prefijo es ruido para quien lee la pantalla.
        return msg ? msg.replace(/^Value error,\s*/, "") : null;
      })
      .filter(Boolean);
    if (frases.length) return frases.join(". ");
  }

  return "Error en la solicitud";
}

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
}

function setToken(token: string): void {
  localStorage.setItem("access_token", token);
}

function removeToken(): void {
  localStorage.removeItem("access_token");
}

async function request<T>(
  endpoint: string,
  options: FetchOptions = {}
): Promise<T> {
  const { skipAuth = false, headers: customHeaders, ...rest } = options;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(customHeaders as Record<string, string>),
  };

  if (!skipAuth) {
    const token = getToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...rest,
    headers,
  });

  if (response.status === 401) {
    removeToken();
    throw new ApiError("No autorizado", 401);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const data = await response.json();

  if (!response.ok) {
    throw new ApiError(mensajeDeError(data), response.status, data);
  }

  return data as T;
}

/**
 * Descarga un archivo del backend y se lo entrega al navegador.
 *
 * No basta con un enlace: el endpoint exige la cabecera de autorización, y un
 * `<a href>` no la manda. Se pide con fetch, se convierte en blob y se dispara
 * la descarga con un enlace temporal.
 */
async function descargar(endpoint: string, nombrePorDefecto: string): Promise<void> {
  const token = getToken();
  const respuesta = await fetch(`${API_BASE_URL}${endpoint}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });

  if (!respuesta.ok) {
    let detalle: { detail?: unknown } = {};
    try {
      detalle = await respuesta.json();
    } catch {
      /* el error no venía en JSON */
    }
    throw new ApiError(mensajeDeError(detalle), respuesta.status, detalle);
  }

  // El nombre lo propone el servidor en Content-Disposition; si no viene, se
  // usa el de respaldo para no descargar un archivo llamado "download".
  const cabecera = respuesta.headers.get("Content-Disposition") ?? "";
  const encontrado = /filename="?([^"]+)"?/.exec(cabecera);
  const nombre = encontrado ? encontrado[1] : nombrePorDefecto;

  const blob = await respuesta.blob();
  const url = URL.createObjectURL(blob);
  const enlace = document.createElement("a");
  enlace.href = url;
  enlace.download = nombre;
  document.body.appendChild(enlace);
  enlace.click();
  enlace.remove();
  // Sin esto el blob se queda en memoria hasta que se cierre la pestaña.
  URL.revokeObjectURL(url);
}

export { API_BASE_URL, ApiError, getToken, setToken, removeToken, request, descargar };
export type { FetchOptions };
