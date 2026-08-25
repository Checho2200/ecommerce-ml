/**
 * Zustand store para el carrito de compras.
 * Persiste en localStorage para que sobreviva al cerrar el navegador.
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { ProductResponse } from '@/lib/api';

export interface CartItem {
  product: ProductResponse;
  quantity: number;
}

interface CartStore {
  items: CartItem[];
  addToCart: (product: ProductResponse, quantity?: number) => void;
  removeFromCart: (productId: string) => void;
  updateQuantity: (productId: string, quantity: number) => void;
  clearCart: () => void;
  totalItems: number;
  totalPrice: number;
}

export const useCartStore = create<CartStore>()(
  persist(
    (set, get) => ({
      items: [],

      addToCart: (product, quantity = 1) => {
        const prev = get().items;
        const existing = prev.find((i) => i.product.id === product.id);
        const newItems = existing
          ? prev.map((i) =>
              i.product.id === product.id
                ? { ...i, quantity: i.quantity + quantity }
                : i
            )
          : [...prev, { product, quantity }];
        set({
          items: newItems,
          totalItems: newItems.reduce((a, i) => a + i.quantity, 0),
          totalPrice: newItems.reduce((a, i) => a + i.product.price * i.quantity, 0),
        });
      },

      removeFromCart: (productId) => {
        const newItems = get().items.filter((i) => i.product.id !== productId);
        set({
          items: newItems,
          totalItems: newItems.reduce((a, i) => a + i.quantity, 0),
          totalPrice: newItems.reduce((a, i) => a + i.product.price * i.quantity, 0),
        });
      },

      updateQuantity: (productId, quantity) => {
        const newItems = get().items.map((i) =>
          i.product.id === productId ? { ...i, quantity } : i
        );
        set({
          items: newItems,
          totalItems: newItems.reduce((a, i) => a + i.quantity, 0),
          totalPrice: newItems.reduce((a, i) => a + i.product.price * i.quantity, 0),
        });
      },

      clearCart: () => set({ items: [], totalItems: 0, totalPrice: 0 }),

      totalItems: 0,
      totalPrice: 0,
    }),
    {
      name: 'sts-cart',
      // Recompute derived values on hydration
      onRehydrateStorage: () => (state) => {
        if (state) {
          state.totalItems = state.items.reduce((a, i) => a + i.quantity, 0);
          state.totalPrice = state.items.reduce((a, i) => a + i.product.price * i.quantity, 0);
        }
      },
    }
  )
);
