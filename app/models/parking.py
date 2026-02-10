from sqlalchemy import (
    Column, String, Boolean, DateTime, ForeignKey, Text, Index, Enum, Integer
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from .base import Base, TimestampMixin
from .enums import ParkingType, ParkingSlotStatus, VehicleType


class ParkingSlot(Base, TimestampMixin):
    """
    Parking slot definition from floor plan.
    Managed by SECURITY admin.
    """
    __tablename__ = "parking_slots"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Reference to floor plan
    floor_plan_id = Column(UUID(as_uuid=True), ForeignKey("floor_plans.id"), nullable=False)
    
    # Slot identification
    slot_code = Column(String(20), unique=True, nullable=False, index=True)  # e.g., A-01, B-02
    slot_label = Column(String(50), nullable=False)
    
    # Grid position
    cell_row = Column(Integer, nullable=False)
    cell_column = Column(Integer, nullable=False)
    
    # Slot properties
    parking_type = Column(Enum(ParkingType), nullable=False, default=ParkingType.EMPLOYEE)
    vehicle_type = Column(Enum(VehicleType), nullable=True)  # car, bike - if specific
    status = Column(Enum(ParkingSlotStatus), default=ParkingSlotStatus.AVAILABLE)
    
    is_active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    
    # Relationships
    floor_plan = relationship("FloorPlan")
    
    __table_args__ = (
        Index("ix_parking_slots_floor", "floor_plan_id"),
        Index("ix_parking_slots_status", "status"),
    )


class ParkingAllocation(Base, TimestampMixin):
    """
    Current parking allocations (who is parked where).
    Uses user_code instead of user_id.
    """
    __tablename__ = "parking_allocations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Slot reference
    slot_id = Column(UUID(as_uuid=True), ForeignKey("parking_slots.id"), nullable=False)
    
    # For employee parking - use user_code
    user_code = Column(String(10), ForeignKey("users.user_code"), nullable=True)
    
    # For visitor parking
    parking_type = Column(Enum(ParkingType), nullable=False, default=ParkingType.EMPLOYEE)
    visitor_name = Column(String(200), nullable=True)
    visitor_phone = Column(String(20), nullable=True)
    visitor_company = Column(String(200), nullable=True)
    
    # Vehicle info
    vehicle_number = Column(String(50), nullable=False)
    vehicle_type = Column(Enum(VehicleType), nullable=False)
    
    # Timing
    entry_time = Column(DateTime(timezone=True), nullable=False)
    expected_exit_time = Column(DateTime(timezone=True), nullable=True)
    exit_time = Column(DateTime(timezone=True), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    
    # Relationships
    slot = relationship("ParkingSlot")
    user = relationship("User", foreign_keys=[user_code], primaryjoin="ParkingAllocation.user_code == User.user_code")
    
    __table_args__ = (
        Index("ix_parking_allocation_user", "user_code", "is_active"),
        Index("ix_parking_allocation_slot", "slot_id", "is_active"),
        Index("ix_parking_allocation_entry", "entry_time"),
    )


class ParkingHistory(Base, TimestampMixin):
    """
    Historical record of all parking allocations.
    Created when a parking allocation is released.
    """
    __tablename__ = "parking_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # References
    allocation_id = Column(UUID(as_uuid=True), nullable=False)  # Original allocation ID
    slot_id = Column(UUID(as_uuid=True), ForeignKey("parking_slots.id"), nullable=False)
    slot_code = Column(String(20), nullable=False)
    
    # User/Visitor info
    parking_type = Column(Enum(ParkingType), nullable=False)
    user_code = Column(String(10), ForeignKey("users.user_code"), nullable=True)
    visitor_name = Column(String(200), nullable=True)
    
    # Vehicle info
    vehicle_number = Column(String(50), nullable=False)
    vehicle_type = Column(Enum(VehicleType), nullable=False)
    
    # Timing
    entry_time = Column(DateTime(timezone=True), nullable=False)
    exit_time = Column(DateTime(timezone=True), nullable=False)
    duration_minutes = Column(Integer, nullable=True)
    
    # Relationships
    slot = relationship("ParkingSlot")
    user = relationship("User", foreign_keys=[user_code], primaryjoin="ParkingHistory.user_code == User.user_code")
    
    __table_args__ = (
        Index("ix_parking_history_user", "user_code"),
        Index("ix_parking_history_slot", "slot_id"),
        Index("ix_parking_history_date", "entry_time"),
    )