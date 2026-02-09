from sqlalchemy import (
    Column, String, Boolean, Integer, Text, ForeignKey, JSON, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from .base import Base, TimestampMixin


class FloorPlan(Base, TimestampMixin):
    __tablename__ = "floor_plans"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False)
    name = Column(String(200), nullable=False)
    floor_number = Column(Integer, nullable=False)  # Negative for basements
    rows = Column(Integer, nullable=False)
    columns = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)
    is_basement = Column(Boolean, default=False)
    description = Column(Text, nullable=True)
    current_version = Column(Integer, default=1)
    
    # Relationships
    building = relationship("Building", back_populates="floor_plans")
    versions = relationship(
        "FloorPlanVersion", 
        back_populates="floor_plan", 
        order_by="desc(FloorPlanVersion.version)"
    )
    
    __table_args__ = (
        Index("ix_floor_plans_building_floor", "building_id", "floor_number", unique=True),
    )


class FloorPlanVersion(Base, TimestampMixin):
    __tablename__ = "floor_plan_versions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    floor_plan_id = Column(UUID(as_uuid=True), ForeignKey("floor_plans.id"), nullable=False)
    version = Column(Integer, nullable=False)
    grid_data = Column(JSON, nullable=False)  # 2D array of cell configurations
    is_active = Column(Boolean, default=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    change_notes = Column(Text, nullable=True)
    
    # Relationships
    floor_plan = relationship("FloorPlan", back_populates="versions")
    created_by = relationship("User")
    
    __table_args__ = (
        Index("ix_floor_plan_versions_unique", "floor_plan_id", "version", unique=True),
    )