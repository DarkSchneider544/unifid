from sqlalchemy import (
    Column, String, DateTime, Date, ForeignKey, Text, Index, Enum, Time
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from .base import Base, TimestampMixin
from .enums import BookingStatus


class CafeteriaTableBooking(Base, TimestampMixin):
    __tablename__ = "cafeteria_table_bookings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    floor_plan_id = Column(UUID(as_uuid=True), ForeignKey("floor_plans.id"), nullable=False)
    table_label = Column(String(50), nullable=False)
    cell_row = Column(String(10), nullable=False)
    cell_column = Column(String(10), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    booking_date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    guest_count = Column(String(10), default="1")
    status = Column(Enum(BookingStatus), default=BookingStatus.CONFIRMED)
    notes = Column(Text, nullable=True)
    
    # Relationships
    floor_plan = relationship("FloorPlan")
    user = relationship("User")
    
    __table_args__ = (
        Index("ix_table_booking_date", "floor_plan_id", "table_label", "booking_date"),
    )