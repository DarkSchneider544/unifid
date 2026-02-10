from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID

from ..models.enums import UserRole, ManagerType, VehicleType
from ..core.config import settings


class UserBase(BaseModel):
    """Base user schema with common fields."""
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone: Optional[str] = None


class UserCreate(UserBase):
    """
    User creation schema - Only SUPER_ADMIN and ADMIN can create users.
    
    Required fields:
    - first_name, last_name (required)
    - password (required)
    - role (required - assigned by creator)
    
    Optional fields:
    - email (auto-generated from name + company domain if not provided)
    - phone (optional)
    - vehicle_number, vehicle_type (optional - for parking)
    - manager_type (required when role is MANAGER)
    - department (required when role is TEAM_LEAD)
    - team_lead_code (optional when role is EMPLOYEE)
    
    Auto-generated:
    - user_code: 6-character unique code (e.g., AB1234)
    - created_by_code: Set to creator's user_code
    - hierarchy codes: Auto-assigned based on creator and role
    
    Permission rules:
    - SUPER_ADMIN can create: ADMIN, MANAGER, TEAM_LEAD, EMPLOYEE
    - ADMIN can create: MANAGER, TEAM_LEAD, EMPLOYEE
    """
    email: Optional[EmailStr] = None  # Auto-generated if not provided
    password: str = Field(..., min_length=8)
    
    # Role - required, assigned by Admin/Super Admin
    role: UserRole
    
    # Manager type - required when role is MANAGER
    manager_type: Optional[ManagerType] = None
    
    # Department - required for TEAM_LEAD, optional for others
    department: Optional[str] = None
    
    # Team lead assignment - optional when creating EMPLOYEE
    team_lead_code: Optional[str] = None
    
    # Manager assignment - optional, auto-assigned if not provided
    manager_code: Optional[str] = None
    
    # Admin assignment - optional, auto-assigned if not provided  
    admin_code: Optional[str] = None
    
    # Vehicle info (for parking services)
    vehicle_number: Optional[str] = None
    vehicle_type: Optional[VehicleType] = None
    
    @model_validator(mode='after')
    def validate_role_fields(self):
        """Validate fields based on role."""
        if self.role == UserRole.MANAGER:
            if not self.manager_type:
                raise ValueError('manager_type is required for MANAGER role')
        
        if self.role == UserRole.TEAM_LEAD:
            if not self.department:
                raise ValueError('department is required for TEAM_LEAD role')
        
        if self.role == UserRole.SUPER_ADMIN:
            raise ValueError('Cannot create SUPER_ADMIN users')
        
        return self


class UserUpdate(BaseModel):
    """User update schema - limited fields that can be updated."""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = None
    is_active: Optional[bool] = None
    department: Optional[str] = None
    
    # Hierarchy updates (by superior only)
    team_lead_code: Optional[str] = None
    manager_code: Optional[str] = None
    admin_code: Optional[str] = None
    
    # Vehicle info
    vehicle_number: Optional[str] = None
    vehicle_type: Optional[VehicleType] = None
    
    # Manager only field
    manager_type: Optional[ManagerType] = None


class PasswordUpdate(BaseModel):
    """Password update by user."""
    current_password: str
    new_password: str = Field(..., min_length=8)


class PasswordUpdateByAdmin(BaseModel):
    """Password reset by admin - no current password needed."""
    new_password: str = Field(..., min_length=8)


class UserRoleChange(BaseModel):
    """Schema for changing user role (promotion/demotion)."""
    new_role: UserRole
    
    # Required if new_role is MANAGER
    manager_type: Optional[ManagerType] = None
    department: Optional[str] = None
    
    # Required based on role for approval hierarchy
    team_lead_code: Optional[str] = None
    manager_code: Optional[str] = None
    admin_code: Optional[str] = None
    
    @model_validator(mode='after')
    def validate_role_fields(self):
        """Validate fields based on new role."""
        if self.new_role == UserRole.MANAGER:
            if not self.manager_type:
                raise ValueError('manager_type is required when changing to MANAGER role')
            if not self.admin_code:
                raise ValueError('admin_code is required when changing to MANAGER role')
        elif self.new_role == UserRole.EMPLOYEE:
            if not self.team_lead_code:
                raise ValueError('team_lead_code is required when changing to EMPLOYEE role')
            if not self.manager_code:
                raise ValueError('manager_code is required when changing to EMPLOYEE role')
        elif self.new_role == UserRole.TEAM_LEAD:
            if not self.manager_code:
                raise ValueError('manager_code is required when changing to TEAM_LEAD role')
            if not self.department:
                raise ValueError('department is required when changing to TEAM_LEAD role')
        return self


class UserResponse(BaseModel):
    """User response schema."""
    id: UUID
    user_code: str  # Unique 6-character alphanumeric identifier
    email: str
    first_name: str
    last_name: str
    full_name: str
    role: UserRole
    manager_type: Optional[ManagerType] = None
    department: Optional[str] = None
    phone: Optional[str] = None
    
    # Hierarchy
    team_lead_code: Optional[str] = None
    manager_code: Optional[str] = None
    admin_code: Optional[str] = None
    created_by_code: Optional[str] = None
    
    # Vehicle
    vehicle_number: Optional[str] = None
    vehicle_type: Optional[str] = None
    
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class UserDetailResponse(UserResponse):
    """Detailed user response with hierarchy info."""
    team_lead: Optional['UserMinimalResponse'] = None
    manager: Optional['UserMinimalResponse'] = None
    admin: Optional['UserMinimalResponse'] = None
    creator: Optional['UserMinimalResponse'] = None
    
    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """Paginated user list response."""
    users: List[UserResponse]
    total: int
    page: int
    page_size: int


class UserMinimalResponse(BaseModel):
    """Minimal user info for references."""
    user_code: str  # 6-character unique identifier
    full_name: str
    role: UserRole
    email: str
    manager_type: Optional[ManagerType] = None
    department: Optional[str] = None
    
    class Config:
        from_attributes = True


class TeamMemberResponse(BaseModel):
    """Response for team members (for team leads and managers)."""
    user_code: str
    full_name: str
    email: str
    role: UserRole
    department: Optional[str] = None
    manager_type: Optional[ManagerType] = None
    is_active: bool
    
    class Config:
        from_attributes = True


class ManagerListResponse(BaseModel):
    """Response for listing managers under an admin."""
    managers: List['UserMinimalResponse']
    total: int
    
    class Config:
        from_attributes = True


class TeamLeadListResponse(BaseModel):
    """Response for listing team leads under a manager."""
    team_leads: List['UserMinimalResponse']
    total: int
    
    class Config:
        from_attributes = True


class EmployeeListResponse(BaseModel):
    """Response for listing employees under a team lead."""
    employees: List['UserMinimalResponse']
    total: int
    
    class Config:
        from_attributes = True


# Update forward reference
UserDetailResponse.model_rebuild()