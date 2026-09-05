/**
 * Reglas de presentación del árbol de categorías.
 *
 * El backend devuelve la lista plana: raíces y subcategorías mezcladas, cada
 * una con los productos que le cuelgan directamente. Decidir qué se enseña al
 * cliente —solo las familias, y solo las que tienen algo que vender— es una
 * regla de la tienda, no del endpoint, y vive aquí porque la usan tanto la
 * navegación de la cabecera como la portada. Tenerla duplicada era lo que hacía
 * que la portada listara "DDR4" o "Intel Core i7" junto a "Procesadores".
 */

import type { CategoryResponse } from "@/lib/api";

export interface CategoriaRaiz extends CategoryResponse {
  /** Productos activos de la categoría más los de todas sus subcategorías. */
  total_products: number;
}

/**
 * Las categorías raíz que tienen algo que ofrecer, de la más surtida a la que
 * menos.
 *
 * Una raíz entra si vende algo por sí misma o a través de alguna hija: los
 * productos cuelgan de las subcategorías, así que filtrar solo por
 * `product_count` dejaría el menú vacío.
 *
 * El orden importa porque quien consume esta lista se queda con las primeras:
 * el menú de la cabecera enseña siete y la portada seis. El backend las
 * devuelve alfabéticamente, y recortar ese orden escondía justo las familias
 * grandes —"Procesadores", "Tarjetas de Video"— detrás de las que empiezan por
 * A. Ordenarlas por surtido deja arriba lo que la tienda más vende y se
 * reacomoda solo cuando cambia el catálogo; el nombre desempata para que dos
 * categorías del mismo tamaño no se turnen entre recargas.
 */
export function categoriasRaiz(categories: CategoryResponse[]): CategoriaRaiz[] {
  const enHijas = new Map<number, number>();
  for (const c of categories) {
    if (c.parent_id === null) continue;
    enHijas.set(c.parent_id, (enHijas.get(c.parent_id) ?? 0) + c.product_count);
  }

  return categories
    .filter((c) => c.parent_id === null)
    .map((c) => ({ ...c, total_products: c.product_count + (enHijas.get(c.id) ?? 0) }))
    .filter((c) => c.total_products > 0)
    .sort(
      (a, b) =>
        b.total_products - a.total_products || a.name.localeCompare(b.name, "es")
    );
}
