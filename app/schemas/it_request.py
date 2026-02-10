from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID

from ..models.enums import ITRequestType, ITRequestStatus, ITRequestPriority


# ==================== IT Request Schemas ====================

class ITRequestBase(BaseModel):
    """Base IT request schema."""
    request_type: ITRequestType
    title: str = Field(..., min_length=1, max_length=300)
    description: str = Field(..., min_length=10, max_length=5000)
    priority: ITRequestPriority = ITRequestPriority.MEDIUM
    related_asset_code: Optional[str] = Field(None, description="Asset code if request is related to an asset")


class ITRequestCreate(ITRequestBase):
    """
    IT request creation schema.
    
    Available to all authenticated users.
    Request number is auto-generated: REQ-YYYYMMDD-XXXX
    """
    pass


class ITRequestUpdate(BaseModel):
    """IT request update schema (only for PENDING requests)."""
    title: Optional[str] = Field(None, min_length=1, max_length=300)
    description: Optional[str] = Field(None, min_length=10, max_length=5000)
    priority: Optional[ITRequestPriority] = None


class ITRequestApproval(BaseModel):
    """
    IT request approval schema.
    
    Only IT admin can approve/reject requests.
    """
    action: str = Field(..., pattern="^(approve|reject)$")
    notes: Optional[str] = Field(None, max_length=1000)
    rejection_reason: Optional[str] = Field(None, max_length=500)
    assigned_to_code: Optional[str] = Field(None, description="IT staff user code to assign the request to")


class ITRequestAssignment(BaseModel):
    """IT request assignment schema."""
    assigned_to_code: str = Field(..., description="IT staff user code")
    notes: Optional[str] = Field(None, max_length=500)


class ITRequestStatusUpdate(BaseModel):
    """
    IT request status update schema.
    
    Only IT admin can update status.
    """
    status: ITRequestStatus
    notes: Optional[str] = Field(None, max_length=1000)
    resolution_notes: Optional[str] = Field(None, max_length=2000)


class ITRequestResponse(BaseModel):
    """IT request response schema."""
    id: UUID
    request_number: str  # Auto-generated: REQ-YYYYMMDD-XXXX
    user_code: str
    user_name: str
    request_type: ITRequestType
    related_asset_id: Optional[UUID] = None
    related_asset_code: Optional[str] = None
    title: str
    description: str
    priority: ITRequestPriority
    status: ITRequestStatus
    approved_by_code: Optional[str] = None
    approved_by_name: Optional[str] = None
    approved_at: Optional[datetime] = None
    approval_notes: Optional[str] = None
    assigned_to_code: Optional[str] = None
    assigned_to_name: Optional[str] = None
    assigned_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    rejection_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ITRequestListResponse(BaseModel):
    """IT request list response schema."""
    requests: List[ITRequestResponse]
    total: int
    page: int
    page_size: int


class MyITRequestsResponse(BaseModel):
    """User's IT requests response."""
    open_requests: List[ITRequestResponse] = []
    closed_requests: List[ITRequestResponse] = []


# ==================== IT Admin Dashboard Schemas ====================

class ITRequestQueueResponse(BaseModel):
    """IT admin request queue response."""
    pending_approval: List[ITRequestResponse] = []
    approved_unassigned: List[ITRequestResponse] = []
    in_progress: List[ITRequestResponse] = []
    total_pending: int
    total_approved: int
    total_in_progress: int


class ITRequestStatistics(BaseModel):
    """IT request statistics for dashboard."""
    total_requests: int
    pending_requests: int
    in_progress_requests: int
    completed_today: int
    average_resolution_time_hours: float
    by_type: dict  # Request count by type
    by_priority: dict  # Request count by priority