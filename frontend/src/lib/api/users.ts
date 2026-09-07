/** Cuentas de la tienda: listar, dar de alta y cambiar el rol o el estado. */

import { request } from "./cliente";
import type { UserListResponse, UserResponse } from "./tipos";

/**
 * Lo que un administrador puede cambiarle a una cuenta ajena.
 *
 * No lleva contraseña, igual que el esquema del backend: cambiársela a otra
 * persona sin que se entere es suplantarla.
 */
export interface CambiosDeCuenta {
  full_name?: string;
  phone?: string;
  role?: "CLIENTE" | "ADMIN";
  is_active?: boolean;
}

export const users = {
  async list(params?: {
    page?: number;
    per_page?: number;
    search?: string;
    role?: "CLIENTE" | "ADMIN";
    active?: boolean;
  }) {
    const qs = new URLSearchParams();
    if (params?.page) qs.set("page", String(params.page));
    if (params?.per_page) qs.set("per_page", String(params.per_page));
    if (params?.search) qs.set("search", params.search);
    if (params?.role) qs.set("role", params.role);
    // `active` es un booleano: comprobar que no sea undefined y no su verdad,
    // porque `false` es un filtro tan legítimo como `true`.
    if (params?.active !== undefined) qs.set("active", String(params.active));

    const cadena = qs.toString();
    return request<UserListResponse>(`/users${cadena ? `?${cadena}` : ""}`);
  },

  async create(data: {
    email: string;
    password: string;
    full_name: string;
    phone?: string;
    role: "CLIENTE" | "ADMIN";
  }) {
    return request<UserResponse>("/users", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  /**
   * Cambia el rol, el estado o los datos de una cuenta.
   *
   * No incluye la contraseña a propósito: cambiársela a otra persona sin que
   * se entere es suplantarla. Para eso está el enlace de recuperación, que
   * llega a su propio correo.
   */
  async update(id: string, data: CambiosDeCuenta) {
    return request<UserResponse>(`/users/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  },
};
