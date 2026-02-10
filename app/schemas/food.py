from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime, date, time
from decimal import Decimal
from uuid import UUID

from ..models.enums import OrderStatus


# ==================== Food Category Schemas ====================

class FoodCategoryBase(BaseModel):
    """Base food category schema."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    display_order: int = Field(default=0, ge=0)


class FoodCategoryCreate(FoodCategoryBase):
    """Food category creation schema."""
    pass


class FoodCategoryUpdate(BaseModel):
    """Food category update schema."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    display_order: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class FoodCategoryResponse(BaseModel):
    """Food category response schema."""
    id: UUID
    name: str
    description: Optional[str] = None
    display_order: int
    is_active: bool
    item_count: int = 0  # Number of items in this category
    created_at: datetime
    
    class Config:
        from_attributes = True


class FoodCategoryListResponse(BaseModel):
    """Food category list response schema."""
    categories: List[FoodCategoryResponse]
    total: int


# ==================== Food Item Schemas ====================

class FoodItemBase(BaseModel):
    """Base food item schema."""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    price: Decimal = Field(..., gt=0)
    category_id: UUID
    ingredients: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    calories: Optional[int] = Field(None, ge=0)
    preparation_time_minutes: int = Field(default=15, ge=1, le=180)
    image_url: Optional[str] = None


class FoodItemCreate(FoodItemBase):
    """
    Food item creation schema.
    
    Only CAFETERIA admin can create food items.
    """
    pass


class FoodItemUpdate(BaseModel):
    """Food item update schema."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    category_id: Optional[UUID] = None
    price: Optional[Decimal] = Field(None, gt=0)
    ingredients: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    calories: Optional[int] = Field(None, ge=0)
    is_available: Optional[bool] = None
    is_active: Optional[bool] = None
    preparation_time_minutes: Optional[int] = Field(None, ge=1, le=180)
    image_url: Optional[str] = None


class FoodItemResponse(BaseModel):
    """Food item response schema."""
    id: UUID
    name: str
    description: Optional[str] = None
    category_id: UUID
    category_name: str
    price: Decimal
    ingredients: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    calories: Optional[int] = None
    is_available: bool
    is_active: bool
    preparation_time_minutes: int
    image_url: Optional[str] = None
    created_by_code: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class FoodItemListResponse(BaseModel):
    """Food item list response schema."""
    items: List[FoodItemResponse]
    total: int
    page: int
    page_size: int


class FoodMenuResponse(BaseModel):
    """Complete menu response grouped by category."""
    categories: List[FoodCategoryResponse]
    items_by_category: dict  # category_id -> List[FoodItemResponse]


# ==================== Food Order Schemas ====================

class FoodOrderItemCreate(BaseModel):
    """Food order item creation schema."""
    food_item_id: UUID
    quantity: int = Field(default=1, ge=1, le=10)
    special_instructions: Optional[str] = Field(None, max_length=500)


class FoodOrderCreate(BaseModel):
    """
    Food order creation schema.
    
    Available to: EMPLOYEE, TEAM_LEAD, MANAGER roles
    """
    items: List[FoodOrderItemCreate] = Field(..., min_length=1, max_length=20)
    is_scheduled: bool = False
    scheduled_date: Optional[date] = None
    scheduled_time: Optional[time] = None
    notes: Optional[str] = Field(None, max_length=500)
    
    @field_validator('scheduled_date')
    @classmethod
    def validate_scheduled_date(cls, v, info):
        is_scheduled = info.data.get('is_scheduled', False)
        if is_scheduled and not v:
            raise ValueError('Scheduled date is required for scheduled orders')
        if v and v < date.today():
            raise ValueError('Scheduled date cannot be in the past')
        return v
    
    @field_validator('scheduled_time')
    @classmethod
    def validate_scheduled_time(cls, v, info):
        is_scheduled = info.data.get('is_scheduled', False)
        if is_scheduled and not v:
            raise ValueError('Scheduled time is required for scheduled orders')
        return v


class FoodOrderUpdate(BaseModel):
    """Food order update schema (for scheduled orders only)."""
    scheduled_time: Optional[time] = None
    notes: Optional[str] = Field(None, max_length=500)


class FoodOrderCancel(BaseModel):
    """Food order cancellation schema."""
    cancellation_reason: str = Field(..., min_length=1, max_length=500)


class FoodOrderItemResponse(BaseModel):
    """Food order item response schema."""
    id: UUID
    food_item_id: UUID
    food_item_name: str
    quantity: int
    unit_price: Decimal
    subtotal: Decimal
    special_instructions: Optional[str] = None
    
    class Config:
        from_attributes = True


class FoodOrderResponse(BaseModel):
    """Food order response schema."""
    id: UUID
    order_number: str  # Auto-generated: ORD-YYYYMMDD-XXXX
    user_code: str
    user_name: str
    status: OrderStatus
    subtotal: Decimal
    tax: Decimal
    total_amount: Decimal
    is_scheduled: bool
    scheduled_date: Optional[date] = None
    scheduled_time: Optional[time] = None
    estimated_ready_time: Optional[datetime] = None
    items: List[FoodOrderItemResponse] = []
    notes: Optional[str] = None
    processed_by_code: Optional[str] = None
    processed_by_name: Optional[str] = None
    processing_started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class FoodOrderListResponse(BaseModel):
    """Food order list response schema."""
    orders: List[FoodOrderResponse]
    total: int
    page: int
    page_size: int


class MyOrdersResponse(BaseModel):
    """User's orders response."""
    active_orders: List[FoodOrderResponse] = []
    recent_orders: List[FoodOrderResponse] = []


# ==================== Admin Order Management Schemas ====================

class FoodOrderStatusUpdate(BaseModel):
    """
    Food order status update schema.
    
    Only CAFETERIA admin can update order status.
    """
    status: OrderStatus
    notes: Optional[str] = Field(None, max_length=500)


class OrderQueueResponse(BaseModel):
    """Cafeteria admin order queue response."""
    pending_orders: List[FoodOrderResponse] = []
    processing_orders: List[FoodOrderResponse] = []
    ready_orders: List[FoodOrderResponse] = []
    total_pending: int
    total_processing: int
    total_ready: int


# ==================== Food Order Statistics ====================

class FoodOrderStatistics(BaseModel):
    """Food order statistics for dashboard."""
    today_orders: int
    today_completed: int
    today_cancelled: int
    today_revenue: Decimal
    average_preparation_time_minutes: int
    popular_items: List[dict]  # [{"item_name": str, "count": int}]