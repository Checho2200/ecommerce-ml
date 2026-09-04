"""
CRUD de categorías (protegido por rol ADMIN).
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select

from app.core.database import get_db
from app.models.product import Category, Product
from app.models.user import User
from app.schemas.product import CategoryCreate, CategoryUpdate, CategoryResponse
from app.api.deps import require_admin

router = APIRouter(prefix="/categories", tags=["Categorías"])


@router.get("", response_model=List[CategoryResponse])
async def list_categories(
    db: AsyncSession = Depends(get_db),
):
    """
    Lista todas las categorías (público).

    Cada una viaja con `product_count`: cuántos productos activos cuelgan
    directamente de ella. El catálogo lo usa para no mostrar subcategorías
    vacías —una "Intel Core i9" sin nada dentro sobra en la tienda—. Se cuenta
    en una sola consulta agrupada, no una por categoría.
    """
    result = await db.execute(select(Category).order_by(Category.name))
    categories = result.scalars().all()

    conteos = await db.execute(
        select(Product.category_id, func.count(Product.id))
        .where(Product.is_active == True)
        .group_by(Product.category_id)
    )
    por_categoria = dict(conteos.all())

    for categoria in categories:
        # Atributo dinámico que Pydantic lee al serializar; no es una columna.
        categoria.product_count = por_categoria.get(categoria.id, 0)

    return categories


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Obtener detalle de una categoría."""
    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoría no encontrada",
        )

    return category


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    data: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Crear nueva categoría (solo admin)."""
    # Verificar slug único
    result = await db.execute(select(Category).where(Category.slug == data.slug))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una categoría con ese slug",
        )

    category = Category(**data.model_dump())
    db.add(category)
    await db.flush()
    await db.refresh(category)

    return category


@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: int,
    data: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Actualizar una categoría (solo admin)."""
    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoría no encontrada",
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(category, field, value)

    await db.flush()
    await db.refresh(category)

    return category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Eliminar una categoría (solo admin). Falla si tiene productos asociados."""
    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoría no encontrada",
        )

    # Verificar que no tenga productos asociados
    if category.products:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede eliminar: la categoría tiene productos asociados",
        )

    await db.delete(category)
