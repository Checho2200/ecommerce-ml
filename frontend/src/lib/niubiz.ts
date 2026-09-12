/**
 * El formulario de pago de Niubiz, en el navegador.
 *
 * Niubiz no redirige a otro sitio como MercadoPago: carga un script que abre
 * un modal **sobre la tienda**, y la tarjeta se escribe ahí. El número viaja
 * de ese modal a Niubiz sin pasar por este código ni por el servidor de la
 * tienda, que es lo que mantiene a la tienda fuera del alcance de PCI-DSS.
 *
 * Cuando el comprador termina, el propio modal envía un formulario a la
 * dirección de retorno del backend —un POST del navegador, no una llamada de
 * esta aplicación— y es el backend quien cobra y decide a dónde se le manda
 * después. Por eso aquí no hay ningún `callback` que confirme nada: si lo
 * hubiera, el resultado del pago dependería de que la pestaña siguiera
 * abierta.
 */

import type { NiubizSessionResponse } from "@/lib/api";

/** Lo que el script de Niubiz publica en `window` al cargarse. */
interface VisanetCheckout {
  configure: (opciones: Record<string, string>) => void;
  open: () => void;
}

declare global {
  interface Window {
    VisanetCheckout?: VisanetCheckout;
  }
}

/**
 * Carga el script de Niubiz una sola vez.
 *
 * La dirección la manda el backend porque cambia entre pruebas y producción, y
 * tenerla escrita aquí obligaría a recordar cambiarla en dos sitios el día que
 * la tienda pase a cobrar de verdad.
 */
function cargarScript(src: string): Promise<void> {
  return new Promise((resolver, rechazar) => {
    if (window.VisanetCheckout) {
      resolver();
      return;
    }

    const existente = document.querySelector<HTMLScriptElement>(
      `script[src="${src}"]`,
    );
    if (existente) {
      existente.addEventListener("load", () => resolver());
      existente.addEventListener("error", () =>
        rechazar(new Error("No se pudo cargar el formulario de Niubiz.")),
      );
      return;
    }

    const script = document.createElement("script");
    script.src = src;
    script.async = true;
    script.onload = () => resolver();
    script.onerror = () =>
      rechazar(new Error("No se pudo cargar el formulario de Niubiz."));
    document.body.appendChild(script);
  });
}

/**
 * Abre el formulario de Niubiz para cobrar una orden.
 *
 * Todos los datos vienen de la sesión que abrió el backend. El monto en
 * particular: el que se ve en el formulario es el que Niubiz tiene atado a la
 * clave de sesión, así que cambiarlo desde el navegador no serviría de nada.
 */
export async function abrirFormularioDeNiubiz(
  sesion: NiubizSessionResponse,
  opciones: { ordenId: string; nombreDelComercio: string },
): Promise<void> {
  await cargarScript(sesion.checkout_js);

  if (!window.VisanetCheckout) {
    throw new Error("El formulario de Niubiz no quedó disponible.");
  }

  window.VisanetCheckout.configure({
    // A dónde envía el modal su formulario al terminar. Es una dirección del
    // backend, no de esta aplicación: el cobro lo cierra el servidor.
    action: sesion.action_url,
    sessiontoken: sesion.session_key,
    channel: "web",
    merchantid: sesion.merchant_id,
    purchasenumber: sesion.purchase_number,
    amount: sesion.amount,
    expirationminutes: "20",
    // Si el comprador deja el formulario abierto hasta que caduque, Niubiz lo
    // manda aquí en vez de dejarlo en una pantalla muerta. La orden sigue sin
    // pagar y puede reintentarla desde sus compras.
    timeouturl: `${window.location.origin}/checkout/failure?order_id=${opciones.ordenId}`,
    merchantname: opciones.nombreDelComercio,
    formbuttontext: "Pagar",
  });

  window.VisanetCheckout.open();
}
