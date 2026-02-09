from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID

from ..models.enums import LeaveType, LeaveStatus


class LeaveRequestCreate(BaseModel):
    """Leave request creation schema."""
    leave_type: LeaveType
    start_date: date
    end_date: date
    reason: Optional[str] = None
    
    @field_validator('end_date')
    @classmethod
    def validate_dates(cls, v, info):
        start = info.data.get('start_date')
        if start and v < start:
            raise ValueError('End date must be on or after start date')
        return v


class LeaveRequestUpdate(BaseModel):
    """Leave request update schema."""
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    reason: Optional[str] = None


class LeaveApproval(BaseModel):
    """Leave approval schema."""
    action: str = Field(..., pattern="^(approve|reject)$")
    notes: Optional[str] = None
    rejection_reason: Optional[str] = None


class LeaveBalanceResponse(BaseModel):
    """Leave balance response schema."""
    id: UUID
    user_id: UUID
    leave_type: LeaveType
    year: int
    total_days: Decimal
    used_days: Decimal
    pending_days: Decimal
    available_days: float
    
    class Config:
        from_attributes = True


class LeaveRequestResponse(BaseModel):
    """Leave request response schema."""
    id: UUID
    user_id: UUID
    leave_type: LeaveType
    start_date: date
    end_date: date
    total_days: Decimal
    reason: Optional[str] = None
    status: LeaveStatus
    level1_approved_by_id: Optional[UUID] = None
    level1_approved_at: Optional[datetime] = None
    level1_notes: Optional[str] = None
    approved_by_id: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    approval_notes: Optional[str] = None
    rejection_reason: Optional[str] = None
    cancelled_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True