from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date, time
from decimal import Decimal
from uuid import UUID

from ..models.enums import AttendanceStatus


class AttendanceEntryCreate(BaseModel):
    """Attendance entry creation schema."""
    check_in: datetime
    check_out: Optional[datetime] = None
    entry_type: str = "regular"  # regular, break, overtime
    notes: Optional[str] = None


class AttendanceCreate(BaseModel):
    """Attendance creation schema (typically auto-created on check-in)."""
    date: date
    entries: List[AttendanceEntryCreate] = Field(default=[])


class AttendanceEntryResponse(BaseModel):
    """Attendance entry response schema."""
    id: UUID
    check_in: datetime
    check_out: Optional[datetime] = None
    entry_type: str
    duration_hours: Optional[Decimal] = None
    notes: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class AttendanceResponse(BaseModel):
    """Attendance response schema with user_code."""
    id: UUID
    user_code: str  # User identifier
    date: date
    status: AttendanceStatus
    
    # Summary times
    first_check_in: Optional[time] = None
    last_check_out: Optional[time] = None
    total_hours: Optional[Decimal] = None
    
    # Entries
    entries: List[AttendanceEntryResponse] = []
    
    # Approval info
    approved_by_code: Optional[str] = None
    approval_notes: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    rejected_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class AttendanceDetailResponse(AttendanceResponse):
    """Detailed attendance response with user info."""
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    approver_name: Optional[str] = None
    
    class Config:
        from_attributes = True


class AttendanceApproval(BaseModel):
    """
    Attendance approval schema.
    
    Used by:
    - Team Lead to approve Employee attendance
    - Manager to approve Team Lead attendance
    - Super Admin to approve Manager attendance
    """
    action: str = Field(..., pattern="^(approve|reject)$")
    notes: Optional[str] = None
    rejection_reason: Optional[str] = None  # Required if action is 'reject'


class AttendanceCheckIn(BaseModel):
    """Check-in schema."""
    entry_type: str = "regular"  # regular, break, overtime
    notes: Optional[str] = None


class AttendanceCheckOut(BaseModel):
    """Check-out schema."""
    entry_id: UUID
    notes: Optional[str] = None


class AttendanceSubmit(BaseModel):
    """Submit attendance for approval schema."""
    notes: Optional[str] = None


class AttendanceListResponse(BaseModel):
    """Paginated attendance list response."""
    attendances: List[AttendanceDetailResponse]
    total: int
    page: int
    page_size: int


class PendingApprovalResponse(BaseModel):
    """Response for pending approvals (for team leads and managers)."""
    attendance_id: UUID
    user_code: str
    user_name: str
    date: date
    first_check_in: Optional[time] = None
    last_check_out: Optional[time] = None
    total_hours: Optional[Decimal] = None
    submitted_at: Optional[datetime] = None
    status: AttendanceStatus
    
    class Config:
        from_attributes = True


class AttendanceSummary(BaseModel):
    """Attendance summary for a period."""
    user_code: str
    user_name: str
    period_start: date
    period_end: date
    total_days_present: int
    total_hours_worked: Decimal
    pending_approvals: int
    approved_days: int
    rejected_days: int