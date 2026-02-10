from sqlalchemy import (
    Column, String, DateTime, ForeignKey, Text, Index, Enum, event
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
import random
import string
from datetime import datetime, timezone

from .base import Base, TimestampMixin
from .enums import ITRequestType, ITRequestStatus, ITRequestPriority


def generate_request_number():
    """Generate a unique request number: ITR-YYYYMMDD-XXXX"""
    date_str = datetime.now(timezone.utc).strftime('%Y%m%d')
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"ITR-{date_str}-{random_str}"


class ITRequest(Base, TimestampMixin):
    """
    IT Support requests.
    Managed by IT admin.
    Uses user_code instead of user_id.
    """
    __tablename__ = "it_requests"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Request identification
    request_number = Column(String(50), unique=True, nullable=False, index=True)
    
    # Requester - using user_code
    user_code = Column(String(10), ForeignKey("users.user_code"), nullable=False)
    
    # Request details
    request_type = Column(Enum(ITRequestType), nullable=False)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("it_assets.id"), nullable=True)
    
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=False)
    priority = Column(Enum(ITRequestPriority), default=ITRequestPriority.MEDIUM)
    status = Column(Enum(ITRequestStatus), default=ITRequestStatus.PENDING)
    
    # Approval - using user_code
    approved_by_code = Column(String(10), ForeignKey("users.user_code"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approval_notes = Column(Text, nullable=True)
    
    # Assignment - using user_code
    assigned_to_code = Column(String(10), ForeignKey("users.user_code"), nullable=True)
    assigned_at = Column(DateTime(timezone=True), nullable=True)
    
    # Progress tracking
    in_progress_at = Column(DateTime(timezone=True), nullable=True)
    
    # Completion
    completed_at = Column(DateTime(timezone=True), nullable=True)
    completion_notes = Column(Text, nullable=True)
    resolution_summary = Column(Text, nullable=True)
    
    # Rejection
    rejection_reason = Column(Text, nullable=True)
    rejected_at = Column(DateTime(timezone=True), nullable=True)
    rejected_by_code = Column(String(10), ForeignKey("users.user_code"), nullable=True)
    
    # Cancellation
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_code], primaryjoin="ITRequest.user_code == User.user_code")
    asset = relationship("ITAsset")
    approved_by = relationship("User", foreign_keys=[approved_by_code], primaryjoin="ITRequest.approved_by_code == User.user_code")
    assigned_to = relationship("User", foreign_keys=[assigned_to_code], primaryjoin="ITRequest.assigned_to_code == User.user_code")
    rejected_by = relationship("User", foreign_keys=[rejected_by_code], primaryjoin="ITRequest.rejected_by_code == User.user_code")
    
    __table_args__ = (
        Index("ix_it_request_user", "user_code"),
        Index("ix_it_request_status", "status"),
        Index("ix_it_request_priority", "priority"),
        Index("ix_it_request_type", "request_type"),
        Index("ix_it_request_assigned", "assigned_to_code", "status"),
    )


# Event listener to auto-generate request_number if not set
@event.listens_for(ITRequest, 'before_insert')
def generate_request_number_before_insert(mapper, connection, target):
    """Auto-generate a unique request number before inserting."""
    if not target.request_number:
        target.request_number = generate_request_number()