"use client";

/**
 * Despierta el backend apenas se abre el sitio.
 *
 * El plan gratuito de Render suspende el servicio tras ~15 minutos sin tráfico y
 * la primera petición puede tardar entre 30 y 50 segundos. Al lanzar este ping
 * en cuanto carga cualquier página, el servidor arranca mientras la persona
 * todavía está leyendo, y para cuando navega al catálogo ya responde rápido.
 *
 * Es deliberadamente "fire and forget": si falla, no afecta en nada a la página.
 */

import { useEffect } from "react";
import { api } from "@/lib/api";

export default function BackendWarmup() {
  useEffect(() => {
    api.system.health().catch(() => {
      /* silencioso: es solo un empujón para despertar el servidor */
    });
  }, []);

  return null;
}
