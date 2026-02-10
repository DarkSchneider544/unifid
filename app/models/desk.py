from sqlalchemy import (
    Column, String, Boolean, DateTime, Date, ForeignKey, Text, Index, Enum, Time, Integer
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from .base import Base, TimestampMixin
from .enums import BookingStatus, DeskStatus


class Desk(Base, TimestampMixin):
    """
    Desk definition from floor plan.
    Managed by DESK admin.
    """
    __tablename__ = "desks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Reference to floor plan
    floor_plan_id = Column(UUID(as_uuid=True), ForeignKey("floor_plans.id"), nullable=False)
    
    # Desk identification
    desk_code = Column(String(20), unique=True, nullable=False, index=True)  # e.g., D-A01, D-B02
    desk_label = Column(String(50), nullable=False)
    
    # Grid position
    cell_row = Column(Integer, nullable=False)
    cell_column = Column(Integer, nullable=False)
    
    # Desk properties
    status = Column(Enum(DeskStatus), default=DeskStatus.AVAILABLE)
    has_monitor = Column(Boolean, default=True)
    has_docking_station = Column(Boolean, default=False)
    
    # Location info
    zone = Column(String(50), nullable=True)  # e.g., "Zone A", "Window Side"
    
    is_active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    
    # Relationships
    floor_plan = relationship("FloorPlan")
    bookings = relationship("DeskBooking", back_populates="desk")
    
    __table_args__ = (
        Index("ix_desks_floor", "floor_plan_id"),
        Index("ix_desks_status", "status"),
        Index("ix_desks_zone", "zone"),
    )


class DeskBooking(Base, TimestampMixin):
    """
    Desk booking records.
    Uses user_code instead of user_id.
    Supports time-based booking within business hours (9 AM - 7 PM).
    """
    __tablename__ = "desk_bookings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Desk reference
    desk_id = Column(UUID(as_uuid=True), ForeignKey("desks.id"), nullable=False)
    
    # User reference - using user_code
    user_code = Column(String(10), ForeignKey("users.user_code"), nullable=False)
    
    # Booking details
    booking_date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)  # Business hours: 9:00 - 19:00
    end_time = Column(Time, nullable=False)
    
    # Status
    status = Column(Enum(BookingStatus), default=BookingStatus.CONFIRMED)
    
    # Check-in/out tracking
    checked_in_at = Column(DateTime(timezone=True), nullable=True)
    checked_out_at = Column(DateTime(timezone=True), nullable=True)
    
    notes = Column(Text, nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    desk = relationship("Desk", back_populates="bookings")
    user = relationship("User", foreign_keys=[user_code], primaryjoin="DeskBooking.user_code == User.user_code")
    
    __table_args__ = (
        Index("ix_desk_booking_date", "desk_id", "booking_date"),
        Index("ix_desk_booking_user", "user_code", "booking_date"),
        Index("ix_desk_booking_status", "status"),
    )


class ConferenceRoom(Base, TimestampMixin):
    """
    Conference room definition from floor plan.
    Managed by DESK admin.
    """
    __tablename__ = "conference_rooms"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Reference to floor plan
    floor_plan_id = Column(UUID(as_uuid=True), ForeignKey("floor_plans.id"), nullable=False)
    
    # Room identification
    room_code = Column(String(20), unique=True, nullable=False, index=True)
    room_name = Column(String(100), nullable=False)
    
    # Grid position (start position, rooms span multiple cells)
    cell_row = Column(Integer, nullable=False)
    cell_column = Column(Integer, nullable=False)
    cell_span_rows = Column(Integer, default=1)
    cell_span_cols = Column(Integer, default=1)
    
    # Room properties
    capacity = Column(Integer, nullable=False)
    has_projector = Column(Boolean, default=False)
    has_whiteboard = Column(Boolean, default=True)
    has_video_conference = Column(Boolean, default=False)
    has_phone = Column(Boolean, default=False)
    
    status = Column(Enum(DeskStatus), default=DeskStatus.AVAILABLE)
    is_active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    image_url = Column(String(500), nullable=True)
    
    # Relationships
    floor_plan = relationship("FloorPlan")
    bookings = relationship("ConferenceRoomBooking", back_populates="room")
    
    __table_args__ = (
        Index("ix_conference_rooms_floor", "floor_plan_id"),
        Index("ix_conference_rooms_capacity", "capacity"),
    )


class ConferenceRoomBooking(Base, TimestampMixin):
    """
    Conference room booking records.
    Uses user_code instead of user_id.
    """
    __tablename__ = "conference_room_bookings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Room reference
    room_id = Column(UUID(as_uuid=True), ForeignKey("conference_rooms.id"), nullable=False)
    
    # User reference - using user_code
    user_code = Column(String(10), ForeignKey("users.user_code"), nullable=False)
    
    # Booking details
    booking_date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    
    # Meeting info
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    attendees_count = Column(Integer, nullable=False)
    
    # Status
    status = Column(Enum(BookingStatus), default=BookingStatus.PENDING)
    
    notes = Column(Text, nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    room = relationship("ConferenceRoom", back_populates="bookings")
    user = relationship("User", foreign_keys=[user_code], primaryjoin="ConferenceRoomBooking.user_code == User.user_code")
    
    __table_args__ = (
        Index("ix_conf_booking_date", "room_id", "booking_date"),
        Index("ix_conf_booking_user", "user_code", "booking_date"),
        Index("ix_conf_booking_status", "status"),
    )