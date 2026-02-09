from sqlalchemy import (
    Column, String, Boolean, DateTime, Date, ForeignKey, Text, Index, Enum, Time
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from .base import Base, TimestampMixin
from .enums import BookingStatus


class DeskBooking(Base, TimestampMixin):
    __tablename__ = "desk_bookings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    floor_plan_id = Column(UUID(as_uuid=True), ForeignKey("floor_plans.id"), nullable=False)
    floor_plan_version = Column(String(10), nullable=False)
    desk_label = Column(String(50), nullable=False)
    cell_row = Column(String(10), nullable=False)
    cell_column = Column(String(10), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    booking_date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    status = Column(Enum(BookingStatus), default=BookingStatus.CONFIRMED)
    notes = Column(Text, nullable=True)
    
    # Relationships
    floor_plan = relationship("FloorPlan")
    user = relationship("User")
    
    __table_args__ = (
        Index("ix_desk_booking_date", "floor_plan_id", "desk_label", "booking_date"),
        Index("ix_desk_booking_user", "user_id", "booking_date"),
    )