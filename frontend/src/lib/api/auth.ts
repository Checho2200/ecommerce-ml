/** Registro, sesión, perfil y recuperación de contraseña. */

import { request, setToken, removeToken, getToken } from "./cliente";

export const auth = {
  async login(email: string, password: string) {
    const data = await request<{ access_token: string; token_type: string }>(
      "/auth/login",
      {
        method: "POST",
        body: JSON.stringify({ email, password }),
        skipAuth: true,
      }
    );
    setToken(data.access_token);
    return data;
  },

  async register(payload: {
    email: string;
    password: string;
    full_name: string;
    phone?: string;
  }) {
    return request("/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
      skipAuth: true,
    });
  },

  async me() {
    return request<{
      id: string;
      email: string;
      full_name: string;
      phone: string | null;
      role: string;
      is_active: boolean;
      created_at: string;
      avatar_url?: string | null;
    }>("/auth/me");
  },

  async updateProfile(data: { full_name?: string; phone?: string; avatar_url?: string | null }) {
    return request<{
      id: string;
      email: string;
      full_name: string;
      phone: string | null;
      role: string;
      is_active: boolean;
      created_at: string;
      avatar_url?: string | null;
    }>("/auth/me", {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  },

  async forgotPassword(email: string) {
    return request<{ message: string }>("/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify({ email }),
      skipAuth: true,
    });
  },

  async resetPassword(token: string, newPassword: string) {
    return request<{ message: string }>("/auth/reset-password", {
      method: "POST",
      body: JSON.stringify({ token, new_password: newPassword }),
      skipAuth: true,
    });
  },

  logout() {
    removeToken();
    if (typeof window !== "undefined") {
      // Recarga completa a propósito, no router.push: al cerrar sesión hay
      // que tirar también el carrito, el perfil y todo lo que quedó en
      // memoria. Una navegación del cliente conservaría ese estado.
      // eslint-disable-next-line @next/next/no-location-assign-relative-destination
      window.location.href = "/";
    }
  },

  isAuthenticated(): boolean {
    return !!getToken();
  },
};
