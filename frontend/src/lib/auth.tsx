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
  isAdmin: boolean;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchUser = useCallback(async () => {
    if (!api.auth.isAuthenticated()) {
      setUser(null);
      setLoading(false);
      return;
    }

    // El backend vive en el plan gratuito de Render y se suspende por
    // inactividad: al volver de MercadoPago, la primera peticion puede tardar
    // casi un minuto o fallar directamente. Antes cualquier error cerraba la
    // sesion, asi que el cliente regresaba del pago aparentemente
    // deslogueado aunque su token siguiera siendo valido. Solo un 401
    // significa credencial invalida; lo demas se reintenta.
    const esperas = [0, 2000, 5000, 10000];

    for (const espera of esperas) {
      if (espera > 0) {
        await new Promise((resolve) => setTimeout(resolve, espera));
      }

      try {
        setUser(await api.auth.me());
        setLoading(false);
        return;
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) {
          setUser(null);
          setLoading(false);
          return;
        }
        // Fallo transitorio: se reintenta sin descartar el token.
      }
    }

    setLoading(false);
  }, []);

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

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
