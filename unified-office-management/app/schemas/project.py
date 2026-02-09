from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date
from uuid import UUID

from ..models.enums import ProjectStatus


class ProjectMemberCreate(BaseModel):
    """Project member creation schema."""
    user_id: UUID
    role: str = "member"


class ProjectBase(BaseModel):
    """Base project schema."""
    title: str = Field(..., min_length=1, max_length=300)
    description: str = Field(..., min_length=1)
    duration_days: int = Field(..., ge=1)
    justification: Optional[str] = None
    start_date: Optional[date] = None


class ProjectCreate(ProjectBase):
    """Project creation schema."""
    members: List[ProjectMemberCreate] = []


class ProjectUpdate(BaseModel):
    """Project update schema."""
    title: Optional[str] = None
    description: Optional[str] = None
    duration_days: Optional[int] = None
    justification: Optional[str] = None
    start_date: Optional[date] = None


class ProjectApproval(BaseModel):
    """Project approval schema."""
    action: str = Field(..., pattern="^(approve|reject)$")
    notes: Optional[str] = None
    rejection_reason: Optional[str] = None


class ProjectMemberResponse(BaseModel):
    """Project member response schema."""
    id: UUID
    user_id: UUID
    role: str
    is_active: bool
    
    class Config:
        from_attributes = True


class ProjectResponse(BaseModel):
    """Project response schema."""
    id: UUID
    title: str
    description: str
    requested_by_id: UUID
    duration_days: int
    justification: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: ProjectStatus
    approved_by_id: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    approval_notes: Optional[str] = None
    rejection_reason: Optional[str] = None
    members: List[ProjectMemberResponse] = []
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True