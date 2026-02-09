from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date, time
from decimal import Decimal
from uuid import UUID

from ..models.enums import OrderStatus


class FoodItemBase(BaseModel):
    """Base food item schema."""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    category: str = Field(..., min_length=1, max_length=100)
    price: Decimal = Field(..., gt=0)
    ingredients: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    calories: Optional[int] = None
    preparation_time_minutes: int = Field(default=15, ge=1)
    image_url: Optional[str] = None


class FoodItemCreate(FoodItemBase):
    """Food item creation schema."""
    pass


class FoodItemUpdate(BaseModel):
    """Food item update schema."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    category: Optional[str] = None
    price: Optional[Decimal] = Field(None, gt=0)
    ingredients: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    calories: Optional[int] = None
    is_available: Optional[bool] = None
    is_active: Optional[bool] = None
    preparation_time_minutes: Optional[int] = None
    image_url: Optional[str] = None


class FoodItemResponse(BaseModel):
    """Food item response schema."""
    id: UUID
    name: str
    description: Optional[str] = None
    category: str
    price: Decimal
    ingredients: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    calories: Optional[int] = None
    is_available: bool
    is_active: bool
    preparation_time_minutes: int
    image_url: Optional[str] = None
    created_by_id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class FoodOrderItemCreate(BaseModel):
    """Food order item creation schema."""
    food_item_id: UUID
    quantity: int = Field(default=1, ge=1)
    special_instructions: Optional[str] = None


class FoodOrderCreate(BaseModel):
    """Food order creation schema."""
    items: List[FoodOrderItemCreate] = Field(..., min_length=1)
    is_scheduled: bool = False
    scheduled_date: Optional[date] = None
    scheduled_time: Optional[time] = None
    notes: Optional[str] = None


class FoodOrderItemResponse(BaseModel):
    """Food order item response schema."""
    id: UUID
    food_item_id: UUID
    food_item_name: Optional[str] = None
    quantity: int
    unit_price: Decimal
    total_price: Decimal
    special_instructions: Optional[str] = None
    
    class Config:
        from_attributes = True


class FoodOrderResponse(BaseModel):
    """Food order response schema."""
    id: UUID
    order_number: str
    user_id: UUID
    status: OrderStatus
    total_amount: Decimal
    is_scheduled: bool
    scheduled_date: Optional[date] = None
    scheduled_time: Optional[time] = None
    notes: Optional[str] = None
    items: List[FoodOrderItemResponse] = []
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class FoodOrderStatusUpdate(BaseModel):
    """Food order status update schema."""
    status: OrderStatus
    notes: Optional[str] = None