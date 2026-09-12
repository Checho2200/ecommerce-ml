import type { ProductResponse } from "@/lib/api";

/**
 * Lo que cuesta un producto de verdad: el de oferta cuando lo hay.
 *
 * Existe porque no existía. El catálogo enseñaba el precio de oferta y tachaba
 * el de lista, pero el carrito, el resumen del checkout y el pedido sumaban con
 * `price`. La tienda anunciaba un precio y cobraba otro más alto, que es de las
 * pocas cosas que una tienda no se puede permitir.
 *
 * Quien manda es el backend —recalcula el total con su propio
 * `precio_efectivo` y nunca se fía del navegador—, así que esto no decide lo
 * que se cobra. Decide lo que se enseña, y lo que se enseña tiene que coincidir
 * con lo que se cobra.
 */
export function precioEfectivo(producto: ProductResponse): number {
  return producto.discount_price ?? producto.price;
}
