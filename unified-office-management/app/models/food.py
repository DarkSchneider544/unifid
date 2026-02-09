from sqlalchemy import (
    Column, String, Boolean, DateTime, Date, ForeignKey, Text, 
    Index, Enum, Numeric, Integer, ARRAY, Time
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from .base import Base, TimestampMixin
from .enums import OrderStatus


class FoodItem(Base, TimestampMixin):
    __tablename__ = "food_items"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    ingredients = Column(ARRAY(String), nullable=True)
    tags = Column(ARRAY(String), nullable=True)  # vegan, spicy, high-protein, etc.
    calories = Column(Integer, nullable=True)
    is_available = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    image_url = Column(String(500), nullable=True)
    preparation_time_minutes = Column(Integer, default=15)
    
    # Semantic search embedding - stored as bytes, will be cast to vector in queries
    embedding = Column(Text, nullable=True)
    
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Relationships
    created_by = relationship("User")
    
    __table_args__ = (
        Index("ix_food_items_category", "category"),
        Index("ix_food_items_available", "is_available", "is_active"),
    )


class FoodOrder(Base, TimestampMixin):
    __tablename__ = "food_orders"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_number = Column(String(50), unique=True, nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    total_amount = Column(Numeric(10, 2), nullable=False)
    scheduled_date = Column(Date, nullable=True)
    scheduled_time = Column(Time, nullable=True)
    is_scheduled = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    
    # Relationships
    user = relationship("User")
    items = relationship("FoodOrderItem", back_populates="order")
    
    __table_args__ = (
        Index("ix_food_orders_user_status", "user_id", "status"),
    )


class FoodOrderItem(Base, TimestampMixin):
    __tablename__ = "food_order_items"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("food_orders.id"), nullable=False)
    food_item_id = Column(UUID(as_uuid=True), ForeignKey("food_items.id"), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Numeric(10, 2), nullable=False)
    total_price = Column(Numeric(10, 2), nullable=False)
    special_instructions = Column(Text, nullable=True)
    
    # Relationships
    order = relationship("FoodOrder", back_populates="items")
    food_item = relationship("FoodItem")