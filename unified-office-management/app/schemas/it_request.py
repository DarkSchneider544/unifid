from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID

from ..models.enums import ITRequestType, ITRequestStatus


class ITRequestBase(BaseModel):
    """Base IT request schema."""
    request_type: ITRequestType
    title: str = Field(..., min_length=1, max_length=300)
    description: str = Field(..., min_length=1)
    priority: str = Field(default="medium", pattern="^(low|medium|high|critical)$")
    asset_id: Optional[UUID] = None


class ITRequestCreate(ITRequestBase):
    """IT request creation schema."""
    pass


class ITRequestUpdate(BaseModel):
    """IT request update schema."""
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None


class ITRequestApproval(BaseModel):
    """IT request approval schema."""
    action: str = Field(..., pattern="^(approve|reject)$")
    notes: Optional[str] = None
    rejection_reason: Optional[str] = None
    assigned_to_id: Optional[UUID] = None


class ITRequestStatusUpdate(BaseModel):
    """IT request status update schema."""
    status: ITRequestStatus
    notes: Optional[str] = None


class ITRequestResponse(BaseModel):
    """IT request response schema."""
    id: UUID
    request_number: str
    user_id: UUID
    request_type: ITRequestType
    asset_id: Optional[UUID] = None
    title: str
    description: str
    priority: str
    status: ITRequestStatus
    approved_by_id: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    approval_notes: Optional[str] = None
    assigned_to_id: Optional[UUID] = None
    assigned_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    completion_notes: Optional[str] = None
    rejection_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True