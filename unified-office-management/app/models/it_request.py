from sqlalchemy import (
    Column, String, DateTime, ForeignKey, Text, Index, Enum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from .base import Base, TimestampMixin
from .enums import ITRequestType, ITRequestStatus


class ITRequest(Base, TimestampMixin):
    __tablename__ = "it_requests"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_number = Column(String(50), unique=True, nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    request_type = Column(Enum(ITRequestType), nullable=False)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("it_assets.id"), nullable=True)
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=False)
    priority = Column(String(20), default="medium")  # low, medium, high, critical
    status = Column(Enum(ITRequestStatus), default=ITRequestStatus.PENDING)
    
    # Approval
    approved_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approval_notes = Column(Text, nullable=True)
    
    # Assignment
    assigned_to_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    assigned_at = Column(DateTime(timezone=True), nullable=True)
    
    # Completion
    completed_at = Column(DateTime(timezone=True), nullable=True)
    completion_notes = Column(Text, nullable=True)
    
    rejection_reason = Column(Text, nullable=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    asset = relationship("ITAsset")
    approved_by = relationship("User", foreign_keys=[approved_by_id])
    assigned_to = relationship("User", foreign_keys=[assigned_to_id])
    
    __table_args__ = (
        Index("ix_it_request_user", "user_id"),
        Index("ix_it_request_status", "status"),
    )