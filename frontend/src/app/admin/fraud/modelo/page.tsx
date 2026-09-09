"use client";

/**
 * Antifraude · Modelo e indicadores: qué tan bien le va al modelo.
 *
 * Es la mitad analítica de lo que antes era una sola pantalla larguísima. Se
 * separó de la cola de revisión porque son dos usos distintos: la cola se
 * atiende hoy, y esto se consulta cuando alguien pregunta —un jurado, un
 * gerente— cuánto fraude está frenando el sistema de verdad.
 *
 * Quedan tres bloques y el orden sigue el de esas preguntas: por qué este
 * algoritmo y no otro, qué indicadores prometió mover, y cómo han ido en el
 * tiempo con su reporte descargable.
 *
 * La pantalla llegó a llevar también la aritmética de una decisión concreta
 * —el reparto SHAP de un pedido— y una tabla de precisión y exhaustividad.
 * Se retiraron a pedido: explicaban el método en vez de medirlo, que es para
 * lo que se abre esta pantalla. La explicación de cada pedido sigue donde se
 * necesita, guardada con su evaluación y a la vista en la cola de revisión.
 */

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Alert,
  Box,
  Button,
  Snackbar,
  Stack,
  Typography,
} from "@mui/material";
import FactCheckOutlinedIcon from "@mui/icons-material/FactCheckOutlined";

import PorQueLightGBM from "@/components/admin/PorQueLightGBM";
import TarjetasDeIndicadores from "@/components/admin/TarjetasDeIndicadores";
import HistorialAntifraude, { type Granularidad } from "@/components/admin/HistorialAntifraude";
import {
  api,
  type FraudHistoryResponse,
  type FraudModelInfo,
  type ModelComparisonResponse,
} from "@/lib/api";

export default function AdminFraudModelPage() {
  const [modelo, setModelo] = useState<FraudModelInfo | null>(null);
  const [comparacion, setComparacion] = useState<ModelComparisonResponse | null>(null);
  const [granularidad, setGranularidad] = useState<Granularidad>("month");
  // El tramo de calendario, en AAAA-MM-DD. Vacío es «la ventana que termina
  // hoy», que es con lo que abre la pantalla.
  const [rango, setRango] = useState({ desde: "", hasta: "" });
  const [cargando, setCargando] = useState(true);
  const [aviso, setAviso] = useState<{ texto: string; tipo: "success" | "error" } | null>(null);
  const [exportando, setExportando] = useState(false);

  // Qué se está pidiendo, en una sola cadena. Sirve para saber si lo que hay
  // en pantalla corresponde a lo que el usuario acaba de elegir; con la escala
  // sola no bastaba desde que además se puede acotar por fechas.
  const consulta = `${granularidad}|${rango.desde}|${rango.hasta}`;

  // El historial se guarda junto a la consulta con la que se pidió. Así "está
  // cargando" es algo que se deduce —lo que hay en pantalla todavía no es de
  // la consulta elegida— en lugar de un estado aparte que hay que encender a
  // mano dentro del efecto, que es lo que encadena un render de más en cada
  // cambio.
  const [historial, setHistorial] = useState<{
    datos: FraudHistoryResponse | null;
    consulta: string | null;
    fallo: string | null;
  }>({ datos: null, consulta: null, fallo: null });

  const cargandoHistorial = historial.consulta !== consulta;

  const avisar = (texto: string, tipo: "success" | "error" = "success") =>
    setAviso({ texto, tipo });

  // La ficha del modelo y la comparación no dependen de la escala elegida; el
  // historial sí. Separarlos evita volver a pedirlo todo al cambiar de escala.
  useEffect(() => {
    let vigente = true;
    Promise.all([api.fraud.model(), api.fraud.comparison()])
      .then(([info, tabla]) => {
        if (!vigente) return;
        setModelo(info);
        setComparacion(tabla);
      })
      .catch(() => {
        if (vigente) avisar("No se pudieron cargar los datos del modelo", "error");
      })
      .finally(() => {
        if (vigente) setCargando(false);
      });
    return () => {
      vigente = false;
    };
  }, []);

  useEffect(() => {
    let vigente = true;
    api.fraud
      .history({
        granularity: granularidad,
        startDate: rango.desde || undefined,
        endDate: rango.hasta || undefined,
      })
      .then((datos) => {
        if (vigente) setHistorial({ datos, consulta, fallo: null });
      })
      .catch((error: unknown) => {
        // La consulta se anota igual: si no, la pantalla se quedaría cargando
        // para siempre después de un fallo. Y se guarda el mensaje del
        // servidor en vez de uno genérico: cuando el rango pedido no cabe en
        // la escala, ese mensaje dice exactamente qué hacer.
        if (vigente)
          setHistorial({
            datos: null,
            consulta,
            fallo:
              error instanceof Error
                ? error.message
                : "No se pudo cargar el historial.",
          });
      });
    return () => {
      vigente = false;
    };
    // `consulta` resume la escala y las dos fechas, que es todo lo que cambia
    // la petición.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [consulta]);

  /**
   * Descarga el reporte de indicadores.
   *
   * Lo arma el backend a partir de los mismos números que se ven en pantalla,
   * con la escala y el rango que estén seleccionados: el archivo y el panel no
   * pueden decir cosas distintas. Mandar aquí solo la escala, como se hacía
   * antes de que hubiera fechas, haría que quien exporta mirando un día
   * concreto se llevara los últimos doce meses sin enterarse.
   */
  const exportar = async () => {
    setExportando(true);
    try {
      await api.fraud.downloadReport({
        granularity: granularidad,
        startDate: rango.desde || undefined,
        endDate: rango.hasta || undefined,
      });
      avisar("Reporte descargado");
    } catch (error: unknown) {
      avisar(
        error instanceof Error ? error.message : "No se pudo generar el reporte",
        "error"
      );
    } finally {
      setExportando(false);
    }
  };

  return (
    <>
      <Stack
        direction={{ xs: "column", sm: "row" }}
        spacing={2}
        sx={{ justifyContent: "space-between", alignItems: { sm: "center" }, mb: 4 }}
      >
        <Box>
          <Typography variant="h5" sx={{ fontWeight: 800 }}>
            Modelo e indicadores
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            Cómo decide el modelo cada compra, y qué tan bien lo está haciendo.
          </Typography>
        </Box>
        <Button
          component={Link}
          href="/admin/fraud"
          variant="outlined"
          startIcon={<FactCheckOutlinedIcon />}
          sx={{ textTransform: "none", fontWeight: 700, borderRadius: 2, whiteSpace: "nowrap" }}
        >
          Ir a la revisión
        </Button>
      </Stack>

      <Stack spacing={3}>
        <PorQueLightGBM datos={comparacion} cargando={cargando} />

        {/* Los tres indicadores de la tesis: son lo que el sistema promete
            mover, y el historial de abajo enseña cómo se han movido. */}
        <Box>
          <Typography variant="subtitle1" sx={{ fontWeight: 800, mb: 0.5 }}>
            Indicadores del sistema
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2.5, maxWidth: 820 }}>
            Medidos sobre el rango que está seleccionado abajo. El modelo se entrena
            persiguiéndolos: al elegir sus umbrales descarta los que no detectan al
            menos el 80 % del fraude, y un modelo reentrenado no se publica si detecta
            menos que el que ya está sirviendo.
          </Typography>
          <TarjetasDeIndicadores
            datos={historial.datos}
            cargando={cargandoHistorial}
            modelo={modelo}
          />
        </Box>

        {historial.fallo && (
          <Alert severity="error" sx={{ borderRadius: 2 }}>
            {historial.fallo}
          </Alert>
        )}

        <HistorialAntifraude
          datos={historial.datos}
          cargando={cargandoHistorial}
          granularidad={granularidad}
          onGranularidad={setGranularidad}
          desde={rango.desde}
          hasta={rango.hasta}
          onRango={(desde, hasta) => setRango({ desde, hasta })}
          onExportar={exportar}
          exportando={exportando}
        />
      </Stack>

      <Snackbar
        open={!!aviso}
        autoHideDuration={3000}
        onClose={() => setAviso(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
      >
        <Alert
          severity={aviso?.tipo}
          variant="filled"
          onClose={() => setAviso(null)}
          sx={{ width: "100%" }}
        >
          {aviso?.texto}
        </Alert>
      </Snackbar>
    </>
  );
}
