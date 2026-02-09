from sqlalchemy import (
    Column, String, Boolean, DateTime, Date, ForeignKey, Text, 
    Index, Enum, Integer, Numeric
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from .base import Base, TimestampMixin
from .enums import LeaveType as LeaveTypeEnum, LeaveStatus


class LeaveType(Base, TimestampMixin):
    """Leave type configuration."""
    __tablename__ = "leave_types"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    code = Column(Enum(LeaveTypeEnum), unique=True, nullable=False)
    default_days = Column(Integer, default=0)
    is_paid = Column(Boolean, default=True)
    requires_approval = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    description = Column(Text, nullable=True)


class LeaveBalance(Base, TimestampMixin):
    """Yearly leave balance per user."""
    __tablename__ = "leave_balances"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    leave_type_id = Column(UUID(as_uuid=True), ForeignKey("leave_types.id"), nullable=False)
    year = Column(Integer, nullable=False)
    total_days = Column(Numeric(5, 1), nullable=False)
    used_days = Column(Numeric(5, 1), default=0)
    pending_days = Column(Numeric(5, 1), default=0)
    
    # Relationships
    user = relationship("User")
    leave_type = relationship("LeaveType")
    
    __table_args__ = (
        Index("ix_leave_balance_unique", "user_id", "leave_type_id", "year", unique=True),
    )
    
    @property
    def available_days(self) -> float:
        return float(self.total_days) - float(self.used_days) - float(self.pending_days)


class LeaveRequest(Base, TimestampMixin):
    __tablename__ = "leave_requests"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    leave_type_id = Column(UUID(as_uuid=True), ForeignKey("leave_types.id"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    total_days = Column(Numeric(5, 1), nullable=False)
    reason = Column(Text, nullable=True)
    status = Column(Enum(LeaveStatus), default=LeaveStatus.PENDING)
    
    # Level 1 approval (Team Lead)
    level1_approved_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    level1_approved_at = Column(DateTime(timezone=True), nullable=True)
    level1_notes = Column(Text, nullable=True)
    
    # Level 2 approval (Manager)
    approved_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approval_notes = Column(Text, nullable=True)
    
    rejection_reason = Column(Text, nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    leave_type = relationship("LeaveType")
    level1_approved_by = relationship("User", foreign_keys=[level1_approved_by_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])
    
    __table_args__ = (
        Index("ix_leave_request_user", "user_id", "start_date"),
        Index("ix_leave_request_status", "status"),
    )