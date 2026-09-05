"use client";

/**
 * El campo de contraseña de toda la tienda.
 *
 * Estaba copiado en cuatro pantallas —entrar, registrarse, restablecer y
 * repetir la clave— con el botón del ojo pegado a mano en unas y ausente en
 * otras. Ahora se comporta igual en todas, que es lo que permite razonar sobre
 * cómo se trata una contraseña en este proyecto en lugar de revisarlo pantalla
 * por pantalla.
 *
 * Lo que aporta sobre un TextField normal:
 *
 * - **No se corrige ni se autocompleta el texto.** El corrector ortográfico y
 *   la mayúscula automática del móvil alteran lo que se escribe, y algunos
 *   correctores envían el texto a un servicio en la nube para revisarlo.
 * - **Lo revelado se vuelve a ocultar solo** a los pocos segundos y al salir
 *   del campo, que es lo que protege de verdad frente a quien mira la pantalla
 *   por encima del hombro o frente a una clave que se queda a la vista al
 *   alejarse del equipo.
 * - **Una barra que mide la fuerza**, cuando se está eligiendo una nueva. Pesa
 *   la longitud por encima de la mezcla de símbolos, que es el orden en que
 *   las dos cosas importan.
 *
 * Lo que a propósito NO hace: impedir copiar y pegar. Es una costumbre muy
 * extendida y contraproducente —quien no puede pegar no usa un gestor de
 * contraseñas, y sin gestor la gente elige claves cortas que pueda escribir de
 * memoria—, la desaconsejan expresamente el NIST y el NCSC británico, y no
 * defiende de nada: quien ya está frente al teclado puede escribirla igual.
 */

import { useEffect, useState } from "react";
import {
  Box,
  IconButton,
  InputAdornment,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import Visibility from "@mui/icons-material/Visibility";
import VisibilityOff from "@mui/icons-material/VisibilityOff";
import type { TextFieldProps } from "@mui/material";

/** Debe coincidir con app/core/passwords.py del backend. */
export const LONGITUD_MINIMA = 8;

/** Segundos que la contraseña se queda visible antes de volver a ocultarse. */
const SEGUNDOS_VISIBLE = 10;

const CLAVES_EVIDENTES = new Set([
  "12345678", "123456789", "1234567890", "password", "contrasena",
  "contraseña", "qwertyui", "qwerty123", "admin123", "administrador",
  "iloveyou", "princess", "abc12345", "password1", "password123",
  "11111111", "00000000", "letmein1", "welcome1", "gruposts",
]);

const NIVELES = [
  { texto: "Muy débil", color: "error.main" },
  { texto: "Débil", color: "error.main" },
  { texto: "Aceptable", color: "warning.main" },
  { texto: "Buena", color: "success.main" },
  { texto: "Muy buena", color: "success.main" },
];

/**
 * Puntúa de 0 a 4 lo robusta que es la contraseña.
 *
 * Es la misma cuenta que hace `fuerza()` en el backend, repetida aquí para
 * poder pintar la barra mientras se escribe, sin una petición por tecla. Quien
 * decide si se acepta sigue siendo el servidor.
 */
export function fuerzaDeContrasena(clave: string): number {
  if (!clave) return 0;
  if (CLAVES_EVIDENTES.has(clave.toLowerCase())) return 0;

  let puntos = 0;
  if (clave.length >= LONGITUD_MINIMA) puntos += 1;
  if (clave.length >= 12) puntos += 1;
  if (clave.length >= 16) puntos += 1;

  const variedad = [/[a-z]/, /[A-Z]/, /\d/, /[^A-Za-z0-9]/].filter((p) => p.test(clave)).length;
  if (variedad >= 3) puntos += 1;

  return Math.min(puntos, 4);
}

export default function CampoDeContrasena({
  valor,
  onCambio,
  medirFuerza = false,
  ...resto
}: {
  valor: string;
  onCambio: (valor: string) => void;
  /** Solo al elegir una clave nueva; al entrar, la fuerza ya no se decide. */
  medirFuerza?: boolean;
} & Omit<TextFieldProps, "value" | "onChange" | "type">) {
  const [visible, setVisible] = useState(false);

  // Volver a ocultarla sola: una contraseña revelada que se queda en pantalla
  // mientras la persona se levanta del sitio es el descuido más común.
  useEffect(() => {
    if (!visible) return;
    const temporizador = setTimeout(() => setVisible(false), SEGUNDOS_VISIBLE * 1000);
    return () => clearTimeout(temporizador);
  }, [visible]);

  const fuerza = medirFuerza ? fuerzaDeContrasena(valor) : 0;
  const nivel = NIVELES[fuerza];

  return (
    <Box>
      <TextField
        {...resto}
        type={visible ? "text" : "password"}
        value={valor}
        onChange={(e) => onCambio(e.target.value)}
        onBlur={(e) => {
          setVisible(false);
          resto.onBlur?.(e);
        }}
        slotProps={{
          ...resto.slotProps,
          input: {
            ...resto.slotProps?.input,
            endAdornment: (
              <InputAdornment position="end">
                <IconButton
                  onClick={() => setVisible((v) => !v)}
                  edge="end"
                  size="small"
                  // Fuera del recorrido del tabulador: quien navega con el
                  // teclado va del campo al botón de enviar, no al ojo.
                  tabIndex={-1}
                  aria-label={visible ? "Ocultar contraseña" : "Mostrar contraseña"}
                >
                  {visible ? <VisibilityOff fontSize="small" /> : <Visibility fontSize="small" />}
                </IconButton>
              </InputAdornment>
            ),
          },
          htmlInput: {
            ...resto.slotProps?.htmlInput,
            spellCheck: false,
            autoCorrect: "off",
            autoCapitalize: "none",
          },
        }}
      />

      {medirFuerza && valor.length > 0 && (
        <Stack direction="row" spacing={1} sx={{ alignItems: "center", mt: 1, px: 0.5 }}>
          <Stack direction="row" spacing={0.5} sx={{ flexGrow: 1 }}>
            {[0, 1, 2, 3].map((i) => (
              <Box
                key={i}
                sx={{
                  flex: 1,
                  height: 4,
                  borderRadius: 2,
                  bgcolor: i < fuerza ? nivel.color : "action.hover",
                  transition: "background-color 0.2s",
                }}
              />
            ))}
          </Stack>
          <Typography variant="caption" sx={{ color: nivel.color, fontWeight: 700, minWidth: 74 }}>
            {nivel.texto}
          </Typography>
        </Stack>
      )}
    </Box>
  );
}
