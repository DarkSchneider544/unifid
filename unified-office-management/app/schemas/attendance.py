from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date
from uuid import UUID

from ..models.enums import AttendanceStatus


class AttendanceEntryCreate(BaseModel):
    """Attendance entry creation schema."""
    check_in: datetime
    check_out: Optional[datetime] = None
    entry_type: str = "regular"
    notes: Optional[str] = None


class AttendanceCreate(BaseModel):
    """Attendance creation schema."""
    date: date
    entries: List[AttendanceEntryCreate] = Field(default=[])


class AttendanceEntryResponse(BaseModel):
    """Attendance entry response schema."""
    id: UUID
    check_in: datetime
    check_out: Optional[datetime] = None
    entry_type: str
    notes: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class AttendanceResponse(BaseModel):
    """Attendance response schema."""
    id: UUID
    user_id: UUID
    date: date
    status: AttendanceStatus
    entries: List[AttendanceEntryResponse] = []
    approved_by_id: Optional[UUID] = None
    approval_notes: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class AttendanceApproval(BaseModel):
    """Attendance approval schema."""
    action: str = Field(..., pattern="^(approve|reject)$")
    notes: Optional[str] = None
    rejection_reason: Optional[str] = None


class AttendanceCheckIn(BaseModel):
    """Check-in schema."""
    notes: Optional[str] = None


class AttendanceCheckOut(BaseModel):
    """Check-out schema."""
    entry_id: UUID
    notes: Optional[str] = None


class AttendanceSubmit(BaseModel):
    """Submit attendance for approval schema."""
    notes: Optional[str] = None