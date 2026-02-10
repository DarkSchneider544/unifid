from sqlalchemy import (
    Column, String, Boolean, DateTime, Date, ForeignKey, Text, 
    Index, Enum, Numeric, ARRAY
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

from .base import Base, TimestampMixin
from .enums import AssetStatus, AssetType


class ITAsset(Base, TimestampMixin):
    """
    IT Asset inventory.
    Managed by IT admin.
    """
    __tablename__ = "it_assets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Asset identification
    asset_code = Column(String(100), unique=True, nullable=False, index=True)  # e.g., IT-LAP-001
    name = Column(String(200), nullable=False)
    asset_type = Column(Enum(AssetType), nullable=False)
    
    # Description and specs
    description = Column(Text, nullable=True)
    vendor = Column(String(200), nullable=True)
    model = Column(String(200), nullable=True)
    serial_number = Column(String(200), nullable=True, unique=True)
    specifications = Column(JSONB, nullable=True)  # Flexible specs storage
    tags = Column(ARRAY(String), nullable=True)
    
    # Purchase and warranty
    purchase_date = Column(Date, nullable=True)
    purchase_price = Column(Numeric(12, 2), nullable=True)
    warranty_expiry = Column(Date, nullable=True)
    
    # Status and location
    status = Column(Enum(AssetStatus), default=AssetStatus.AVAILABLE)
    location = Column(String(200), nullable=True)
    
    is_active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    
    # Semantic search embedding
    embedding = Column(Text, nullable=True)
    
    # Relationships
    assignments = relationship("ITAssetAssignment", back_populates="asset", order_by="desc(ITAssetAssignment.assigned_at)")
    
    __table_args__ = (
        Index("ix_it_assets_status", "status"),
        Index("ix_it_assets_type", "asset_type"),
        Index("ix_it_assets_available", "status", "is_active"),
    )


class ITAssetAssignment(Base, TimestampMixin):
    """
    IT Asset assignments to users.
    Uses user_code instead of user_id.
    """
    __tablename__ = "it_asset_assignments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Asset reference
    asset_id = Column(UUID(as_uuid=True), ForeignKey("it_assets.id"), nullable=False)
    
    # User reference - using user_code
    user_code = Column(String(10), ForeignKey("users.user_code"), nullable=False)
    
    # Assignment details
    assigned_by_code = Column(String(10), ForeignKey("users.user_code"), nullable=False)
    assigned_at = Column(DateTime(timezone=True), nullable=False)
    
    # Return details
    returned_at = Column(DateTime(timezone=True), nullable=True)
    returned_to_code = Column(String(10), ForeignKey("users.user_code"), nullable=True)
    return_condition = Column(String(100), nullable=True)  # good, damaged, needs_repair
    
    is_active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    
    # Acknowledgement
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    acknowledgement_notes = Column(Text, nullable=True)
    
    # Relationships
    asset = relationship("ITAsset", back_populates="assignments")
    user = relationship("User", foreign_keys=[user_code], primaryjoin="ITAssetAssignment.user_code == User.user_code")
    assigned_by = relationship("User", foreign_keys=[assigned_by_code], primaryjoin="ITAssetAssignment.assigned_by_code == User.user_code")
    returned_to = relationship("User", foreign_keys=[returned_to_code], primaryjoin="ITAssetAssignment.returned_to_code == User.user_code")
    
    __table_args__ = (
        Index("ix_asset_assignment_active", "asset_id", "is_active"),
        Index("ix_asset_assignment_user", "user_code", "is_active"),
    )