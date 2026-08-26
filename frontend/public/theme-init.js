/**
 * Pinta el color de fondo correcto ANTES del primer render.
 *
 * Va como archivo aparte y no como <script> en línea dentro del layout por dos
 * razones: React avisa de los scripts en línea dentro de componentes, y
 * next/script con `beforeInteractive` no sirve aquí porque Next lo difiere a
 * través de su propio runtime en lugar de ejecutarlo en el head. Referenciado
 * con src desde el <head>, el navegador lo ejecuta de forma bloqueante antes
 * de pintar el body, que es justo lo que hace falta.
 *
 * Sin esto, quien tiene el modo oscuro guardado ve un destello blanco en cada
 * carga.
 */
(function () {
  try {
    var raw = localStorage.getItem('sts-theme');
    var mode = raw ? (JSON.parse(raw).state || {}).mode : null;
    if (mode !== 'dark' && mode !== 'light') mode = 'light';
    document.documentElement.style.colorScheme = mode;
    document.documentElement.style.backgroundColor =
      mode === 'dark' ? '#0B1520' : '#F2F4F7';
  } catch (e) {
    /* localStorage bloqueado: se queda con el tema claro por defecto */
  }
})();
