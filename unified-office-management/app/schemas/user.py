from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID

from ..models.enums import UserRole, ManagerDomain
from ..core.config import settings


class UserBase(BaseModel):
    """Base user schema."""
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    department: Optional[str] = None
    phone: Optional[str] = None


class UserCreate(UserBase):
    """User creation schema."""
    employee_id: str = Field(..., min_length=1, max_length=50)
    email: Optional[EmailStr] = None  # Auto-generated if not provided
    password: str = Field(..., min_length=8)
    role: UserRole = UserRole.EMPLOYEE
    manager_domain: Optional[ManagerDomain] = None
    is_team_lead: bool = False
    team_lead_id: Optional[UUID] = None
    manager_id: Optional[UUID] = None
    
    @field_validator('email', mode='before')
    @classmethod
    def generate_email(cls, v, info):
        if v is None:
            first_name = info.data.get('first_name', '').lower()
            last_name = info.data.get('last_name', '').lower()
            return f"{first_name}.{last_name}@{settings.COMPANY_DOMAIN}"
        return v
    
    @field_validator('manager_domain', mode='before')
    @classmethod
    def validate_manager_domain(cls, v, info):
        role = info.data.get('role')
        if role == UserRole.MANAGER and v is None:
            raise ValueError('Manager domain is required for Manager role')
        if role != UserRole.MANAGER and v is not None:
            return None
        return v


class UserUpdate(BaseModel):
    """User update schema."""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    department: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None
    is_team_lead: Optional[bool] = None
    team_lead_id: Optional[UUID] = None
    manager_id: Optional[UUID] = None
    manager_domain: Optional[ManagerDomain] = None


class PasswordUpdateByAdmin(BaseModel):
    """Password update by admin schema."""
    new_password: str = Field(..., min_length=8)


class UserResponse(BaseModel):
    """User response schema."""
    id: UUID
    employee_id: str
    email: str
    first_name: str
    last_name: str
    full_name: str
    role: UserRole
    manager_domain: Optional[ManagerDomain] = None
    is_team_lead: bool
    is_active: bool
    department: Optional[str] = None
    phone: Optional[str] = None
    team_lead_id: Optional[UUID] = None
    manager_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """User list response schema."""
    users: List[UserResponse]
    total: int
    page: int
    page_size: int