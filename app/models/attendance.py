from sqlalchemy import (
    Column, String, DateTime, Date, ForeignKey, Text, Index, Enum, Time, Numeric
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from .base import Base, TimestampMixin
from .enums import AttendanceStatus


class Attendance(Base, TimestampMixin):
    """
    Attendance model with hierarchical approval workflow.
    
    Approval Flow (based on user role):
    - EMPLOYEE attendance -> Approved by TEAM_LEAD
    - TEAM_LEAD attendance -> Approved by MANAGER
    - MANAGER attendance -> Approved by SUPER_ADMIN
    
    Workflow:
    1. User checks in (status = DRAFT)
    2. User checks out
    3. User submits for approval (status = PENDING_APPROVAL)
    4. Approver approves/rejects (status = APPROVED/REJECTED)
    
    Note: Uses user_code as the primary reference instead of user_id
    """
    __tablename__ = "attendances"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # User reference - using user_code instead of user_id
    user_code = Column(String(10), ForeignKey("users.user_code"), nullable=False)
    
    # Date and status
    date = Column(Date, nullable=False)
    status = Column(Enum(AttendanceStatus), default=AttendanceStatus.DRAFT)
    
    # First check-in and last check-out of the day (summary)
    first_check_in = Column(Time, nullable=True)
    last_check_out = Column(Time, nullable=True)
    total_hours = Column(Numeric(5, 2), nullable=True)
    
    # Approval workflow - using user_code
    # For employees: approved by team_lead
    # For team_leads: approved by manager
    # For managers: approved by super_admin
    approved_by_code = Column(String(10), ForeignKey("users.user_code"), nullable=True)
    approval_notes = Column(Text, nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    rejected_at = Column(DateTime(timezone=True), nullable=True)
    
    # Submission tracking
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_code], primaryjoin="Attendance.user_code == User.user_code")
    approved_by = relationship("User", foreign_keys=[approved_by_code], primaryjoin="Attendance.approved_by_code == User.user_code")
    entries = relationship("AttendanceEntry", back_populates="attendance", order_by="AttendanceEntry.check_in")
    
    __table_args__ = (
        Index("ix_attendance_user_date", "user_code", "date", unique=True),
        Index("ix_attendance_status", "status"),
        Index("ix_attendance_date", "date"),
    )


class AttendanceEntry(Base, TimestampMixin):
    """
    Individual attendance entries (check-in/check-out pairs).
    Supports multiple entries per day (breaks, overtime, etc.)
    """
    __tablename__ = "attendance_entries"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    attendance_id = Column(UUID(as_uuid=True), ForeignKey("attendances.id"), nullable=False)
    
    # Check-in/out times
    check_in = Column(DateTime(timezone=True), nullable=False)
    check_out = Column(DateTime(timezone=True), nullable=True)
    
    # Entry type: regular, break, overtime
    entry_type = Column(String(50), default="regular")
    
    # Duration in hours (calculated on check-out)
    duration_hours = Column(Numeric(5, 2), nullable=True)
    
    notes = Column(Text, nullable=True)
    
    # Relationships
    attendance = relationship("Attendance", back_populates="entries")