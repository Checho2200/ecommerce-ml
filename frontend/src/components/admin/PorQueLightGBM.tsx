"use client";

/**
 * Por qué LightGBM y no otro clasificador.
 *
 * El trabajo se titula «sistema web basado en LightGBM», así que la primera
 * pregunta que recibe es por qué ese algoritmo. La respuesta estaba en un
 * informe dentro del repositorio —`ml/informes/comparacion_de_modelos.md`—,
 * que es exactamente donde no la busca quien está mirando el sistema.
 *
 * Aquí está la misma tabla: los mismos datos, la misma partición de prueba y
 * el mismo criterio de costo para todos los modelos. Se incluyen a propósito
 * dos que no son de aprendizaje automático: unas reglas heurísticas —lo que
 * haría la tienda sin modelo— y un clasificador trivial, que marca el suelo.
 * Sin ese suelo, «AUC-PR de 0.70» no significa nada.
 */

import {
  Alert,
  Box,
  Card,
  CardContent,
  Chip,
  Skeleton,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Tooltip,
  Typography,
} from "@mui/material";
import EmojiEventsOutlinedIcon from "@mui/icons-material/EmojiEventsOutlined";

import type { ModelComparisonResponse } from "@/lib/api";

const soles = (monto: number) =>
  `S/ ${monto.toLocaleString("es-PE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

const COLUMNAS: { titulo: string; ayuda: string }[] = [
  { titulo: "Modelo", ayuda: "Todos entrenados y medidos sobre los mismos datos." },
  {
    titulo: "AUC-PR",
    ayuda:
      "Área bajo la curva precisión-exhaustividad. Es la medida que importa cuando una clase es rara: a diferencia del AUC-ROC, no se deja engañar por el 93 % de compras legítimas.",
  },
  { titulo: "AUC-ROC", ayuda: "Capacidad de ordenar por riesgo, sin fijar umbral." },
  { titulo: "Precisión", ayuda: "De lo que frenó, cuánto era fraude de verdad." },
  { titulo: "Exhaustividad", ayuda: "De todo el fraude, cuánto llegó a frenar." },
  { titulo: "Fraudes que pasaron", ayuda: "Cuántos aprobó siendo fraude." },
  { titulo: "Ventas frenadas", ayuda: "Cuántas compras buenas bloqueó." },
  {
    titulo: "Pérdida",
    ayuda:
      "Los dos errores puestos en soles con el mismo criterio de costo. Es la comparación que decide, porque un modelo puede acertar más y costar más.",
  },
];

export default function PorQueLightGBM({
  datos,
  cargando,
}: {
  datos: ModelComparisonResponse | null;
  cargando: boolean;
}) {
  const filas = datos?.resultados ?? [];
  // El que menos cuesta, que es el criterio con el que se eligió.
  const menorPerdida = filas.length
    ? Math.min(...filas.map((f) => f.perdida_total))
    : 0;

  return (
    <Card elevation={0} sx={{ border: "1px solid", borderColor: "divider", borderRadius: 3 }}>
      <CardContent sx={{ p: 3 }}>
        <Typography variant="subtitle1" sx={{ fontWeight: 800 }}>
          Por qué LightGBM
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, mb: 2.5, maxWidth: 860 }}>
          Cinco alternativas entrenadas sobre los mismos datos y medidas sobre la misma
          partición de prueba, con el mismo criterio de costo. Las dos últimas no son
          modelos: son las reglas que aplicaría la tienda sin uno y un clasificador
          trivial. Están para marcar el suelo — sin él, un número suelto no dice si el
          modelo aporta algo.
        </Typography>

        {cargando ? (
          <Skeleton variant="rectangular" height={220} sx={{ borderRadius: 2 }} />
        ) : !datos?.disponible ? (
          <Alert severity="info" sx={{ borderRadius: 2 }}>
            Todavía no hay comparación. La genera <code>python -m ml.baselines</code> y se
            guarda en <code>ml/informes/comparacion_de_modelos.json</code>.
          </Alert>
        ) : (
          <>
            <Box sx={{ overflowX: "auto" }}>
              <Table size="small" sx={{ minWidth: 860 }}>
                <TableHead>
                  <TableRow>
                    {COLUMNAS.map((c, i) => (
                      <TableCell
                        key={c.titulo}
                        align={i === 0 ? "left" : "right"}
                        sx={{
                          fontWeight: 700,
                          fontSize: "0.7rem",
                          textTransform: "uppercase",
                          color: "text.secondary",
                          whiteSpace: "nowrap",
                        }}
                      >
                        <Tooltip title={c.ayuda}>
                          <span style={{ borderBottom: "1px dotted currentColor", cursor: "help" }}>
                            {c.titulo}
                          </span>
                        </Tooltip>
                      </TableCell>
                    ))}
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filas.map((fila) => {
                    const esElElegido = fila.perdida_total === menorPerdida;
                    return (
                      <TableRow
                        key={fila.modelo}
                        hover
                        sx={esElElegido ? { bgcolor: "action.hover" } : undefined}
                      >
                        <TableCell sx={{ fontWeight: esElElegido ? 800 : 600, whiteSpace: "nowrap" }}>
                          {fila.modelo}
                          {esElElegido && (
                            <Chip
                              icon={<EmojiEventsOutlinedIcon sx={{ fontSize: 14 }} />}
                              label="el elegido"
                              size="small"
                              color="success"
                              sx={{ ml: 1, height: 20, fontSize: "0.65rem", fontWeight: 700 }}
                            />
                          )}
                        </TableCell>
                        <TableCell align="right" sx={{ fontWeight: 800 }}>
                          {fila.average_precision.toFixed(4)}
                        </TableCell>
                        <TableCell align="right">{fila.roc_auc.toFixed(4)}</TableCell>
                        <TableCell align="right">{(fila.precision * 100).toFixed(1)}%</TableCell>
                        <TableCell align="right">{(fila.recall * 100).toFixed(1)}%</TableCell>
                        <TableCell align="right">{fila.fraudes_aprobados}</TableCell>
                        <TableCell align="right">{fila.legitimos_bloqueados}</TableCell>
                        <TableCell
                          align="right"
                          sx={{ whiteSpace: "nowrap", fontWeight: esElElegido ? 800 : 400 }}
                        >
                          {soles(fila.perdida_total)}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </Box>

            <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 2, lineHeight: 1.7 }}>
              Medido sobre {datos.particion_de_prueba ?? 0} transacciones que ninguno de los
              modelos vio durante su entrenamiento
              {datos.detalle_de_los_datos ? `, de ${datos.detalle_de_los_datos}` : ""}. La
              comparación la genera <code>ml/baselines.py</code> y se rehace con cada
              entrenamiento, así que la tabla no puede quedarse desfasada respecto al modelo
              que está sirviendo.
            </Typography>
          </>
        )}
      </CardContent>
    </Card>
  );
}
