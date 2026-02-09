from sqlalchemy import (
    Column, String, Boolean, DateTime, ForeignKey, Text, Index, Enum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from .base import Base, TimestampMixin
from .enums import ParkingType


class ParkingAllocation(Base, TimestampMixin):
    __tablename__ = "parking_allocations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    floor_plan_id = Column(UUID(as_uuid=True), ForeignKey("floor_plans.id"), nullable=False)
    slot_label = Column(String(50), nullable=False)
    cell_row = Column(String(10), nullable=False)
    cell_column = Column(String(10), nullable=False)
    parking_type = Column(Enum(ParkingType), nullable=False, default=ParkingType.EMPLOYEE)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    visitor_name = Column(String(200), nullable=True)
    visitor_phone = Column(String(20), nullable=True)
    visitor_company = Column(String(200), nullable=True)
    vehicle_number = Column(String(50), nullable=True)
    entry_time = Column(DateTime(timezone=True), nullable=True)
    exit_time = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    
    # Relationships
    floor_plan = relationship("FloorPlan")
    user = relationship("User")
    
    __table_args__ = (
        Index("ix_parking_user_active", "user_id", "is_active"),
    )


class ParkingHistory(Base, TimestampMixin):
    __tablename__ = "parking_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    allocation_id = Column(UUID(as_uuid=True), ForeignKey("parking_allocations.id"), nullable=False)
    floor_plan_id = Column(UUID(as_uuid=True), ForeignKey("floor_plans.id"), nullable=False)
    slot_label = Column(String(50), nullable=False)
    parking_type = Column(Enum(ParkingType), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    visitor_name = Column(String(200), nullable=True)
    vehicle_number = Column(String(50), nullable=True)
    entry_time = Column(DateTime(timezone=True), nullable=False)
    exit_time = Column(DateTime(timezone=True), nullable=True)
    duration_minutes = Column(String(20), nullable=True)
    
    # Relationships
    allocation = relationship("ParkingAllocation")
    floor_plan = relationship("FloorPlan")
    user = relationship("User")