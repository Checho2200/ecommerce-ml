"""
CRUD de productos (protegido por rol ADMIN).
Incluye listado público con paginación y filtros.
"""

import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.models.product import Product, Category

# Ordenamientos que admite el listado público. La clave llega en ?sort=… y se
# traduce a una cláusula ORDER BY controlada: nunca se arma con texto del
# cliente, así que no hay forma de inyectar SQL por aquí.
#
# El precio con el que se ordena es el que el cliente paga —el de oferta cuando
# lo hay, el normal si no—, no siempre el de lista. Ordenar por `price` a secas
# colocaría mal un producto rebajado. El nombre se ordena en minúsculas para que
# el orden alfabético no separe "ASUS" de "asus".
_PRECIO_EFECTIVO = func.coalesce(Product.discount_price, Product.price)
_NOMBRE = func.lower(Product.name)

ORDENAMIENTOS = {
    "recientes": (Product.created_at.desc(),),
    # El desempate por fecha deja el orden estable cuando varios comparten precio.
    "precio_asc": (_PRECIO_EFECTIVO.asc(), Product.created_at.desc()),
    "precio_desc": (_PRECIO_EFECTIVO.desc(), Product.created_at.desc()),
    "nombre_asc": (_NOMBRE.asc(),),
    "nombre_desc": (_NOMBRE.desc(),),
}
ORDEN_POR_DEFECTO = "recientes"
from app.models.user import User
from app.schemas.product import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    ProductListResponse,
)
from app.api.deps import require_admin, get_current_user

router = APIRouter(prefix="/products", tags=["Productos"])


@router.get("", response_model=ProductListResponse)
async def list_products(
    page: int = Query(1, ge=1),
    per_page: int = Query(12, ge=1, le=100),
    category_id: Optional[int] = None,
    search: Optional[str] = None,
    active_only: bool = True,
    sort: str = Query(ORDEN_POR_DEFECTO),
    db: AsyncSession = Depends(get_db),
):
    """
    Lista productos con paginación, filtros y ordenamiento.
    Endpoint público (no requiere autenticación).

    `sort` acepta: recientes (por defecto), precio_asc, precio_desc,
    nombre_asc, nombre_desc. Un valor desconocido cae en el orden por defecto
    en lugar de dar error, para no romper el catálogo por un parámetro suelto.
    """
    query = select(Product)

    if active_only:
        query = query.where(Product.is_active == True)
    if category_id:
        # Filtrar por una categoría raíz incluye lo de sus subcategorías: quien
        # entra a "Memorias RAM" espera ver también las DDR4 y DDR5, no una
        # lista vacía porque los productos cuelgan de las hijas. Filtrar por una
        # subcategoría (que no tiene hijas) devuelve solo lo suyo.
        hijas = await db.execute(
            select(Category.id).where(Category.parent_id == category_id)
        )
        ids = [category_id, *hijas.scalars().all()]
        query = query.where(Product.category_id.in_(ids))
    if search:
        query = query.where(Product.name.ilike(f"%{search}%"))

    # Contar total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Ordenar y paginar. El ORDER BY va antes del LIMIT para que la página
    # devuelta sea la correcta dentro del orden pedido, no un recorte de otro.
    clausulas = ORDENAMIENTOS.get(sort, ORDENAMIENTOS[ORDEN_POR_DEFECTO])
    query = query.order_by(*clausulas)
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await db.execute(query)
    products = result.scalars().all()

    return ProductListResponse(
        items=[ProductResponse.model_validate(p) for p in products],
        total=total,
        page=page,
        pages=math.ceil(total / per_page) if total > 0 else 1,
    )


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Obtener detalle de un producto por ID."""
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado",
        )

    return product


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    data: ProductCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Crear un nuevo producto (solo admin)."""
    # Verificar que la categoría existe
    cat_result = await db.execute(
        select(Category).where(Category.id == data.category_id)
    )
    if not cat_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoría no encontrada",
        )

    product = Product(**data.model_dump())
    db.add(product)
    await db.flush()
    await db.refresh(product)

    return product


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str,
    data: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Actualizar un producto existente (solo admin)."""
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado",
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)

    await db.flush()
    await db.refresh(product)

    return product


@router.patch("/{product_id}/toggle", response_model=ProductResponse)
async def toggle_product(
    product_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Activar/desactivar un producto (solo admin)."""
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado",
        )

    product.is_active = not product.is_active
    await db.flush()
    await db.refresh(product)

    return product
