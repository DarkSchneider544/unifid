from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime, date
from uuid import UUID
import re

from ..models.enums import ProjectStatus


# ==================== Project Member Schemas ====================

class ProjectMemberCreate(BaseModel):
    """Project member creation schema."""
    user_code: str = Field(..., description="User code of the member to add")
    role: str = Field(default="member", max_length=50)
    
    @field_validator('user_code')
    @classmethod
    def validate_user_code(cls, v):
        if not re.match(r'^[A-Z]{2}\d{4}$', v.upper()):
            raise ValueError('Invalid user code format. Expected format: AA0000')
        return v.upper()


class ProjectMemberUpdate(BaseModel):
    """Project member update schema."""
    role: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None


class ProjectMemberResponse(BaseModel):
    """Project member response schema."""
    id: UUID
    project_id: UUID
    user_code: str
    user_name: str
    user_email: str
    role: str
    is_active: bool
    joined_at: datetime
    left_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# ==================== Project Schemas ====================

class ProjectBase(BaseModel):
    """Base project schema."""
    title: str = Field(..., min_length=1, max_length=300)
    description: str = Field(..., min_length=10, max_length=5000)
    duration_days: int = Field(..., ge=1, le=365)
    justification: Optional[str] = Field(None, max_length=2000)
    start_date: Optional[date] = None
    
    @field_validator('start_date')
    @classmethod
    def validate_start_date(cls, v):
        if v and v < date.today():
            raise ValueError('Start date cannot be in the past')
        return v


class ProjectCreate(ProjectBase):
    """
    Project creation schema.
    
    project_code is auto-generated: PRJ-YYYYMMDD-XXXX
    Only MANAGER and TEAM_LEAD can create projects.
    """
    members: List[ProjectMemberCreate] = []


class ProjectUpdate(BaseModel):
    """Project update schema (only for PENDING projects)."""
    title: Optional[str] = Field(None, min_length=1, max_length=300)
    description: Optional[str] = Field(None, min_length=10, max_length=5000)
    duration_days: Optional[int] = Field(None, ge=1, le=365)
    justification: Optional[str] = Field(None, max_length=2000)
    start_date: Optional[date] = None


class ProjectApproval(BaseModel):
    """
    Project approval schema.
    
    Approval hierarchy:
    - Team Lead's project: Approved by Manager
    - Manager's project: Approved by Super Admin
    """
    action: str = Field(..., pattern="^(approve|reject)$")
    notes: Optional[str] = Field(None, max_length=1000)
    rejection_reason: Optional[str] = Field(None, max_length=500)


class ProjectStatusUpdate(BaseModel):
    """Project status update schema."""
    status: ProjectStatus
    notes: Optional[str] = Field(None, max_length=1000)


class ProjectResponse(BaseModel):
    """Project response schema."""
    id: UUID
    project_code: str  # Auto-generated: PRJ-YYYYMMDD-XXXX
    title: str
    description: str
    requested_by_code: str
    requested_by_name: str
    duration_days: int
    justification: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: ProjectStatus
    approved_by_code: Optional[str] = None
    approved_by_name: Optional[str] = None
    approved_at: Optional[datetime] = None
    approval_notes: Optional[str] = None
    rejection_reason: Optional[str] = None
    member_count: int = 0
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ProjectDetailResponse(ProjectResponse):
    """Detailed project response with members."""
    members: List[ProjectMemberResponse] = []
    
    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    """Project list response schema."""
    projects: List[ProjectResponse]
    total: int
    page: int
    page_size: int


class MyProjectsResponse(BaseModel):
    """User's projects response."""
    owned_projects: List[ProjectResponse] = []  # Projects created by user
    member_projects: List[ProjectResponse] = []  # Projects user is a member of


# ==================== Project Statistics ====================

class ProjectStatistics(BaseModel):
    """Project statistics for dashboard."""
    total_projects: int
    pending_projects: int
    approved_projects: int
    active_projects: int
    completed_projects: int
    by_status: dict  # Project count by status