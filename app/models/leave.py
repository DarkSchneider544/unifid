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
    
    # Carry forward settings
    can_carry_forward = Column(Boolean, default=False)
    max_carry_forward_days = Column(Integer, default=0)


class LeaveBalance(Base, TimestampMixin):
    """
    Yearly leave balance per user.
    Uses user_code instead of user_id.
    """
    __tablename__ = "leave_balances"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # User reference - using user_code
    user_code = Column(String(10), ForeignKey("users.user_code"), nullable=False)
    leave_type_id = Column(UUID(as_uuid=True), ForeignKey("leave_types.id"), nullable=False)
    year = Column(Integer, nullable=False)
    total_days = Column(Numeric(5, 1), nullable=False)
    used_days = Column(Numeric(5, 1), default=0)
    pending_days = Column(Numeric(5, 1), default=0)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_code], primaryjoin="LeaveBalance.user_code == User.user_code")
    leave_type = relationship("LeaveType")
    
    __table_args__ = (
        Index("ix_leave_balance_unique", "user_code", "leave_type_id", "year", unique=True),
    )
    
    @property
    def available_days(self) -> float:
        return float(self.total_days) - float(self.used_days) - float(self.pending_days)


class LeaveRequest(Base, TimestampMixin):
    """
    Leave request with hierarchical approval workflow.
    
    Approval Flow (based on user role):
    - EMPLOYEE leave -> TEAM_LEAD approves (level1) -> MANAGER approves (level2)
    - TEAM_LEAD leave -> MANAGER approves (direct)
    - MANAGER leave -> SUPER_ADMIN approves (direct)
    
    Uses user_code instead of user_id throughout.
    """
    __tablename__ = "leave_requests"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # User reference - using user_code
    user_code = Column(String(10), ForeignKey("users.user_code"), nullable=False)
    leave_type_id = Column(UUID(as_uuid=True), ForeignKey("leave_types.id"), nullable=False)
    
    # Leave period
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    total_days = Column(Numeric(5, 1), nullable=False)
    is_half_day = Column(Boolean, default=False)
    half_day_type = Column(String(20), nullable=True)  # first_half, second_half
    
    reason = Column(Text, nullable=True)
    status = Column(Enum(LeaveStatus), default=LeaveStatus.PENDING)
    
    # Level 1 approval (Team Lead approves Employee leave)
    # For Team Lead/Manager leaves, this is skipped
    level1_approver_code = Column(String(10), ForeignKey("users.user_code"), nullable=True)
    level1_approved_at = Column(DateTime(timezone=True), nullable=True)
    level1_notes = Column(Text, nullable=True)
    
    # Level 2 / Final approval
    # For Employee: Manager approves after Team Lead
    # For Team Lead: Manager approves directly
    # For Manager: Super Admin approves
    final_approver_code = Column(String(10), ForeignKey("users.user_code"), nullable=True)
    final_approved_at = Column(DateTime(timezone=True), nullable=True)
    final_approval_notes = Column(Text, nullable=True)
    
    rejection_reason = Column(Text, nullable=True)
    rejected_by_code = Column(String(10), ForeignKey("users.user_code"), nullable=True)
    rejected_at = Column(DateTime(timezone=True), nullable=True)
    
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    
    # Emergency contact during leave
    emergency_contact = Column(String(100), nullable=True)
    emergency_phone = Column(String(20), nullable=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_code], primaryjoin="LeaveRequest.user_code == User.user_code")
    leave_type = relationship("LeaveType")
    level1_approver = relationship("User", foreign_keys=[level1_approver_code], primaryjoin="LeaveRequest.level1_approver_code == User.user_code")
    final_approver = relationship("User", foreign_keys=[final_approver_code], primaryjoin="LeaveRequest.final_approver_code == User.user_code")
    rejected_by = relationship("User", foreign_keys=[rejected_by_code], primaryjoin="LeaveRequest.rejected_by_code == User.user_code")
    
    __table_args__ = (
        Index("ix_leave_request_user", "user_code", "start_date"),
        Index("ix_leave_request_status", "status"),
        Index("ix_leave_request_dates", "start_date", "end_date"),
    )