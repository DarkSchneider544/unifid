from sqlalchemy import (
    Column, String, Boolean, Integer, Text, ForeignKey, JSON, Index, Enum, event
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
import random
import string

from .base import Base, TimestampMixin
from .enums import FloorPlanType, ManagerType


def generate_floor_plan_code(plan_type: FloorPlanType) -> str:
    """
    Generate a unique floor plan code based on type.
    Format: TYPE_PREFIX + 4 random digits
    - PARKING: PKG-XXXX
    - DESK_AREA: DSK-XXXX
    - CAFETERIA: CAF-XXXX
    """
    prefixes = {
        FloorPlanType.PARKING: "PKG",
        FloorPlanType.DESK_AREA: "DSK",
        FloorPlanType.CAFETERIA: "CAF"
    }
    prefix = prefixes.get(plan_type, "FLP")
    digits = ''.join(random.choices(string.digits, k=4))
    return f"{prefix}-{digits}"


# Mapping between floor plan types and manager types
FLOOR_PLAN_MANAGER_MAPPING = {
    FloorPlanType.PARKING: ManagerType.PARKING,
    FloorPlanType.DESK_AREA: ManagerType.DESK_CONFERENCE,
    FloorPlanType.CAFETERIA: ManagerType.CAFETERIA
}


class FloorPlan(Base, TimestampMixin):
    """
    Floor plan for different areas of the office.
    
    There are exactly 3 floor plan types, each managed by a specific admin:
    - PARKING: Managed by SECURITY admin - parking slot layouts
    - DESK_AREA: Managed by DESK admin - desk and conference room layouts  
    - CAFETERIA: Managed by CAFETERIA admin - dining area layouts
    
    Floor plan IDs are auto-generated in format: TYPE-XXXX
    (e.g., PKG-1234, DSK-5678, CAF-9012)
    
    Only ONE active floor plan per type is allowed at a time.
    """
    __tablename__ = "floor_plans"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Floor plan code - auto-generated unique identifier
    # Format: TYPE-XXXX (e.g., PKG-1234, DSK-5678, CAF-9012)
    floor_code = Column(String(20), unique=True, nullable=False, index=True)
    
    name = Column(String(200), nullable=False)
    plan_type = Column(Enum(FloorPlanType), nullable=False)
    
    # Grid dimensions
    rows = Column(Integer, nullable=False)
    columns = Column(Integer, nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True)
    description = Column(Text, nullable=True)
    
    # Versioning
    current_version = Column(Integer, default=1)
    
    # Created by - using user_code
    created_by_code = Column(String(10), ForeignKey("users.user_code"), nullable=False)
    
    # Building/Floor info
    building_name = Column(String(100), nullable=True)
    floor_number = Column(String(20), nullable=True)
    
    # Relationships
    versions = relationship(
        "FloorPlanVersion", 
        back_populates="floor_plan", 
        order_by="desc(FloorPlanVersion.version)"
    )
    created_by = relationship("User", foreign_keys=[created_by_code], primaryjoin="FloorPlan.created_by_code == User.user_code")
    
    __table_args__ = (
        Index("ix_floor_plans_type", "plan_type"),
        Index("ix_floor_plans_code", "floor_code"),
        Index("ix_floor_plans_active_type", "is_active", "plan_type"),
    )
    
    @classmethod
    def get_manager_type_for_plan(cls, plan_type: FloorPlanType) -> ManagerType:
        """Get the manager type that manages this floor plan type."""
        return FLOOR_PLAN_MANAGER_MAPPING.get(plan_type)


class FloorPlanVersion(Base, TimestampMixin):
    """
    Version history for floor plans.
    Each update creates a new version, preserving history.
    """
    __tablename__ = "floor_plan_versions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    floor_plan_id = Column(UUID(as_uuid=True), ForeignKey("floor_plans.id"), nullable=False)
    version = Column(Integer, nullable=False)
    
    # Grid data - 2D array of cell configurations
    # Each cell contains: type, label, status, capacity, etc.
    grid_data = Column(JSON, nullable=False)
    
    is_active = Column(Boolean, default=True)
    
    # Created by - using user_code
    created_by_code = Column(String(10), ForeignKey("users.user_code"), nullable=False)
    change_notes = Column(Text, nullable=True)
    
    # Relationships
    floor_plan = relationship("FloorPlan", back_populates="versions")
    created_by = relationship("User", foreign_keys=[created_by_code], primaryjoin="FloorPlanVersion.created_by_code == User.user_code")
    
    __table_args__ = (
        Index("ix_floor_plan_versions_unique", "floor_plan_id", "version", unique=True),
    )


# Event listener to auto-generate floor_code if not set
@event.listens_for(FloorPlan, 'before_insert')
def generate_floor_code_before_insert(mapper, connection, target):
    """Auto-generate a unique floor plan code before inserting."""
    if not target.floor_code:
        target.floor_code = generate_floor_plan_code(target.plan_type)