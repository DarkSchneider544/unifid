from sqlalchemy import (
    Column, String, DateTime, Date, ForeignKey, Text, Index, Enum, Time, Integer, Boolean
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from .base import Base, TimestampMixin
from .enums import BookingStatus


class CafeteriaTable(Base, TimestampMixin):
    """
    Cafeteria table definition from floor plan.
    Managed by CAFETERIA admin.
    """
    __tablename__ = "cafeteria_tables"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Reference to floor plan
    floor_plan_id = Column(UUID(as_uuid=True), ForeignKey("floor_plans.id"), nullable=False)
    
    # Table identification
    table_code = Column(String(20), unique=True, nullable=False, index=True)  # e.g., T-01, T-02
    table_label = Column(String(50), nullable=False)
    
    # Grid position
    cell_row = Column(Integer, nullable=False)
    cell_column = Column(Integer, nullable=False)
    
    # Table properties
    capacity = Column(Integer, nullable=False, default=4)
    table_type = Column(String(50), default="regular")  # regular, high_top, booth
    
    is_active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    
    # Relationships
    floor_plan = relationship("FloorPlan")
    bookings = relationship("CafeteriaTableBooking", back_populates="table")
    
    __table_args__ = (
        Index("ix_cafeteria_tables_floor", "floor_plan_id"),
        Index("ix_cafeteria_tables_capacity", "capacity"),
    )


class CafeteriaTableBooking(Base, TimestampMixin):
    """
    Cafeteria table booking records.
    Uses user_code instead of user_id.
    """
    __tablename__ = "cafeteria_table_bookings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Table reference
    table_id = Column(UUID(as_uuid=True), ForeignKey("cafeteria_tables.id"), nullable=False)
    
    # User reference - using user_code
    user_code = Column(String(10), ForeignKey("users.user_code"), nullable=False)
    
    # Booking details
    booking_date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    
    # Guest info
    guest_count = Column(Integer, default=1)
    guest_names = Column(Text, nullable=True)  # Comma-separated if multiple guests
    
    # Status
    status = Column(Enum(BookingStatus), default=BookingStatus.CONFIRMED)
    
    notes = Column(Text, nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    table = relationship("CafeteriaTable", back_populates="bookings")
    user = relationship("User", foreign_keys=[user_code], primaryjoin="CafeteriaTableBooking.user_code == User.user_code")
    
    __table_args__ = (
        Index("ix_table_booking_date", "table_id", "booking_date"),
        Index("ix_table_booking_user", "user_code", "booking_date"),
        Index("ix_table_booking_status", "status"),
    )