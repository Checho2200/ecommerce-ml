/**
 * Cómo se escribe un tiempo de detección para que se pueda leer.
 *
 * El indicador viaja siempre en milisegundos, pero su magnitud depende por
 * completo de quién detectó. El modelo puntúa una compra en poco más de un
 * milisegundo; antes de que existiera, la regla fija solo levantaba la mano y
 * quien decidía era una persona cuando le llegaba el turno en la cola, o sea
 * horas. Forzar las dos cosas a «ms» produce «12,600,000.0 ms», que no dice
 * nada, y es justo el período con el que hay que comparar.
 *
 * Vive en `lib/` y no dentro de un componente porque lo usan las tarjetas de
 * indicadores y la tabla del historial, y las dos tienen que escribir el mismo
 * número de la misma forma.
 */

export function duracionLegible(milisegundos: number): string {
  if (!Number.isFinite(milisegundos) || milisegundos < 0) return "—";
  if (milisegundos < 1000) return `${milisegundos.toFixed(1)} ms`;

  const segundos = milisegundos / 1000;
  if (segundos < 60) return `${segundos.toFixed(1)} s`;

  const minutos = segundos / 60;
  if (minutos < 60) return `${Math.round(minutos)} min`;

  const horas = minutos / 60;
  if (horas < 48) return `${horas.toFixed(1)} h`;

  return `${(horas / 24).toFixed(1)} d`;
}
