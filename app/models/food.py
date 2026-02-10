from sqlalchemy import (
    Column, String, Boolean, DateTime, Date, ForeignKey, Text, 
    Index, Enum, Numeric, Integer, ARRAY, Time, event
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
import random
import string
from datetime import datetime, timezone

from .base import Base, TimestampMixin
from .enums import OrderStatus


def generate_order_number():
    """Generate a unique order number: ORD-YYYYMMDD-XXXX"""
    date_str = datetime.now(timezone.utc).strftime('%Y%m%d')
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"ORD-{date_str}-{random_str}"


class FoodCategory(Base, TimestampMixin):
    """Food item categories."""
    __tablename__ = "food_categories"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    display_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    image_url = Column(String(500), nullable=True)


class FoodItem(Base, TimestampMixin):
    """
    Food menu items.
    Managed by CAFETERIA admin.
    """
    __tablename__ = "food_items"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Item details
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    
    # Category
    category_id = Column(UUID(as_uuid=True), ForeignKey("food_categories.id"), nullable=True)
    category_name = Column(String(100), nullable=False)  # Denormalized for quick access
    
    # Pricing
    price = Column(Numeric(10, 2), nullable=False)
    
    # Item properties
    ingredients = Column(ARRAY(String), nullable=True)
    tags = Column(ARRAY(String), nullable=True)  # vegan, spicy, high-protein, gluten-free, etc.
    allergens = Column(ARRAY(String), nullable=True)
    calories = Column(Integer, nullable=True)
    
    # Availability
    is_available = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    is_special = Column(Boolean, default=False)  # Today's special
    
    # Display
    image_url = Column(String(500), nullable=True)
    preparation_time_minutes = Column(Integer, default=15)
    
    # Semantic search embedding
    embedding = Column(Text, nullable=True)
    
    # Created by - using user_code
    created_by_code = Column(String(10), ForeignKey("users.user_code"), nullable=False)
    
    # Relationships
    category = relationship("FoodCategory")
    created_by = relationship("User", foreign_keys=[created_by_code], primaryjoin="FoodItem.created_by_code == User.user_code")
    
    __table_args__ = (
        Index("ix_food_items_category", "category_id"),
        Index("ix_food_items_available", "is_available", "is_active"),
        Index("ix_food_items_special", "is_special"),
    )


class FoodOrder(Base, TimestampMixin):
    """
    Food orders placed by users.
    Uses user_code instead of user_id.
    """
    __tablename__ = "food_orders"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Order identification
    order_number = Column(String(50), unique=True, nullable=False, index=True)
    
    # User reference - using user_code
    user_code = Column(String(10), ForeignKey("users.user_code"), nullable=False)
    
    # Order status
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    
    # Pricing
    subtotal = Column(Numeric(10, 2), nullable=False)
    tax = Column(Numeric(10, 2), default=0)
    total_amount = Column(Numeric(10, 2), nullable=False)
    
    # Scheduling (for pre-orders)
    scheduled_date = Column(Date, nullable=True)
    scheduled_time = Column(Time, nullable=True)
    is_scheduled = Column(Boolean, default=False)
    
    # Order notes
    notes = Column(Text, nullable=True)
    special_instructions = Column(Text, nullable=True)
    
    # Timestamps
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    preparing_at = Column(DateTime(timezone=True), nullable=True)
    ready_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    
    # Processed by (cafeteria staff)
    processed_by_code = Column(String(10), ForeignKey("users.user_code"), nullable=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_code], primaryjoin="FoodOrder.user_code == User.user_code")
    processed_by = relationship("User", foreign_keys=[processed_by_code], primaryjoin="FoodOrder.processed_by_code == User.user_code")
    items = relationship("FoodOrderItem", back_populates="order")
    
    __table_args__ = (
        Index("ix_food_orders_user_status", "user_code", "status"),
        Index("ix_food_orders_date", "created_at"),
        Index("ix_food_orders_scheduled", "scheduled_date", "scheduled_time"),
    )


class FoodOrderItem(Base, TimestampMixin):
    """Individual items in a food order."""
    __tablename__ = "food_order_items"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # References
    order_id = Column(UUID(as_uuid=True), ForeignKey("food_orders.id"), nullable=False)
    food_item_id = Column(UUID(as_uuid=True), ForeignKey("food_items.id"), nullable=False)
    
    # Item details at time of order
    item_name = Column(String(200), nullable=False)  # Denormalized
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Numeric(10, 2), nullable=False)
    total_price = Column(Numeric(10, 2), nullable=False)
    
    # Customizations
    special_instructions = Column(Text, nullable=True)
    
    # Relationships
    order = relationship("FoodOrder", back_populates="items")
    food_item = relationship("FoodItem")


# Event listener to auto-generate order_number if not set
@event.listens_for(FoodOrder, 'before_insert')
def generate_order_number_before_insert(mapper, connection, target):
    """Auto-generate a unique order number before inserting."""
    if not target.order_number:
        target.order_number = generate_order_number()