"use client";

import { useCallback, useEffect, useState } from "react";

/**
 * Trae un recurso del backend y mantiene su estado de carga.
 *
 * Las pantallas del panel repetían todas el mismo bloque de veinticinco líneas:
 * un `useCallback` con la consulta, otro que aplicaba el resultado, un efecto
 * con un interruptor para descartar respuestas tardías y una función de
 * recarga. Cuatro copias del mismo código, con sus cuatro oportunidades de
 * divergir. Aquí está una sola vez.
 *
 * Dos detalles que no son casuales:
 *
 * - El resultado se guarda **dentro del callback de la promesa**, nunca en el
 *   cuerpo del efecto. Llamar a `setState` de forma síncrona ahí encadena un
 *   render extra en el mismo commit, y es lo que marca la regla
 *   `react-hooks/set-state-in-effect`.
 * - El interruptor `vigente` descarta la respuesta si el componente se
 *   desmontó o si ya se pidió otra página mientras esta viajaba. Sin él, una
 *   consulta lenta puede pisar el resultado de otra más reciente.
 *
 * `consultar` tiene que venir de un `useCallback`: es la dependencia que decide
 * cuándo volver a pedir los datos.
 */
export function useRecurso<T>(consultar: () => Promise<T>) {
  const [datos, setDatos] = useState<T | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    let vigente = true;

    consultar()
      .then((respuesta) => {
        if (!vigente) return;
        setDatos(respuesta);
        setError(null);
        setCargando(false);
      })
      .catch((problema) => {
        if (!vigente) return;
        console.error(problema);
        setError(problema);
        setCargando(false);
      });

    return () => {
      vigente = false;
    };
  }, [consultar]);

  /**
   * Vuelve a pedir los datos mostrando el indicador de carga.
   *
   * Se usa desde los manejadores de eventos —tras guardar o borrar algo—, donde
   * marcar el estado es correcto porque nace de una acción del usuario.
   */
  const recargar = useCallback(async () => {
    setCargando(true);
    try {
      setDatos(await consultar());
      setError(null);
    } catch (problema) {
      console.error(problema);
      setError(problema);
    } finally {
      setCargando(false);
    }
  }, [consultar]);

  return { datos, cargando, error, recargar };
}
