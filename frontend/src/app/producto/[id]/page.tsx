"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Header from "@/components/ui/Header";
import { api, ProductResponse, ProductReviewResponse, ApiError } from "@/lib/api";
import { useCart } from "@/lib/cart";
import { useAuth } from "@/lib/auth";
import { Star, ShoppingCart, ShieldCheck, Truck, RotateCcw, AlertTriangle, ArrowLeft } from "lucide-react";
import Link from "next/link";

export default function ProductDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { id } = params;
  
  const { isAuthenticated } = useAuth();
  const { addToCart } = useCart();
  
  const [product, setProduct] = useState<ProductResponse | null>(null);
  const [reviews, setReviews] = useState<ProductReviewResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [quantity, setQuantity] = useState(1);
  const [added, setAdded] = useState(false);
  
  // Review Form
  const [rating, setRating] = useState(5);
  const [comment, setComment] = useState("");
  const [reviewLoading, setReviewLoading] = useState(false);
  const [reviewError, setReviewError] = useState("");
  const [reviewSuccess, setReviewSuccess] = useState("");

  useEffect(() => {
    const fetchProductAndReviews = async () => {
      try {
        const [prodRes, reviewsRes] = await Promise.all([
          api.products.get(id as string),
          api.reviews.getProductReviews(id as string)
        ]);
        setProduct(prodRes);
        setReviews(reviewsRes);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    
    if (id) fetchProductAndReviews();
  }, [id]);

  const handleAddToCart = () => {
    if (product) {
      addToCart(product, quantity);
      setAdded(true);
      setTimeout(() => setAdded(false), 2000);
    }
  };

  const handleSubmitReview = async (e: React.FormEvent) => {
    e.preventDefault();
    setReviewError("");
    setReviewSuccess("");
    setReviewLoading(true);
    
    try {
      const newReview = await api.reviews.create({
        product_id: id as string,
        rating,
        comment: comment.trim() || undefined
      });
      setReviews([newReview, ...reviews]);
      setReviewSuccess("¡Tu reseña ha sido publicada!");
      setComment("");
      setRating(5);
    } catch (err) {
      if (err instanceof ApiError) {
        setReviewError(err.message);
      } else {
        setReviewError("Error al publicar la reseña");
      }
    } finally {
      setReviewLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
        <Header />
        <div className="flex items-center justify-center min-h-[60vh]">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-600"></div>
        </div>
      </div>
    );
  }

  if (!product) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
        <Header />
        <div className="container mx-auto px-4 py-20 text-center flex flex-col items-center">
          <AlertTriangle size={64} className="text-gray-400 mb-6" />
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">Producto no encontrado</h1>
          <p className="text-gray-500 dark:text-gray-400 mb-8">El producto que buscas no existe o ha sido eliminado.</p>
          <button onClick={() => router.back()} className="px-6 py-3 bg-indigo-600 text-white rounded-full font-medium">
            Volver atrás
          </button>
        </div>
      </div>
    );
  }

  const averageRating = reviews.length > 0 
    ? reviews.reduce((acc, r) => acc + r.rating, 0) / reviews.length 
    : 0;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      <Header />
      
      <main className="container mx-auto px-4 py-8">
        <button onClick={() => router.back()} className="flex items-center gap-2 text-sm text-gray-500 hover:text-indigo-600 mb-6 transition-colors">
          <ArrowLeft size={16} /> Volver al catálogo
        </button>

        <div className="bg-white dark:bg-gray-900 rounded-3xl overflow-hidden shadow-sm border border-gray-100 dark:border-gray-800 flex flex-col lg:flex-row mb-12">
          {/* Image */}
          <div className="w-full lg:w-1/2 p-10 flex items-center justify-center bg-gray-50 dark:bg-gray-800/50">
            {product.image_url ? (
              <img src={product.image_url} alt={product.name} className="w-full max-w-md object-contain mix-blend-multiply dark:mix-blend-normal hover:scale-105 transition-transform duration-500" />
            ) : (
              <div className="w-full aspect-square flex items-center justify-center bg-gray-100 dark:bg-gray-800 rounded-2xl max-w-md">
                <span className="text-gray-400">Sin imagen</span>
              </div>
            )}
          </div>
          
          {/* Details */}
          <div className="w-full lg:w-1/2 p-8 lg:p-12 flex flex-col">
            <div className="flex items-center gap-2 mb-3">
              <span className="text-xs font-bold uppercase tracking-wider text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-900/30 px-3 py-1 rounded-full">
                {product.category?.name || "Hardware"}
              </span>
              {product.stock <= 5 && product.stock > 0 && (
                <span className="text-xs font-bold uppercase tracking-wider text-orange-600 bg-orange-50 px-3 py-1 rounded-full border border-orange-100">
                  Poco Stock
                </span>
              )}
            </div>
            
            <h1 className="text-3xl lg:text-4xl font-black text-gray-900 dark:text-white mb-4 leading-tight">
              {product.name}
            </h1>
            
            <div className="flex items-center gap-4 mb-6">
              <div className="flex items-center gap-1">
                {[1, 2, 3, 4, 5].map(star => (
                  <Star 
                    key={star} 
                    size={18} 
                    fill={star <= averageRating ? "currentColor" : "none"} 
                    className={star <= averageRating ? "text-yellow-400" : "text-gray-300 dark:text-gray-600"} 
                  />
                ))}
                <span className="text-sm font-medium text-gray-600 dark:text-gray-400 ml-2">
                  {reviews.length} {reviews.length === 1 ? 'reseña' : 'reseñas'}
                </span>
              </div>
            </div>
            
            <div className="flex items-end gap-3 mb-8">
              {product.discount_price ? (
                <>
                  <span className="text-4xl font-black text-red-600 dark:text-red-500 leading-none">
                    S/{product.discount_price.toFixed(2)}
                  </span>
                  <span className="text-lg text-gray-400 line-through mb-1">
                    S/{product.price.toFixed(2)}
                  </span>
                  <span className="bg-red-100 text-red-800 text-xs font-bold px-2 py-1 rounded dark:bg-red-900 dark:text-red-300 mb-1">
                    -{Math.round(((product.price - product.discount_price) / product.price) * 100)}%
                  </span>
                </>
              ) : (
                <span className="text-4xl font-black text-indigo-600 dark:text-indigo-400 leading-none">
                  S/{product.price.toFixed(2)}
                </span>
              )}
            </div>
            
            <p className="text-gray-600 dark:text-gray-300 mb-8 leading-relaxed">
              {product.description || "Sin descripción detallada para este producto."}
            </p>
            
            {/* Add to Cart Section */}
            <div className="mt-auto">
              {product.stock > 0 ? (
                <div className="flex flex-col sm:flex-row gap-4 mb-6">
                  <div className="flex items-center border border-gray-300 dark:border-gray-700 rounded-full bg-white dark:bg-gray-800 w-fit">
                    <button 
                      onClick={() => setQuantity(q => Math.max(1, q - 1))}
                      className="w-12 h-12 flex items-center justify-center text-gray-600 dark:text-gray-300 hover:text-indigo-600 disabled:opacity-50"
                      disabled={quantity <= 1}
                    >
                      -
                    </button>
                    <span className="w-8 text-center font-bold">{quantity}</span>
                    <button 
                      onClick={() => setQuantity(q => Math.min(product.stock, q + 1))}
                      className="w-12 h-12 flex items-center justify-center text-gray-600 dark:text-gray-300 hover:text-indigo-600 disabled:opacity-50"
                      disabled={quantity >= product.stock}
                    >
                      +
                    </button>
                  </div>
                  
                  <button 
                    onClick={handleAddToCart}
                    className={`flex-1 flex items-center justify-center gap-2 px-8 py-3 rounded-full font-bold text-white transition-all shadow-lg shadow-indigo-600/20 active:scale-95 ${
                      added ? "bg-green-500 hover:bg-green-600 shadow-green-500/20" : "bg-indigo-600 hover:bg-indigo-700"
                    }`}
                  >
                    {added ? (
                      <>Agregado al carrito</>
                    ) : (
                      <><ShoppingCart size={20} /> Agregar al Carrito</>
                    )}
                  </button>
                </div>
              ) : (
                <div className="w-full py-4 text-center bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400 font-bold rounded-xl mb-6">
                  Producto Agotado
                </div>
              )}
              
              {/* Features */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-6 border-t border-gray-100 dark:border-gray-800">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-green-50 text-green-600 flex items-center justify-center dark:bg-green-900/30 dark:text-green-400">
                    <ShieldCheck size={20} />
                  </div>
                  <div>
                    <p className="text-xs font-bold text-gray-900 dark:text-white">Garantía</p>
                    <p className="text-xs text-gray-500">12 meses</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-blue-50 text-blue-600 flex items-center justify-center dark:bg-blue-900/30 dark:text-blue-400">
                    <Truck size={20} />
                  </div>
                  <div>
                    <p className="text-xs font-bold text-gray-900 dark:text-white">Envío a todo el Perú</p>
                    <p className="text-xs text-gray-500">24-48hrs útiles</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-orange-50 text-orange-600 flex items-center justify-center dark:bg-orange-900/30 dark:text-orange-400">
                    <RotateCcw size={20} />
                  </div>
                  <div>
                    <p className="text-xs font-bold text-gray-900 dark:text-white">Devoluciones</p>
                    <p className="text-xs text-gray-500">7 días para cambios</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Reviews Section */}
        <div className="bg-white dark:bg-gray-900 rounded-3xl p-8 lg:p-12 shadow-sm border border-gray-100 dark:border-gray-800">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-8">Opiniones de Clientes</h2>
          
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-12">
            <div className="lg:col-span-1">
              <div className="bg-gray-50 dark:bg-gray-800/50 p-6 rounded-2xl flex flex-col items-center justify-center mb-6">
                <span className="text-5xl font-black text-gray-900 dark:text-white mb-2">{averageRating.toFixed(1)}</span>
                <div className="flex gap-1 mb-2">
                  {[1, 2, 3, 4, 5].map(star => (
                    <Star 
                      key={star} 
                      size={24} 
                      fill={star <= Math.round(averageRating) ? "currentColor" : "none"} 
                      className={star <= Math.round(averageRating) ? "text-yellow-400" : "text-gray-300 dark:text-gray-600"} 
                    />
                  ))}
                </div>
                <p className="text-sm text-gray-500">Basado en {reviews.length} reseñas</p>
              </div>

              <div className="border-t border-gray-200 dark:border-gray-700 pt-6">
                <h3 className="font-bold text-gray-900 dark:text-white mb-4">¿Compraste este producto?</h3>
                {isAuthenticated ? (
                  <form onSubmit={handleSubmitReview} className="flex flex-col gap-4">
                    {reviewError && (
                      <div className="p-3 bg-red-50 text-red-600 text-sm rounded-xl border border-red-100 dark:bg-red-900/20 dark:border-red-800/30">
                        {reviewError}
                      </div>
                    )}
                    {reviewSuccess && (
                      <div className="p-3 bg-green-50 text-green-600 text-sm rounded-xl border border-green-100 dark:bg-green-900/20 dark:border-green-800/30">
                        {reviewSuccess}
                      </div>
                    )}
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Tu calificación</label>
                      <div className="flex gap-2">
                        {[1, 2, 3, 4, 5].map(star => (
                          <button 
                            key={star} 
                            type="button"
                            onClick={() => setRating(star)}
                            className="focus:outline-none transition-transform hover:scale-110"
                          >
                            <Star 
                              size={28} 
                              fill={star <= rating ? "currentColor" : "none"} 
                              className={star <= rating ? "text-yellow-400" : "text-gray-300 dark:text-gray-600"} 
                            />
                          </button>
                        ))}
                      </div>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Comentario (Opcional)</label>
                      <textarea 
                        className="w-full px-4 py-3 rounded-xl border border-gray-300 bg-gray-50 focus:bg-white focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 outline-none transition-all resize-none dark:bg-gray-800 dark:border-gray-700 dark:text-white"
                        rows={3}
                        placeholder="Cuéntanos qué te pareció..."
                        value={comment}
                        onChange={(e) => setComment(e.target.value)}
                      ></textarea>
                    </div>
                    <button 
                      type="submit" 
                      disabled={reviewLoading}
                      className="w-full py-3 bg-gray-900 text-white font-semibold rounded-xl hover:bg-gray-800 transition-colors disabled:opacity-50 dark:bg-indigo-600 dark:hover:bg-indigo-700"
                    >
                      {reviewLoading ? "Publicando..." : "Publicar Reseña"}
                    </button>
                  </form>
                ) : (
                  <div className="p-4 bg-indigo-50 dark:bg-indigo-900/20 rounded-xl text-center">
                    <p className="text-sm text-indigo-800 dark:text-indigo-300 mb-3">
                      Inicia sesión para compartir tu experiencia con otros clientes.
                    </p>
                    <Link href="/login" className="inline-block px-6 py-2 bg-indigo-600 text-white font-medium rounded-full hover:bg-indigo-700 text-sm">
                      Iniciar Sesión
                    </Link>
                  </div>
                )}
              </div>
            </div>

            <div className="lg:col-span-2 flex flex-col gap-6">
              {reviews.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12 text-center text-gray-500">
                  <Star size={48} className="text-gray-300 dark:text-gray-600 mb-4" />
                  <p className="font-medium">Aún no hay reseñas</p>
                  <p className="text-sm">Sé el primero en dar tu opinión sobre este producto.</p>
                </div>
              ) : (
                reviews.map(review => (
                  <div key={review.id} className="p-6 bg-gray-50 dark:bg-gray-800/30 rounded-2xl">
                    <div className="flex justify-between items-start mb-3">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-indigo-100 text-indigo-600 font-bold flex items-center justify-center dark:bg-indigo-900/40 dark:text-indigo-400">
                          {review.user_name?.charAt(0).toUpperCase()}
                        </div>
                        <div>
                          <p className="font-bold text-gray-900 dark:text-white text-sm">{review.user_name}</p>
                          <p className="text-xs text-gray-500">Comprador Verificado</p>
                        </div>
                      </div>
                      <span className="text-xs text-gray-500">
                        {new Date(review.created_at).toLocaleDateString("es-PE")}
                      </span>
                    </div>
                    <div className="flex gap-1 mb-3">
                      {[1, 2, 3, 4, 5].map(star => (
                        <Star 
                          key={star} 
                          size={14} 
                          fill={star <= review.rating ? "currentColor" : "none"} 
                          className={star <= review.rating ? "text-yellow-400" : "text-gray-300 dark:text-gray-600"} 
                        />
                      ))}
                    </div>
                    {review.comment && (
                      <p className="text-gray-700 dark:text-gray-300 text-sm leading-relaxed">
                        {review.comment}
                      </p>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
