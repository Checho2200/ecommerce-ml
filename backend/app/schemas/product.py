"""
Schemas Pydantic para productos y categorías.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# --- Category ---
class CategoryCreate(BaseModel):
    """Crear nueva categoría."""
    name: str = Field(..., min_length=2, max_length=100)
    slug: str = Field(..., min_length=2, max_length=100, pattern=r"^[a-z0-9\-]+$")
    is_high_risk: bool = False
    image_url: Optional[str] = Field(None, max_length=500)
    # Si viene, la categoría es una subcategoría de esta otra.
    parent_id: Optional[int] = None


class CategoryUpdate(BaseModel):
    """Actualizar categoría."""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    slug: Optional[str] = Field(None, min_length=2, max_length=100, pattern=r"^[a-z0-9\-]+$")
    is_high_risk: Optional[bool] = None
    image_url: Optional[str] = Field(None, max_length=500)
    parent_id: Optional[int] = None


class CategoryResponse(BaseModel):
    """Respuesta de categoría."""
    id: int
    name: str
    slug: str
    is_high_risk: bool
    image_url: Optional[str] = None
    # Nulo en las categorías raíz; el id del padre en las subcategorías. El
    # frontend arma el árbol del filtro con este dato.
    parent_id: Optional[int] = None
    # Productos activos que cuelgan directamente de esta categoría. El catálogo
    # oculta las subcategorías con cero. Por defecto 0 cuando no se calcula.
    product_count: int = 0

    model_config = {"from_attributes": True}


# --- Product ---
class ProductCreate(BaseModel):
    """Crear nuevo producto."""
    name: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = None
    price: float = Field(..., gt=0)
    discount_price: Optional[float] = Field(None, gt=0)
    stock: int = Field(..., ge=0)
    image_url: Optional[str] = Field(None, max_length=500)
    category_id: int
    is_active: bool = True


class ProductUpdate(BaseModel):
    """Actualizar producto."""
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    description: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    discount_price: Optional[float] = Field(None, gt=0)
    stock: Optional[int] = Field(None, ge=0)
    image_url: Optional[str] = Field(None, max_length=500)
    category_id: Optional[int] = None
    is_active: Optional[bool] = None


class ProductResponse(BaseModel):
    """Respuesta de producto con categoría."""
    id: str
    name: str
    description: Optional[str] = None
    price: float
    discount_price: Optional[float] = None
    stock: int
    image_url: Optional[str] = None
    category_id: int
    category: Optional[CategoryResponse] = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ProductListResponse(BaseModel):
    """Respuesta paginada de productos."""
    items: List[ProductResponse]
    total: int
    page: int
    pages: int
