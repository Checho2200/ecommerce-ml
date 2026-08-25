from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class ProductReviewCreate(BaseModel):
    product_id: str
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None

class ProductReviewResponse(BaseModel):
    id: str
    user_id: str
    product_id: str
    rating: int
    comment: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

class ProductReviewWithUserResponse(ProductReviewResponse):
    user_name: str
