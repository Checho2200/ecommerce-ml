"use client";

/**
 * Cómo llega el modelo a su puntaje, con la cuenta a la vista.
 *
 * Antes esta parte del panel era una línea de tiempo que decía *cuándo* corría
 * el modelo. Estaba bien pero no respondía la pregunta que de verdad se hace
 * quien mira un pedido rechazado: por qué salió 88 % y no 40 %.
 *
 * La respuesta se puede enseñar entera porque LightGBM la deja escrita. El
 * puntaje es la suma de los votos de sus árboles en escala logit, y esa suma se
 * reparte de forma exacta entre las cuatro variables (valores SHAP, que la
 * librería calcula con `pred_contrib`). Cada evaluación guarda ese reparto, así
 * que aquí se puede rehacer la aritmética con un pedido de verdad:
 *
 *     puntaje = sigmoide(base + aporte₁ + aporte₂ + aporte₃ + aporte₄)
 *
 * Que es la diferencia entre "el modelo lo decidió" y una decisión auditable.
 */

import { useMemo } from "react";
import {
  Box,
  Card,
  CardContent,
  Chip,
  Skeleton,
  Stack,
  Tooltip,
  Typography,
  useTheme,
} from "@mui/material";
import type { FraudLogResponse, FraudModelInfo } from "@/lib/api";

/** Cómo se llama y qué significa cada variable de cara a una persona. */
const VARIABLES: Record<string, { nombre: string; explica: string; formato: (v: number) => string }> = {
  total_amount: {
    nombre: "Monto del pedido",
    explica: "Un carrito muy por encima de lo habitual es la señal más fuerte.",
    formato: (v) => `S/ ${v.toLocaleString("es-PE", { minimumFractionDigits: 2 })}`,
  },
  high_risk_items_count: {
    nombre: "Artículos de alto riesgo",
    explica: "Procesadores, tarjetas de video, monitores y placas: lo que se revende rápido.",
    formato: (v) => `${v}`,
  },
  checkout_duration_seconds: {
    nombre: "Duración del checkout",
    explica: "Quien compra con una tarjeta que no es suya no se detiene a comparar.",
    formato: (v) => (v >= 60 ? `${(v / 60).toFixed(1)} min` : `${Math.round(v)} s`),
  },
  is_new_shipping_address: {
    nombre: "Dirección nueva",
    explica: "Una dirección que este cliente nunca usó antes.",
    formato: (v) => (v ? "Sí" : "No"),
  },
};

const sigmoide = (x: number) => 1 / (1 + Math.exp(-x));

/**
 * Naranja para lo que empuja hacia fraude, azul para lo que empuja al otro
 * lado. Los mismos dos colores que el gráfico del historial, y por el mismo
 * motivo: verde y rojo es justo el par que no distingue la forma más común de
 * daltonismo.
 *
 * Las barras y los números llevan tonos distintos porque necesitan cosas
 * distintas: una barra es un gráfico y le basta 3:1 sobre el fondo, mientras
 * que un número es texto pequeño y necesita 4.5:1. Los tonos de las barras,
 * puestos en el texto, no llegaban.
 */
const TONOS = {
  claro: { barraFraude: "#eb6834", barraLegitima: "#2a78d6", textoFraude: "#b23c0a", textoLegitima: "#1e4fa8" },
  oscuro: { barraFraude: "#d95926", barraLegitima: "#3987e5", textoFraude: "#f08a5d", textoLegitima: "#79a9e8" },
};

function Formula({ children }: { children: React.ReactNode }) {
  return (
    <Box
      sx={{
        fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
        fontSize: { xs: "0.82rem", md: "0.9rem" },
        bgcolor: "action.hover",
        borderRadius: 2,
        px: 2,
        py: 1.4,
        overflowX: "auto",
        whiteSpace: "nowrap",
      }}
    >
      {children}
    </Box>
  );
}

/** Una barra que sale del centro: a la derecha empuja a fraude, a la izquierda no. */
function BarraDeAporte({
  aporte,
  maximo,
  tonos,
}: {
  aporte: number;
  maximo: number;
  tonos: (typeof TONOS)["claro"];
}) {
  const proporcion = maximo > 0 ? Math.min(Math.abs(aporte) / maximo, 1) : 0;
  const haciaFraude = aporte > 0;

  return (
    <Box sx={{ position: "relative", height: 10, display: "flex", alignItems: "center" }}>
      <Box sx={{ position: "absolute", inset: 0, display: "flex" }}>
        <Box sx={{ flex: 1, display: "flex", justifyContent: "flex-end" }}>
          {!haciaFraude && (
            <Box sx={{ width: `${proporcion * 100}%`, bgcolor: tonos.barraLegitima, borderRadius: "3px 0 0 3px" }} />
          )}
        </Box>
        <Box sx={{ width: "1px", bgcolor: "divider" }} />
        <Box sx={{ flex: 1 }}>
          {haciaFraude && (
            <Box sx={{ width: `${proporcion * 100}%`, height: "100%", bgcolor: tonos.barraFraude, borderRadius: "0 3px 3px 0" }} />
          )}
        </Box>
      </Box>
    </Box>
  );
}

export default function ComoDecideElModelo({
  modelo,
  ejemplo,
  cargando,
}: {
  modelo: FraudModelInfo | null;
  /** Una evaluación real con la que enseñar la cuenta. */
  ejemplo: FraudLogResponse | null;
  cargando: boolean;
}) {
  const tema = useTheme();
  const tonos = tema.palette.mode === "dark" ? TONOS.oscuro : TONOS.claro;
  const base = modelo?.base_value ?? null;

  const cuenta = useMemo(() => {
    if (!ejemplo?.contributions || base === null) return null;

    const aportes = Object.entries(ejemplo.contributions)
      .map(([variable, aporte]) => ({
        variable,
        aporte,
        valor: ejemplo.feature_vector?.[variable],
      }))
      .sort((a, b) => Math.abs(b.aporte) - Math.abs(a.aporte));

    const suma = aportes.reduce((n, a) => n + a.aporte, 0);
    const logit = base + suma;

    return {
      aportes,
      suma,
      logit,
      probabilidad: sigmoide(logit),
      maximo: Math.max(...aportes.map((a) => Math.abs(a.aporte)), 0.0001),
    };
  }, [ejemplo, base]);

  const bandas = [
    { etiqueta: "Aprobar", desde: 0, hasta: modelo?.approve_below ?? 0.35, color: tonos.barraLegitima },
    {
      etiqueta: "Revisar a mano",
      desde: modelo?.approve_below ?? 0.35,
      hasta: modelo?.block_above ?? 0.8,
      color: "#eda100",
    },
    { etiqueta: "Bloquear", desde: modelo?.block_above ?? 0.8, hasta: 1, color: tonos.barraFraude },
  ];

  return (
    <Card elevation={0} sx={{ border: "1px solid", borderColor: "divider", borderRadius: 3 }}>
      <CardContent sx={{ p: 3 }}>
        <Typography variant="subtitle1" sx={{ fontWeight: 800 }}>
          Cómo decide el modelo
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, mb: 3, maxWidth: 820 }}>
          Ocurre dentro de la misma petición que crea el pedido, <strong>antes de que
          exista un cobro</strong>: una compra bloqueada nunca llega a la pasarela de pago.
          Lo que sigue es la cuenta completa, con un pedido real.
        </Typography>

        {/* ── 1. Lo que mira ──────────────────────────────────────────── */}
        <Typography variant="subtitle2" sx={{ fontWeight: 800, mb: 1 }}>
          1. Lee cuatro datos del pedido
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2, maxWidth: 820 }}>
          Ninguno es un dato personal: no mira quién compra, mira cómo compra. Con cuatro
          variables el modelo se puede auditar entero, que es más valioso que el punto de
          acierto extra que darían veinte.
        </Typography>
        <Stack direction={{ xs: "column", md: "row" }} spacing={1.5} sx={{ mb: 3.5 }}>
          {Object.entries(VARIABLES).map(([clave, v]) => (
            <Box
              key={clave}
              sx={{ flex: 1, border: "1px solid", borderColor: "divider", borderRadius: 2, p: 1.8 }}
            >
              <Typography variant="body2" sx={{ fontWeight: 700 }}>
                {v.nombre}
              </Typography>
              <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 0.5, lineHeight: 1.6 }}>
                {v.explica}
              </Typography>
            </Box>
          ))}
        </Stack>

        {/* ── 2. La fórmula ───────────────────────────────────────────── */}
        <Typography variant="subtitle2" sx={{ fontWeight: 800, mb: 1 }}>
          2. Suma los votos de {modelo?.n_trees ?? 100} árboles de decisión
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2, maxWidth: 820 }}>
          LightGBM no es un árbol, son cientos, y cada uno se entrena para corregir el error
          que dejaron los anteriores. Cada árbol emite un voto en <em>log-odds</em> —una
          escala donde los votos se suman— y el modelo los acumula. Esa suma se reparte de
          forma exacta entre las cuatro variables, y ese reparto es lo que se guarda con
          cada pedido:
        </Typography>
        <Formula>
          suma = base{" "}
          {base !== null && (
            <Box component="span" sx={{ color: "text.secondary" }}>
              ({base.toFixed(2)})
            </Box>
          )}{" "}
          + aporte<sub>monto</sub> + aporte<sub>riesgo</sub> + aporte<sub>checkout</sub> +
          aporte<sub>dirección</sub>
        </Formula>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 2, mb: 2, maxWidth: 820 }}>
          La suma vive en log-odds y va de −∞ a +∞, así que no se puede leer como
          probabilidad. La función logística la comprime al rango de 0 a 1:
        </Typography>
        <Formula>puntaje = 1 / (1 + e^−suma)</Formula>

        {base !== null && (
          <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 1.5, maxWidth: 820, lineHeight: 1.7 }}>
            El <strong>base</strong> es el punto de partida del modelo antes de mirar nada, y
            es el mismo para todos los pedidos. No es la tasa de fraude de la tienda: el
            entrenamiento equilibra las clases para que el fraude —que es raro— no quede
            aplastado, y eso levanta el punto de partida por encima de la proporción real.
          </Typography>
        )}

        {/* ── 3. El ejemplo real ──────────────────────────────────────── */}
        <Typography variant="subtitle2" sx={{ fontWeight: 800, mt: 3.5, mb: 1 }}>
          3. La cuenta, con un pedido de verdad
        </Typography>

        {cargando ? (
          <Skeleton variant="rectangular" height={230} sx={{ borderRadius: 2 }} />
        ) : !cuenta ? (
          <Box sx={{ py: 4, textAlign: "center", border: "1px dashed", borderColor: "divider", borderRadius: 2 }}>
            <Typography variant="body2" color="text.secondary">
              Aún no hay evaluaciones con las que enseñar la cuenta.
            </Typography>
          </Box>
        ) : (
          <Box sx={{ border: "1px solid", borderColor: "divider", borderRadius: 2, p: { xs: 2, md: 2.5 } }}>
            <Stack direction="row" spacing={1.5} sx={{ alignItems: "center", mb: 2, flexWrap: "wrap" }}>
              <Typography component="code" variant="caption" sx={{ color: "text.secondary" }}>
                {ejemplo?.order_id.slice(0, 8)}
              </Typography>
              <Chip
                size="small"
                label={ejemplo?.decision}
                color={
                  ejemplo?.decision === "BLOCKED"
                    ? "error"
                    : ejemplo?.decision === "REVIEW"
                    ? "warning"
                    : "success"
                }
                sx={{ fontWeight: 800, fontSize: "0.68rem" }}
              />
              <Typography variant="caption" color="text.secondary">
                Evaluado en {ejemplo?.detection_time_ms?.toFixed(1) ?? "—"} ms
              </Typography>
            </Stack>

            {/* Fila de la base */}
            <Stack direction="row" spacing={2} sx={{ alignItems: "center", py: 1 }}>
              <Box sx={{ flex: { xs: "1 1 40%", md: "0 0 30%" }, minWidth: 0 }}>
                <Typography variant="body2" sx={{ fontWeight: 700, color: "text.secondary" }}>
                  Punto de partida
                </Typography>
              </Box>
              <Box sx={{ flex: 1, display: { xs: "none", md: "block" } }} />
              <Typography
                variant="body2"
                sx={{ fontFamily: "monospace", fontWeight: 700, minWidth: 68, textAlign: "right", color: "text.secondary" }}
              >
                {base?.toFixed(4)}
              </Typography>
            </Stack>

            {cuenta.aportes.map((a) => {
              const meta = VARIABLES[a.variable];
              return (
                <Stack
                  key={a.variable}
                  direction="row"
                  spacing={2}
                  sx={{ alignItems: "center", py: 1, borderTop: "1px solid", borderColor: "divider" }}
                >
                  <Box sx={{ flex: { xs: "1 1 40%", md: "0 0 30%" }, minWidth: 0 }}>
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>
                      {meta?.nombre ?? a.variable}
                    </Typography>
                    {typeof a.valor === "number" && meta && (
                      <Typography variant="caption" color="text.secondary">
                        {meta.formato(a.valor)}
                      </Typography>
                    )}
                  </Box>

                  <Box sx={{ flex: 1, display: { xs: "none", md: "block" } }}>
                    <Tooltip
                      title={
                        a.aporte > 0
                          ? "Empuja hacia fraude"
                          : "Empuja hacia compra legítima"
                      }
                    >
                      <Box>
                        <BarraDeAporte aporte={a.aporte} maximo={cuenta.maximo} tonos={tonos} />
                      </Box>
                    </Tooltip>
                  </Box>

                  <Typography
                    variant="body2"
                    sx={{
                      fontFamily: "monospace",
                      fontWeight: 800,
                      minWidth: 68,
                      textAlign: "right",
                      color: a.aporte > 0 ? tonos.textoFraude : tonos.textoLegitima,
                    }}
                  >
                    {a.aporte > 0 ? "+" : ""}
                    {a.aporte.toFixed(4)}
                  </Typography>
                </Stack>
              );
            })}

            <Stack
              direction="row"
              spacing={2}
              sx={{ alignItems: "center", py: 1.4, borderTop: "2px solid", borderColor: "divider", mt: 0.5 }}
            >
              <Box sx={{ flex: { xs: "1 1 40%", md: "0 0 30%" } }}>
                <Typography variant="body2" sx={{ fontWeight: 800 }}>
                  Suma
                </Typography>
              </Box>
              <Box sx={{ flex: 1, display: { xs: "none", md: "block" } }} />
              <Typography
                variant="body2"
                sx={{ fontFamily: "monospace", fontWeight: 800, minWidth: 68, textAlign: "right" }}
              >
                {cuenta.logit.toFixed(4)}
              </Typography>
            </Stack>

            <Box sx={{ mt: 1.5, pt: 1.5, borderTop: "1px solid", borderColor: "divider" }}>
              {/* El exponente va entre paréntesis: con una suma negativa,
                  "e^−−0.1026" se lee fatal. */}
              <Formula>
                puntaje = 1 / (1 + e^−({cuenta.logit.toFixed(4)})) ={" "}
                <Box component="span" sx={{ fontWeight: 800 }}>
                  {(cuenta.probabilidad * 100).toFixed(1)} %
                </Box>
              </Formula>
              <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 1 }}>
                El puntaje que guardó el sistema para este pedido fue{" "}
                {((ejemplo?.fraud_score ?? 0) * 100).toFixed(1)} %: la cuenta cierra.
              </Typography>
            </Box>
          </Box>
        )}

        {/* ── 4. De la probabilidad a la decisión ─────────────────────── */}
        <Typography variant="subtitle2" sx={{ fontWeight: 800, mt: 3.5, mb: 1 }}>
          4. El puntaje cae en una de tres bandas
        </Typography>

        <Box sx={{ display: "flex", height: 30, borderRadius: 1, overflow: "hidden", mb: 1 }}>
          {bandas.map((b) => (
            <Box
              key={b.etiqueta}
              sx={{
                width: `${(b.hasta - b.desde) * 100}%`,
                bgcolor: b.color,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <Typography sx={{ fontSize: "0.7rem", fontWeight: 800, color: "#FFFFFF", whiteSpace: "nowrap", px: 0.5 }}>
                {b.etiqueta}
              </Typography>
            </Box>
          ))}
        </Box>
        <Stack direction="row" sx={{ justifyContent: "space-between", mb: 2 }}>
          {[0, modelo?.approve_below ?? 0.35, modelo?.block_above ?? 0.8, 1].map((v, i) => (
            <Typography key={i} variant="caption" sx={{ color: "text.disabled", fontFamily: "monospace" }}>
              {v}
            </Typography>
          ))}
        </Stack>

        <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 820, lineHeight: 1.75 }}>
          Los dos umbrales no están escritos a mano: se eligen probando todos los pares
          posibles y quedándose con el que menos dinero le cuesta a la tienda, entre los que
          caben en lo que se puede revisar a mano (15 % de los pedidos) y detectan al menos
          el 80 % del fraude. Aprobar un fraude cuesta la mercadería más el contracargo;
          bloquear una compra buena cuesta el margen de esa venta; revisar cuesta el tiempo
          de una persona.
        </Typography>
      </CardContent>
    </Card>
  );
}
