from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID

from ..models.enums import LeaveType, LeaveStatus


class LeaveRequestCreate(BaseModel):
    """
    Leave request creation schema.
    
    Approval flow depends on user role:
    - Employee: Team Lead -> Manager
    - Team Lead: Manager only
    - Manager: Super Admin only
    """
    leave_type: LeaveType
    start_date: date
    end_date: date
    reason: Optional[str] = None
    is_half_day: bool = False
    half_day_type: Optional[str] = None  # first_half, second_half
    emergency_contact: Optional[str] = None
    emergency_phone: Optional[str] = None
    
    @field_validator('end_date')
    @classmethod
    def validate_dates(cls, v, info):
        start = info.data.get('start_date')
        if start and v < start:
            raise ValueError('End date must be on or after start date')
        return v
    
    @field_validator('half_day_type')
    @classmethod
    def validate_half_day(cls, v, info):
        is_half_day = info.data.get('is_half_day')
        if is_half_day and not v:
            raise ValueError('half_day_type is required when is_half_day is True')
        if v and v not in ['first_half', 'second_half']:
            raise ValueError('half_day_type must be either first_half or second_half')
        return v


class LeaveRequestUpdate(BaseModel):
    """Leave request update schema (only for PENDING status)."""
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    reason: Optional[str] = None
    is_half_day: Optional[bool] = None
    half_day_type: Optional[str] = None
    emergency_contact: Optional[str] = None
    emergency_phone: Optional[str] = None


class LeaveApproval(BaseModel):
    """
    Leave approval schema.
    
    Used by:
    - Team Lead: To approve Employee leave (level 1)
    - Manager: To approve Team Lead leave OR Employee leave (level 2)
    - Super Admin: To approve Manager leave
    """
    action: str = Field(..., pattern="^(approve|reject)$")
    notes: Optional[str] = None
    rejection_reason: Optional[str] = None  # Required if action is 'reject'


class LeaveCancellation(BaseModel):
    """Leave cancellation schema."""
    reason: Optional[str] = None


class LeaveTypeResponse(BaseModel):
    """Leave type configuration response."""
    id: UUID
    name: str
    code: LeaveType
    default_days: int
    is_paid: bool
    requires_approval: bool
    is_active: bool
    description: Optional[str] = None
    can_carry_forward: bool
    max_carry_forward_days: int
    
    class Config:
        from_attributes = True


class LeaveBalanceResponse(BaseModel):
    """Leave balance response schema with user_code."""
    id: UUID
    user_code: str
    leave_type: LeaveType
    leave_type_name: Optional[str] = None
    year: int
    total_days: Decimal
    used_days: Decimal
    pending_days: Decimal
    available_days: float
    
    class Config:
        from_attributes = True


class LeaveRequestResponse(BaseModel):
    """Leave request response schema with user_code."""
    id: UUID
    user_code: str
    leave_type: LeaveType
    leave_type_name: Optional[str] = None
    start_date: date
    end_date: date
    total_days: Decimal
    is_half_day: bool
    half_day_type: Optional[str] = None
    reason: Optional[str] = None
    status: LeaveStatus
    
    # Level 1 approval (Team Lead for employees)
    level1_approver_code: Optional[str] = None
    level1_approver_name: Optional[str] = None
    level1_approved_at: Optional[datetime] = None
    level1_notes: Optional[str] = None
    
    # Final approval
    final_approver_code: Optional[str] = None
    final_approver_name: Optional[str] = None
    final_approved_at: Optional[datetime] = None
    final_approval_notes: Optional[str] = None
    
    # Rejection
    rejection_reason: Optional[str] = None
    rejected_by_code: Optional[str] = None
    rejected_at: Optional[datetime] = None
    
    # Cancellation
    cancelled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None
    
    # Emergency contact
    emergency_contact: Optional[str] = None
    emergency_phone: Optional[str] = None
    
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class LeaveRequestDetailResponse(LeaveRequestResponse):
    """Detailed leave request with user info."""
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    user_department: Optional[str] = None
    
    class Config:
        from_attributes = True


class LeaveRequestListResponse(BaseModel):
    """Paginated leave request list response."""
    leave_requests: List[LeaveRequestDetailResponse]
    total: int
    page: int
    page_size: int


class PendingLeaveApprovalResponse(BaseModel):
    """Response for pending leave approvals."""
    request_id: UUID
    user_code: str
    user_name: str
    leave_type: LeaveType
    start_date: date
    end_date: date
    total_days: Decimal
    reason: Optional[str] = None
    status: LeaveStatus
    created_at: datetime
    
    class Config:
        from_attributes = True


class LeaveBalanceSummary(BaseModel):
    """Summary of all leave balances for a user."""
    user_code: str
    user_name: str
    year: int
    balances: List[LeaveBalanceResponse]