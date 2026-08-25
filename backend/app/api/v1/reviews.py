from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.review import ProductReview
from app.models.order import Order, OrderItem, OrderStatus
from app.schemas.review import ProductReviewCreate, ProductReviewResponse, ProductReviewWithUserResponse

router = APIRouter()

@router.post("/", response_model=ProductReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_review(
    review_in: ProductReviewCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Validar que el usuario compró el producto y la orden está COMPLETED
    query = (
        select(Order)
        .join(OrderItem, Order.id == OrderItem.order_id)
        .where(
            Order.user_id == current_user.id,
            Order.status == OrderStatus.COMPLETED,
            OrderItem.product_id == review_in.product_id
        )
    )
    result = await db.execute(query)
    has_bought = result.scalars().first()

    if not has_bought:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Debe comprar y recibir el producto para dejar una reseña"
        )
        
    # Validar si ya dejó reseña
    query_existing = select(ProductReview).where(
        ProductReview.user_id == current_user.id,
        ProductReview.product_id == review_in.product_id
    )
    res_existing = await db.execute(query_existing)
    if res_existing.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya has dejado una reseña para este producto"
        )

    db_review = ProductReview(
        user_id=current_user.id,
        product_id=review_in.product_id,
        rating=review_in.rating,
        comment=review_in.comment
    )
    db.add(db_review)
    await db.commit()
    await db.refresh(db_review)
    return db_review

@router.get("/product/{product_id}", response_model=List[ProductReviewWithUserResponse])
async def get_product_reviews(product_id: str, db: AsyncSession = Depends(get_db)):
    query = (
        select(ProductReview)
        .where(ProductReview.product_id == product_id)
        .order_by(ProductReview.created_at.desc())
    )
    result = await db.execute(query)
    reviews = result.scalars().all()
    
    response = []
    for r in reviews:
        # Load user
        u_query = select(User).where(User.id == r.user_id)
        u_res = await db.execute(u_query)
        user = u_res.scalars().first()
        
        response.append({
            "id": r.id,
            "user_id": r.user_id,
            "product_id": r.product_id,
            "rating": r.rating,
            "comment": r.comment,
            "created_at": r.created_at,
            "user_name": user.full_name if user else "Usuario Desconocido"
        })
        
    return response
