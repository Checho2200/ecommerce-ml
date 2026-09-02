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
    throw new ApiError(
      data.detail || "Error en la solicitud",
      response.status,
      data
    );
  }

  return data as T;
}

export { API_BASE_URL, ApiError, getToken, setToken, removeToken, request };
export type { FetchOptions };
