/**
 * Punto de entrada del cliente de API.
 *
 * Reúne los recursos en el objeto `api` que usa toda la aplicación, de modo
 * que las pantallas sigan escribiendo `api.orders.list()` sin saber en qué
 * archivo vive cada cosa.
 */

import { system } from "./system";
import { auth } from "./auth";
import { products } from "./products";
import { categories } from "./categories";
import { orders } from "./orders";
import { serviceOrders } from "./servicios";
import { reviews } from "./reviews";
import { upload } from "./upload";
import { fraud } from "./fraud";

export const api = {
  system,
  auth,
  products,
  categories,
  orders,
  serviceOrders,
  reviews,
  upload,
  fraud,
};

export { ApiError, getToken, setToken, removeToken } from "./cliente";
export * from "./tipos";
export default api;
