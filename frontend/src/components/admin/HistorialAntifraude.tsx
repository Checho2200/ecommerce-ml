"use client";

/**
 * Historial del modelo: cuántas compras evaluó y cuántas dejó pasar, en el
 * tiempo.
 *
 * Las métricas generales dicen cómo va el modelo hoy; esto dice cómo ha ido, y
 * son preguntas distintas: un promedio sobre toda la vida de la tienda esconde
 * que los bloqueos se dispararon la semana pasada.
 *
 * El gráfico separa solo dos cosas —lo que pasó al cobro y lo que se retuvo—
 * porque esa es la lectura de un vistazo; el desglose exacto entre "en
 * revisión" y "bloqueada", con los montos, está en la tabla de abajo. Y la
 * tabla no es un extra: un color por sí solo nunca debe ser la única forma de
 * leer un dato.
 *
 * La escala sola no alcanzaba. Respondía "los últimos treinta días" pero no
 * "el 14 de agosto" ni "el trimestre que voy a citar", que es justo lo que se
 * pregunta cuando alguien tiene delante una fecha concreta. De ahí los dos
 * calendarios: acotan el tramo, y el mismo tramo se lleva el Excel, porque un
 * archivo que cubre otras fechas que la pantalla de la que salió no sirve como
 * evidencia de nada.
 */

import { useState } from "react";
import {
  Box,
  Button,
  Card,
  CardContent,
  Skeleton,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  MenuItem,
  TextField,
  Typography,
  useTheme,
} from "@mui/material";
import DownloadOutlinedIcon from "@mui/icons-material/FileDownloadOutlined";
import RestartAltIcon from "@mui/icons-material/RestartAlt";
import type {
  EscalaDelHistorial,
  FraudHistoryPeriod,
  FraudHistoryResponse,
} from "@/lib/api";

// La lista de escalas la define el cliente de la API, que es quien tiene que
// coincidir con lo que valida el backend. Aquí solo se le pone nombre corto.
export type Granularidad = EscalaDelHistorial;

const OPCIONES: { valor: Granularidad; etiqueta: string }[] = [
  { valor: "day", etiqueta: "Diario" },
  { valor: "week", etiqueta: "Semanal" },
  { valor: "month", etiqueta: "Mensual" },
  { valor: "bimester", etiqueta: "Bimestral" },
  { valor: "quarter", etiqueta: "Trimestral" },
  { valor: "semester", etiqueta: "Semestral" },
  { valor: "year", etiqueta: "Anual" },
];

/**
 * Los dos colores del gráfico.
 *
 * Azul y naranja, y no verde y rojo: "retenida" no es un error, es el modelo
 * haciendo su trabajo, así que pintarla de rojo diría algo que no es. Además
 * el par verde/rojo es justo el que no distingue la forma más común de
 * daltonismo, mientras que éste se separa con holgura en las tres simulaciones
 * y llega al contraste mínimo sobre los dos fondos del panel.
 */
const COLORES = {
  claro: { paso: "#2a78d6", retenida: "#eb6834" },
  oscuro: { paso: "#3987e5", retenida: "#d95926" },
};

const soles = (monto: number) =>
  `S/ ${monto.toLocaleString("es-PE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

/**
 * Hoy según el reloj de la tienda, en AAAA-MM-DD.
 *
 * Se pide en la zona de Lima y no la del navegador porque es el tope de los
 * dos calendarios: un administrador que abra el panel desde otro huso vería
 * habilitado un día que para la tienda todavía no ha empezado, elegiría ese
 * rango y recibiría un período vacío sin entender por qué. El formato "en-CA"
 * es el atajo estándar para que `toLocaleDateString` devuelva ISO.
 */
function hoyEnLaTienda(): string {
  return new Date().toLocaleDateString("en-CA", { timeZone: "America/Lima" });
}

/**
 * Una fecha ISO escrita para leer.
 *
 * Se parte a mano en vez de pasarla por `new Date(cadena)`, por lo mismo que
 * `etiquetaDePeriodo`: ese constructor la interpreta como UTC y en Perú la
 * mostraría corrida un día hacia atrás.
 */
function fechaLegible(iso: string): string {
  const [anio, mes, dia] = iso.split("-").map(Number);
  return new Date(anio, mes - 1, dia).toLocaleDateString("es-PE", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

/**
 * Cómo se nombra un período según la escala que se esté mirando.
 *
 * La fecha llega como AAAA-MM-DD y se parte a mano en vez de pasarla por
 * `new Date(cadena)`: ese constructor la interpreta como UTC y en Perú la
 * mostraría corrida un día hacia atrás, justo el error que el agrupamiento del
 * backend se cuida de evitar.
 */
function etiquetaDePeriodo(iso: string, granularidad: Granularidad, largo = false) {
  const [anio, mes, dia] = iso.split("-").map(Number);
  const fecha = new Date(anio, mes - 1, dia);

  if (granularidad === "year") return String(anio);

  if (granularidad === "month") {
    return fecha.toLocaleDateString("es-PE", {
      month: largo ? "long" : "short",
      year: largo ? "numeric" : "2-digit",
    });
  }

  if (granularidad === "quarter" || granularidad === "semester") {
    const tamano = granularidad === "quarter" ? 3 : 6;
    const numero = Math.floor((mes - 1) / tamano) + 1;
    const nombre = granularidad === "quarter" ? "trimestre" : "semestre";
    const inicial = granularidad === "quarter" ? "T" : "S";
    return largo
      ? `${numero}.º ${nombre} de ${anio}`
      : `${inicial}${numero} ${String(anio).slice(2)}`;
  }

  if (granularidad === "bimester") {
    // `mes` es 1-based y el constructor de Date es 0-based, así que pasarle
    // `mes` sin restar uno da justo el mes siguiente: el segundo del bimestre.
    const segundo = new Date(anio, mes, 1);
    const desde = fecha.toLocaleDateString("es-PE", { month: "short" });
    const hasta = segundo.toLocaleDateString("es-PE", { month: "short" });
    return largo ? `${desde}–${hasta} de ${anio}` : `${desde}–${hasta}`;
  }

  const corta = fecha.toLocaleDateString("es-PE", { day: "numeric", month: "short" });
  return granularidad === "week" && largo ? `Semana del ${corta}` : corta;
}

/**
 * Barras apiladas, una por período.
 *
 * La altura total es cuántas compras evaluó el modelo; el corte, cuántas dejó
 * pasar. Está hecho con cajas y no con una librería de gráficos: sumar una
 * dependencia entera al proyecto por un único gráfico no sale a cuenta.
 */
function BarrasApiladas({
  periodos,
  granularidad,
}: {
  periodos: FraudHistoryPeriod[];
  granularidad: Granularidad;
}) {
  const tema = useTheme();
  const color = tema.palette.mode === "dark" ? COLORES.oscuro : COLORES.claro;
  const [encima, setEncima] = useState<number | null>(null);

  const ALTO = 190;
  const GRUESO = 22; // Las barras no llenan su carril: el aire las separa.
  const SEPARACION = 2; // El corte del apilado se hace con un hueco, no con un borde.

  const maximo = Math.max(1, ...periodos.map((p) => p.evaluations));

  // Con muchos períodos no caben todas las fechas debajo: se rotulan algunas y
  // el resto se lee en el globo al pasar el ratón.
  const cada = Math.ceil(periodos.length / 12);

  return (
    <Box sx={{ position: "relative" }}>
      <Box sx={{ position: "relative", height: ALTO }}>
        {/* Rejilla: tiene que verse menos que los datos. */}
        {[0, 0.5, 1].map((f) => (
          <Box
            key={f}
            aria-hidden
            sx={{
              position: "absolute",
              left: 0,
              right: 0,
              bottom: f * ALTO,
              height: "1px",
              bgcolor: "divider",
            }}
          />
        ))}

        {/* Las barras se colocan con flex y no dentro de un SVG escalado: así
            el grosor se mantiene en píxeles reales sea cual sea el ancho de la
            pantalla, en vez de estirarse con ella. */}
        <Stack
          direction="row"
          sx={{ position: "absolute", inset: 0, alignItems: "flex-end" }}
          onMouseLeave={() => setEncima(null)}
        >
          {periodos.map((p, i) => {
            const total = (p.evaluations / maximo) * (ALTO - 8);
            const retenidas = p.in_review + p.blocked;
            const altoRetenidas = p.evaluations ? (retenidas / p.evaluations) * total : 0;
            const altoPasaron = Math.max(total - altoRetenidas, 0);

            return (
              <Box
                key={p.period_start}
                onMouseEnter={() => setEncima(i)}
                sx={{
                  flex: 1,
                  minWidth: 0,
                  height: "100%",
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "flex-end",
                  alignItems: "center",
                  // La zona sensible ocupa el carril entero: apuntar con el
                  // ratón a una barra de 22 px es innecesariamente difícil.
                  bgcolor: encima === i ? "action.hover" : "transparent",
                }}
              >
                {altoRetenidas > 0 && (
                  <Box
                    sx={{
                      width: GRUESO,
                      maxWidth: "80%",
                      height: Math.max(altoRetenidas - SEPARACION, 1),
                      bgcolor: color.retenida,
                      // Redondeado solo en el extremo del dato.
                      borderRadius: "3px 3px 0 0",
                      mb: `${SEPARACION}px`,
                    }}
                  />
                )}
                {altoPasaron > 0 && (
                  <Box
                    sx={{
                      width: GRUESO,
                      maxWidth: "80%",
                      height: Math.max(altoPasaron, 1),
                      bgcolor: color.paso,
                      // Cuadrado abajo, apoyado en la línea base.
                      borderRadius: altoRetenidas > 0 ? 0 : "3px 3px 0 0",
                    }}
                  />
                )}
              </Box>
            );
          })}
        </Stack>
      </Box>

      <Stack direction="row" sx={{ mt: 1 }}>
        {periodos.map((p, i) => (
          <Box key={p.period_start} sx={{ flex: 1, textAlign: "center", minWidth: 0 }}>
            <Typography
              variant="caption"
              sx={{
                color: encima === i ? "text.primary" : "text.disabled",
                fontSize: "0.66rem",
                whiteSpace: "nowrap",
                visibility: i % cada === 0 || encima === i ? "visible" : "hidden",
              }}
            >
              {etiquetaDePeriodo(p.period_start, granularidad)}
            </Typography>
          </Box>
        ))}
      </Stack>

      {encima !== null && periodos[encima] && (
        <Box
          sx={{
            position: "absolute",
            top: 0,
            right: 0,
            bgcolor: "background.paper",
            border: "1px solid",
            borderColor: "divider",
            borderRadius: 2,
            px: 1.5,
            py: 1,
            pointerEvents: "none",
            boxShadow: 3,
            minWidth: 170,
          }}
        >
          <Typography variant="caption" sx={{ fontWeight: 800, display: "block" }}>
            {etiquetaDePeriodo(periodos[encima].period_start, granularidad, true)}
          </Typography>
          {[
            { texto: "Pasaron", valor: periodos[encima].approved, tono: color.paso },
            {
              texto: "No pasaron",
              valor: periodos[encima].in_review + periodos[encima].blocked,
              tono: color.retenida,
            },
          ].map((fila) => (
            <Stack
              key={fila.texto}
              direction="row"
              spacing={1}
              sx={{ alignItems: "center", mt: 0.5 }}
            >
              <Box sx={{ width: 9, height: 9, bgcolor: fila.tono, flexShrink: 0, borderRadius: 0.5 }} />
              <Typography variant="caption" sx={{ color: "text.secondary", flexGrow: 1 }}>
                {fila.texto}
              </Typography>
              <Typography variant="caption" sx={{ fontWeight: 800 }}>
                {fila.valor}
              </Typography>
            </Stack>
          ))}
        </Box>
      )}
    </Box>
  );
}

export default function HistorialAntifraude({
  datos,
  cargando,
  granularidad,
  onGranularidad,
  desde,
  hasta,
  onRango,
  onExportar,
  exportando,
}: {
  datos: FraudHistoryResponse | null;
  cargando: boolean;
  granularidad: Granularidad;
  onGranularidad: (g: Granularidad) => void;
  // El rango elegido, en AAAA-MM-DD. Cadenas vacías significan "sin acotar",
  // que es la ventana que termina hoy.
  desde: string;
  hasta: string;
  onRango: (desde: string, hasta: string) => void;
  onExportar: () => void;
  exportando: boolean;
}) {
  const tema = useTheme();
  const color = tema.palette.mode === "dark" ? COLORES.oscuro : COLORES.claro;
  const periodos = datos?.periods ?? [];
  const hoy = hoyEnLaTienda();
  const hayRango = Boolean(desde || hasta);

  // La tabla solo repite los períodos con algo dentro: una fila de ceros por
  // cada día tranquilo enterraría a los que sí tienen datos. El gráfico sí los
  // dibuja, porque ahí los huecos son parte de la forma de la curva.
  const conDatos = periodos.filter((p) => p.evaluations > 0).slice().reverse();

  const totalPaso = datos?.total_approved ?? 0;
  const totalRetenido = datos?.total_held ?? 0;
  const totalEvaluado = datos?.total_evaluations ?? 0;

  return (
    <Card elevation={0} sx={{ border: "1px solid", borderColor: "divider", borderRadius: 3 }}>
      <CardContent sx={{ p: 3 }}>
        <Stack
          direction={{ xs: "column", lg: "row" }}
          spacing={2}
          sx={{ justifyContent: "space-between", alignItems: { lg: "flex-end" }, mb: 1.5 }}
        >
          <Box>
            <Typography variant="subtitle1" sx={{ fontWeight: 800 }}>
              Historial de indicadores
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              Compras evaluadas por período, y cuántas pasaron al cobro.
            </Typography>
          </Box>

          {/* Los controles envuelven en varias líneas en vez de encogerse: en
              un teléfono, cuatro campos en una fila dejan cada uno demasiado
              estrecho para leer la fecha que tiene dentro. */}
          <Stack
            direction="row"
            sx={{ alignItems: "center", flexWrap: "wrap", gap: 1.5 }}
          >
            {/* Los dos calendarios son <input type="date">: abren el selector
                nativo del sistema —también en el teléfono— y devuelven la
                fecha ya en AAAA-MM-DD, que es como la espera la API. Traer una
                librería de calendarios para esto sería sumar una dependencia
                entera al proyecto por dos campos. */}
            <TextField
              type="date"
              size="small"
              label="Desde"
              value={desde}
              onChange={(e) => onRango(e.target.value, hasta)}
              // Sin esto la etiqueta se monta encima de la fecha mientras el
              // campo está vacío: un input de fecha nunca se ve vacío del todo.
              slotProps={{
                inputLabel: { shrink: true },
                // No se puede empezar después de donde se termina, ni elegir
                // un día que para la tienda todavía no ha llegado.
                htmlInput: { max: hasta || hoy },
              }}
              sx={{ minWidth: 155 }}
            />
            <TextField
              type="date"
              size="small"
              label="Hasta"
              value={hasta}
              onChange={(e) => onRango(desde, e.target.value)}
              slotProps={{
                inputLabel: { shrink: true },
                htmlInput: { min: desde || undefined, max: hoy },
              }}
              sx={{ minWidth: 155 }}
            />

            {/* Una lista y no una fila de botones: con siete escalas, los
                botones se salen de la tarjeta en un teléfono. */}
            <TextField
              select
              size="small"
              label="Escala"
              value={granularidad}
              onChange={(e) => onGranularidad(e.target.value as Granularidad)}
              sx={{ minWidth: 140 }}
            >
              {OPCIONES.map((o) => (
                <MenuItem key={o.valor} value={o.valor} sx={{ fontWeight: 600 }}>
                  {o.etiqueta}
                </MenuItem>
              ))}
            </TextField>

            {/* El archivo lo arma el backend con los mismos números y el mismo
                rango que se ven en pantalla, así que no puede desviarse. */}
            <Button
              size="small"
              variant="outlined"
              startIcon={<DownloadOutlinedIcon />}
              onClick={onExportar}
              disabled={exportando || cargando}
              sx={{ textTransform: "none", fontWeight: 700, borderRadius: 2, whiteSpace: "nowrap" }}
            >
              {exportando ? "Generando…" : "Exportar a Excel"}
            </Button>
          </Stack>
        </Stack>

        {/* Qué tramo se está mirando de verdad. No siempre es el que se pidió:
            las fechas se redondean al período que las contiene —del 14 al 20 de
            agosto, en escala mensual, es agosto entero— y una fecha final
            futura se recorta a hoy. Decirlo evita la lectura equivocada de un
            porcentaje, que es el error caro en una pantalla como ésta. */}
        <Stack
          direction="row"
          sx={{ alignItems: "center", flexWrap: "wrap", gap: 1, mb: 2 }}
        >
          <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
            {datos
              ? datos.range_start === datos.range_end
                ? `Mostrando ${fechaLegible(datos.range_start)}`
                : `Mostrando del ${fechaLegible(datos.range_start)} al ${fechaLegible(datos.range_end)}`
              : " "}
          </Typography>
          {hayRango && (
            <Button
              size="small"
              startIcon={<RestartAltIcon />}
              onClick={() => onRango("", "")}
              sx={{ textTransform: "none", fontWeight: 700, py: 0, minWidth: 0 }}
            >
              Quitar el rango
            </Button>
          )}
        </Stack>

        {/* Con dos series la leyenda va siempre: el color no puede ser lo único
            que distinga una de la otra. */}
        <Stack direction="row" spacing={2.5} sx={{ mb: 2.5, flexWrap: "wrap" }}>
          {[
            { texto: `Pasaron al cobro (${totalPaso})`, tono: color.paso },
            { texto: `No pasaron (${totalRetenido})`, tono: color.retenida },
          ].map((s) => (
            <Stack key={s.texto} direction="row" spacing={0.9} sx={{ alignItems: "center" }}>
              <Box sx={{ width: 11, height: 11, bgcolor: s.tono, borderRadius: 0.5 }} />
              <Typography variant="caption" sx={{ color: "text.secondary", fontWeight: 600 }}>
                {s.texto}
              </Typography>
            </Stack>
          ))}
        </Stack>

        {cargando ? (
          <Skeleton variant="rectangular" height={215} sx={{ borderRadius: 2 }} />
        ) : totalEvaluado === 0 ? (
          <Box
            sx={{
              py: 6,
              textAlign: "center",
              border: "1px dashed",
              borderColor: "divider",
              borderRadius: 2,
            }}
          >
            <Typography variant="body2" color="text.secondary">
              Todavía no hay compras evaluadas en este rango.
            </Typography>
          </Box>
        ) : (
          <BarrasApiladas periodos={periodos} granularidad={granularidad} />
        )}

        {/* ── El mismo dato, en números exactos ─────────────────────── */}
        {!cargando && conDatos.length > 0 && (
          <Box sx={{ mt: 4 }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 800, mb: 0.5 }}>
              Reporte de pasados y no pasados
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 2 }}>
              «Pasaron» son las compras que el modelo dejó seguir hasta el cobro. «No pasaron»
              son las que retuvo —en revisión o bloqueadas— y que nunca llegaron a la pasarela
              de pago.
            </Typography>

            <Box sx={{ overflowX: "auto" }}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    {[
                      "Período",
                      "Evaluadas",
                      "Pasaron",
                      "En revisión",
                      "Bloqueadas",
                      "% que pasó",
                      "Fraudes conf.",
                      "Detectados",
                      "No detectado",
                      "Precisión",
                      "Tiempo",
                      "Monto cobrable",
                      "Monto retenido",
                    ].map((h, i) => (
                      <TableCell
                        key={h}
                        align={i === 0 ? "left" : "right"}
                        sx={{
                          fontWeight: 700,
                          fontSize: "0.7rem",
                          textTransform: "uppercase",
                          color: "text.secondary",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {h}
                      </TableCell>
                    ))}
                  </TableRow>
                </TableHead>
                <TableBody>
                  {conDatos.map((p) => (
                    <TableRow key={p.period_start} hover>
                      <TableCell sx={{ whiteSpace: "nowrap", fontWeight: 600 }}>
                        {etiquetaDePeriodo(p.period_start, granularidad, true)}
                      </TableCell>
                      <TableCell align="right">{p.evaluations}</TableCell>
                      <TableCell align="right" sx={{ fontWeight: 700 }}>
                        {p.approved}
                      </TableCell>
                      <TableCell align="right">{p.in_review}</TableCell>
                      <TableCell align="right">{p.blocked}</TableCell>
                      <TableCell align="right">
                        {((p.approved / p.evaluations) * 100).toFixed(0)}%
                      </TableCell>
                      <TableCell align="right">{p.actual_frauds}</TableCell>
                      {/* Las dos tasas van en guion, y no en cero, cuando el
                          período no tuvo ningún fraude confirmado: un cero
                          diría "no se detectó nada". */}
                      <TableCell align="right" sx={{ fontWeight: 700 }}>
                        {p.detection_rate === null
                          ? "—"
                          : `${(p.detection_rate * 100).toFixed(0)}%`}
                      </TableCell>
                      <TableCell align="right">
                        {p.undetected_rate === null
                          ? "—"
                          : `${(p.undetected_rate * 100).toFixed(0)}%`}
                      </TableCell>
                      {/* De lo que el modelo frenó y alguien comprobó, cuánto
                          era fraude de verdad. En guion mientras no se haya
                          revisado ninguna alerta del período: sin comprobar no
                          hay precisión, y un 0 % acusaría al modelo de fallar
                          en algo que nadie miró. */}
                      <TableCell align="right">
                        {p.precision == null ? "—" : `${(p.precision * 100).toFixed(0)}%`}
                      </TableCell>
                      <TableCell align="right" sx={{ whiteSpace: "nowrap" }}>
                        {p.average_detection_time_ms.toFixed(1)} ms
                      </TableCell>
                      <TableCell align="right" sx={{ whiteSpace: "nowrap" }}>
                        {soles(p.approved_amount)}
                      </TableCell>
                      <TableCell align="right" sx={{ whiteSpace: "nowrap" }}>
                        {soles(p.held_amount)}
                      </TableCell>
                    </TableRow>
                  ))}

                  <TableRow>
                    <TableCell sx={{ fontWeight: 800, borderTop: "2px solid", borderColor: "divider" }}>
                      Total del rango
                    </TableCell>
                    {[
                      totalEvaluado,
                      totalPaso,
                      conDatos.reduce((n, p) => n + p.in_review, 0),
                      conDatos.reduce((n, p) => n + p.blocked, 0),
                      `${totalEvaluado ? ((totalPaso / totalEvaluado) * 100).toFixed(0) : 0}%`,
                      datos?.total_actual_frauds ?? 0,
                      // Los totales salen de sumar los casos y dividir una
                      // sola vez, no de promediar las tasas de cada período:
                      // ese promedio le daría el mismo peso a un mes con un
                      // fraude que a uno con cien.
                      datos?.detection_rate == null
                        ? "—"
                        : `${(datos.detection_rate * 100).toFixed(0)}%`,
                      datos?.undetected_rate == null
                        ? "—"
                        : `${(datos.undetected_rate * 100).toFixed(0)}%`,
                      datos?.precision == null
                        ? "—"
                        : `${(datos.precision * 100).toFixed(0)}%`,
                      `${(datos?.average_detection_time_ms ?? 0).toFixed(1)} ms`,
                      soles(conDatos.reduce((n, p) => n + p.approved_amount, 0)),
                      soles(conDatos.reduce((n, p) => n + p.held_amount, 0)),
                    ].map((valor, i) => (
                      <TableCell
                        key={i}
                        align="right"
                        sx={{
                          fontWeight: 800,
                          whiteSpace: "nowrap",
                          borderTop: "2px solid",
                          borderColor: "divider",
                        }}
                      >
                        {valor}
                      </TableCell>
                    ))}
                  </TableRow>
                </TableBody>
              </Table>
            </Box>
          </Box>
        )}
      </CardContent>
    </Card>
  );
}
