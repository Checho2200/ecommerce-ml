/**
 * Script que pinta el color de fondo correcto ANTES del primer render.
 *
 * Sin él, quien tiene el modo oscuro guardado ve un destello blanco en cada
 * carga: el tema vive en localStorage y React no lo conoce hasta que hidrata.
 *
 * Se inyecta en línea, dentro del <head> del layout. Antes vivía en
 * `public/theme-init.js` y se cargaba con `<script src>`, lo que obligaba al
 * navegador a detenerse a pedir un archivo justo en el momento más sensible
 * de la carga —y era exactamente lo que advertía la regla
 * `@next/next/no-sync-scripts`—. En línea se ejecuta sin viaje a la red y el
 * código sigue viviendo en un solo lugar, aquí.
 *
 * `next/script` con `beforeInteractive` no sirve para esto: Next lo difiere a
 * través de su propio runtime en lugar de ejecutarlo en el head.
 */
export const THEME_INIT_SCRIPT = `(function () {
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
})();`;
