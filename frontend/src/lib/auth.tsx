"use client";

/**
 * Auth Context & Provider.
 * Maneja el estado de autenticación global y protección de rutas.
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { api, ApiError } from "@/lib/api";

interface User {
  id: string;
  email: string;
  full_name: string;
  phone: string | null;
  role: string;
  is_active: boolean;
  created_at: string;
  avatar_url?: string | null;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (data: {
    email: string;
    password: string;
    full_name: string;
    phone?: string;
  }) => Promise<void>;
  logout: () => void;
  /** Vuelve a leer el perfil del backend, p. ej. tras editarlo. */
  refresh: () => Promise<void>;
  isAdmin: boolean;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | null>(null);

/**
 * Consulta quien es el usuario del token guardado.
 *
 * No toca el estado de React: devuelve el usuario, `null` si no hay sesion
 * valida, o `undefined` cuando no se pudo averiguar. Esa tercera respuesta
 * importa: el backend vive en el plan gratuito de Render y se suspende por
 * inactividad, asi que al volver de MercadoPago la primera peticion puede
 * tardar casi un minuto o fallar. Antes cualquier error cerraba la sesion y el
 * cliente regresaba del pago aparentemente deslogueado aunque su token
 * siguiera siendo valido. Solo un 401 significa credencial invalida; lo demas
 * se reintenta, y si aun asi no hay respuesta se deja el estado como estaba.
 */
async function obtenerUsuario(): Promise<User | null | undefined> {
  if (!api.auth.isAuthenticated()) return null;

  const esperas = [0, 2000, 5000, 10000];

  for (const espera of esperas) {
    if (espera > 0) {
      await new Promise((resolve) => setTimeout(resolve, espera));
    }

    try {
      return await api.auth.me();
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) return null;
      // Fallo transitorio: se reintenta sin descartar el token.
    }
  }

  return undefined;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const aplicarUsuario = useCallback((resultado: User | null | undefined) => {
    if (resultado !== undefined) setUser(resultado);
    setLoading(false);
  }, []);

  // Lo usan login y register, que nacen de un clic del usuario.
  const fetchUser = useCallback(async () => {
    aplicarUsuario(await obtenerUsuario());
  }, [aplicarUsuario]);

  // La sesion se comprueba al montar. El resultado se guarda dentro del
  // callback de la promesa, no en el cuerpo del efecto, para no encadenar un
  // render de mas; `vigente` descarta la respuesta si el provider ya se
  // desmonto durante la espera.
  useEffect(() => {
    let vigente = true;
    obtenerUsuario()
      .then((resultado) => { if (vigente) aplicarUsuario(resultado); })
      .catch(() => { if (vigente) setLoading(false); });
    return () => { vigente = false; };
  }, [aplicarUsuario]);

  const login = async (email: string, password: string) => {
    await api.auth.login(email, password);
    await fetchUser();
  };

  const register = async (data: {
    email: string;
    password: string;
    full_name: string;
    phone?: string;
  }) => {
    await api.auth.register(data);
    await api.auth.login(data.email, data.password);
    await fetchUser();
  };

  const logout = () => {
    api.auth.logout();
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        register,
        logout,
        refresh: fetchUser,
        isAdmin: user?.role === "ADMIN",
        isAuthenticated: !!user,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth debe usarse dentro de un AuthProvider");
  }
  return context;
}

export default AuthProvider;
