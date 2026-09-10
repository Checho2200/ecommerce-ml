"use client";

/**
 * Los tres indicadores que mide la tesis, con la dirección en la que conviene
 * que se muevan.
 *
 * Un porcentaje suelto no dice nada: "42 %" solo significa algo cuando al lado
 * está escrito si eso debería subir o bajar. Por eso cada tarjeta lleva su
 * flecha y su leyenda, y por eso la flecha es del color que corresponde al
 * sentido —no al signo del cambio—: la tasa de fraude no detectado bajando es
 * una buena noticia.
 *
 * El mismo componente sirve para el Antifraude, donde va con todo el detalle,
 * y para el Dashboard, donde va en `compacto` y solo enseña las tres cifras.
 */

import { Box, Card, CardContent, Grid, Skeleton, Stack, Tooltip, Typography } from "@mui/material";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import TrendingDownIcon from "@mui/icons-material/TrendingDown";
import ShieldOutlinedIcon from "@mui/icons-material/ShieldOutlined";
import ReportGmailerrorredOutlinedIcon from "@mui/icons-material/ReportGmailerrorredOutlined";
import BoltOutlinedIcon from "@mui/icons-material/BoltOutlined";
import type { SvgIconComponent } from "@mui/icons-material";
import type { FraudHistoryResponse, FraudModelInfo } from "@/lib/api";
import { duracionLegible } from "@/lib/duracion";

type Direccion = "subir" | "bajar";

interface Indicador {
  clave: string;
  titulo: string;
  valor: string;
  detalle: string;
  explicacion: string;
  direccion: Direccion;
  icono: SvgIconComponent;
  /** Sin fraudes confirmados en el rango, la tasa no se puede calcular. */
  medible: boolean;
  /**
   * La fórmula de la tesis, escrita con los números de este rango.
   *
   * DTF y NFND dividen entre el total de transacciones, así que dan cifras muy
   * distintas de la tasa que encabeza la tarjeta. Van aquí, con la cuenta a la
   * vista, para que se puedan citar sin que nadie las confunda con el titular.
   */
  formula?: string | null;
  /**
   * Lo que el modelo midió al entrenarse, sobre datos que no había visto.
   *
   * Se enseña solo cuando el indicador todavía no se puede calcular con los
   * pedidos de la tienda. Una tienda sin contracargos confirmados no puede
   * decir qué proporción de fraude frena —y decir 0 % sería mentir—, pero sí
   * puede decir qué midió el modelo en su partición de prueba. Es el número
   * honesto que se puede enseñar mientras el otro no exista.
   */
  referencia: string | null;
}

const porcentaje = (v: number | null) => (v === null ? "—" : `${(v * 100).toFixed(1)} %`);

export function indicadoresDe(
  datos: FraudHistoryResponse | null,
  modelo?: FraudModelInfo | null
): Indicador[] {
  // Sin un solo fraude confirmado no hay nada que dividir: DTF y NFND salen en
  // guion, no en cero. Un cero diría «no se detectó nada» cuando lo cierto es
  // que no hay con qué medirlo.
  const medible = (datos?.total_actual_frauds ?? 0) > 0;

  // La tasa que el entrenamiento midió sobre su partición de prueba.
  const alEntrenarse = modelo?.detection_rate ?? null;
  const comoPorcentaje = (v: number) => `${(v * 100).toFixed(1)} %`;

  return [
    {
      clave: "detectados",
      titulo: "Tasa de fraudes detectados",
      valor: porcentaje(datos?.detection_rate ?? null),
      detalle: medible
        ? `${datos?.total_detected_frauds ?? 0} frenados de ${datos?.total_actual_frauds ?? 0} fraudes confirmados`
        : "Aún sin fraudes confirmados que medir",
      // La tarjeta enseña la exhaustividad y no DTF porque es la que responde
      // «de los fraudes que hubo, cuántos frenamos», que es la pregunta del
      // indicador. DTF, con el total de transacciones en el denominador, tiene
      // por techo la propia tasa de fraude de la tienda —con un 7 % de fraude
      // no puede pasar del 7 % ni detectándolos todos—, así que como titular
      // engaña: parece un suspenso cuando el sistema va bien. Se sigue
      // calculando y se enseña debajo, que es donde no se confunde con esto.
      explicacion:
        "De los fraudes confirmados, qué proporción frenó el sistema antes de cobrar.",
      formula:
        datos?.dtf == null
          ? null
          : `DTF = ${datos.total_detected_frauds} ÷ ${datos.total_evaluations} × 100 = ${(datos.dtf * 100).toFixed(1)} % del total de transacciones`,
      direccion: "subir",
      icono: ShieldOutlinedIcon,
      medible,
      referencia:
        medible || alEntrenarse === null
          ? null
          : `De cada 100 fraudes, el modelo frenó ${comoPorcentaje(alEntrenarse)} al entrenarse. Esa proporción —la exhaustividad— no es DTF: se divide entre los fraudes, no entre todas las compras.`,
    },
    {
      clave: "no-detectados",
      titulo: "Tasa de fraude no detectado",
      valor: porcentaje(datos?.undetected_rate ?? null),
      detalle: medible
        ? `${datos?.total_undetected_frauds ?? 0} se aprobaron de ${datos?.total_actual_frauds ?? 0} fraudes confirmados`
        : "Aún sin fraudes confirmados que medir",
      explicacion:
        "De los fraudes confirmados, qué proporción se aprobó igual y terminó en pérdida.",
      formula:
        datos?.nfnd == null
          ? null
          : `NFND = ${datos.total_undetected_frauds} ÷ ${datos.total_evaluations} × 100 = ${(datos.nfnd * 100).toFixed(1)} % del total de transacciones`,
      direccion: "bajar",
      icono: ReportGmailerrorredOutlinedIcon,
      medible,
      referencia:
        medible || alEntrenarse === null
          ? null
          : `Al entrenarse se le escapó el ${comoPorcentaje(1 - alEntrenarse)} sobre compras que no había visto.`,
    },
    {
      clave: "tiempo",
      titulo: "Tiempo de detección",
      valor: duracionLegible(datos?.average_detection_time_ms ?? 0),
      detalle: `Mediana de ${datos?.total_evaluations ?? 0} evaluaciones`,
      explicacion:
        "TD = tiempo final − tiempo inicial, cronometrado por el servicio alrededor de la evaluación de cada compra. Se da la mediana y no el promedio: si el rango cruza la entrada del modelo, mezcla evaluaciones que tardaban horas con otras de un milisegundo y la media no describe ninguna.",
      direccion: "bajar",
      icono: BoltOutlinedIcon,
      // El tiempo no necesita etiquetas: lo cronometra el propio servicio.
      medible: (datos?.total_evaluations ?? 0) > 0,
      referencia:
        (datos?.total_evaluations ?? 0) > 0 || modelo?.detection_time_ms == null
          ? null
          : `Al entrenarse tardó ${duracionLegible(modelo.detection_time_ms)} por compra.`,
    },
  ];
}

function Flecha({ direccion }: { direccion: Direccion }) {
  const Icono = direccion === "subir" ? TrendingUpIcon : TrendingDownIcon;
  return (
    <Stack direction="row" spacing={0.5} sx={{ alignItems: "center" }}>
      <Icono sx={{ fontSize: 16, color: "text.secondary" }} />
      <Typography variant="caption" sx={{ color: "text.secondary", fontWeight: 700 }}>
        Debe {direccion}
      </Typography>
    </Stack>
  );
}

export default function TarjetasDeIndicadores({
  datos,
  cargando,
  modelo = null,
  compacto = false,
}: {
  datos: FraudHistoryResponse | null;
  cargando: boolean;
  /**
   * La ficha del modelo, si la pantalla ya la tiene. Sirve para enseñar lo
   * que midió al entrenarse en los indicadores que todavía no se pueden
   * calcular con los pedidos de la tienda.
   */
  modelo?: FraudModelInfo | null;
  /** Versión reducida para el Dashboard: solo las tres cifras. */
  compacto?: boolean;
}) {
  const indicadores = indicadoresDe(datos, modelo);

  if (compacto) {
    return (
      <Stack
        direction={{ xs: "column", sm: "row" }}
        spacing={{ xs: 1.5, sm: 3 }}
        sx={{ flexWrap: "wrap" }}
      >
        {indicadores.map((i) => (
          <Tooltip key={i.clave} title={`${i.explicacion} Debe ${i.direccion}.`}>
            <Stack direction="row" spacing={1.2} sx={{ alignItems: "center" }}>
              <i.icono sx={{ fontSize: 20, color: "acento.main" }} />
              <Box>
                <Typography variant="caption" sx={{ color: "text.secondary", display: "block", lineHeight: 1.2 }}>
                  {i.titulo}
                </Typography>
                {cargando ? (
                  <Skeleton width={54} height={22} />
                ) : (
                  <Typography sx={{ fontWeight: 900, fontSize: "1.05rem", lineHeight: 1.25 }}>
                    {i.valor}
                  </Typography>
                )}
              </Box>
            </Stack>
          </Tooltip>
        ))}
      </Stack>
    );
  }

  return (
    <Grid container spacing={3}>
      {indicadores.map((i) => (
        <Grid size={{ xs: 12, md: 4 }} key={i.clave}>
          <Card
            elevation={0}
            sx={{ borderRadius: 3, border: "1px solid", borderColor: "divider", height: "100%" }}
          >
            <CardContent sx={{ p: 3 }}>
              <Stack
                direction="row"
                sx={{ justifyContent: "space-between", alignItems: "flex-start", mb: 1.5, gap: 1 }}
              >
                <Typography
                  variant="body2"
                  sx={{
                    color: "text.secondary",
                    fontWeight: 700,
                    textTransform: "uppercase",
                    fontSize: "0.7rem",
                    lineHeight: 1.4,
                  }}
                >
                  {i.titulo}
                </Typography>
                <i.icono sx={{ fontSize: 21, color: "acento.main", flexShrink: 0 }} />
              </Stack>

              {cargando ? (
                <Skeleton width={110} height={46} />
              ) : (
                <Typography
                  variant="h4"
                  sx={{ fontWeight: 900, color: i.medible ? "text.primary" : "text.disabled" }}
                >
                  {i.valor}
                </Typography>
              )}

              <Typography variant="caption" sx={{ color: "text.secondary", display: "block", mt: 0.8 }}>
                {i.detalle}
              </Typography>

              {/* Mientras la tienda no tenga con qué medir, se enseña lo que
                  midió el entrenamiento. Va marcado como lo que es —una
                  referencia de laboratorio, no el dato de la tienda— para que
                  nadie lo lea como si fuera lo segundo. */}
              {!cargando && i.referencia && (
                <Box
                  sx={{
                    mt: 1.5,
                    px: 1.5,
                    py: 1,
                    borderRadius: 1.5,
                    bgcolor: "action.hover",
                  }}
                >
                  <Typography
                    variant="caption"
                    sx={{ color: "text.secondary", display: "block", lineHeight: 1.6 }}
                  >
                    <Box component="span" sx={{ fontWeight: 800 }}>
                      Referencia del entrenamiento:{" "}
                    </Box>
                    {i.referencia}
                  </Typography>
                </Box>
              )}

              {/* La fórmula de la tesis con los números de este rango. Va
                  aparte y con la cuenta escrita porque su denominador es otro
                  —el total de transacciones— y da una cifra que no se puede
                  comparar con el titular de arriba. */}
              {!cargando && i.formula && (
                <Typography
                  variant="caption"
                  sx={{
                    mt: 1.5,
                    display: "block",
                    color: "text.secondary",
                    fontFamily: "monospace",
                    fontSize: "0.68rem",
                    lineHeight: 1.6,
                  }}
                >
                  {i.formula}
                </Typography>
              )}

              <Box sx={{ mt: 2, pt: 1.5, borderTop: "1px solid", borderColor: "divider" }}>
                <Flecha direccion={i.direccion} />
                <Typography
                  variant="caption"
                  sx={{ color: "text.secondary", display: "block", mt: 0.8, lineHeight: 1.6 }}
                >
                  {i.explicacion}
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      ))}
    </Grid>
  );
}
