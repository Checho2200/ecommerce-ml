"use client";

/**
 * Compatibility shim — re-exports the Zustand cart store
 * with the same interface as the old React Context API.
 * All components using useCart() continue to work without changes.
 */

export { type CartItem } from "@/lib/stores/cart";
export { useCartStore as useCart } from "@/lib/stores/cart";

// CartProvider is now a no-op wrapper kept for layout compatibility
import React from "react";
export function CartProvider({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
