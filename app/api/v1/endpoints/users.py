from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID

from ....core.database import get_db
from ....core.dependencies import (
    get_current_active_user, require_admin_or_above, require_super_admin
)
from ....models.user import User
from ....models.enums import UserRole, ManagerType
from ....schemas.user import (
    UserCreate, UserUpdate, UserResponse, PasswordUpdateByAdmin, UserRoleChange
)
from ....schemas.base import APIResponse, PaginatedResponse
from ....services.user_service import UserService
from ....services.auth_service import AuthService
from ....utils.response import create_response, create_paginated_response

router = APIRouter()


@router.get("/me", response_model=APIResponse[UserResponse])
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user's profile."""
    return create_response(
        data=UserResponse.model_validate(current_user),
        message="Profile retrieved successfully"
    )


@router.post("", response_model=APIResponse[UserResponse])
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(require_admin_or_above),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new user - Only SUPER_ADMIN and ADMIN can create users.
    
    Required fields:
    - first_name, last_name (required)
    - password (required)
    - role (required - ADMIN, MANAGER, TEAM_LEAD, or EMPLOYEE)
    
    Optional fields:
    - email (auto-generated from name if not provided)
    - phone (optional)
    - vehicle_number, vehicle_type (optional)
    - manager_type (required when role is MANAGER)
    - department (required when role is TEAM_LEAD)
    - team_lead_code (optional when role is EMPLOYEE)
    - manager_code (optional - for hierarchy assignment)
    - admin_code (optional - for hierarchy assignment)
    
    Permission rules:
    - SUPER_ADMIN can create: ADMIN, MANAGER, TEAM_LEAD, EMPLOYEE
    - ADMIN can create: MANAGER, TEAM_LEAD, EMPLOYEE
    """
    user_service = UserService(db)
    user, error = await user_service.create_user(user_data, current_user)
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return create_response(
        data=UserResponse.model_validate(user),
        message="User created successfully"
    )


@router.get("", response_model=PaginatedResponse[UserResponse])
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    role: Optional[UserRole] = None,
    manager_type: Optional[ManagerType] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    current_user: User = Depends(require_admin_or_above),
    db: AsyncSession = Depends(get_db)
):
    """List users with filtering. Admin+ required."""
    user_service = UserService(db)
    users, total = await user_service.list_users(
        page=page,
        page_size=page_size,
        role=role,
        manager_type=manager_type,
        is_active=is_active,
        search=search,
        requesting_user=current_user
    )
    
    return create_paginated_response(
        data=[UserResponse.model_validate(u) for u in users],
        total=total,
        page=page,
        page_size=page_size,
        message="Users retrieved successfully"
    )


@router.get("/{user_id}", response_model=APIResponse[UserResponse])
async def get_user(
    user_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user by ID."""
    user_service = UserService(db)
    user = await user_service.get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Non-admin users can only view their own profile
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
        if str(user.id) != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot view other users' profiles"
            )
    
    return create_response(
        data=UserResponse.model_validate(user),
        message="User retrieved successfully"
    )


@router.put("/{user_id}", response_model=APIResponse[UserResponse])
async def update_user(
    user_id: UUID,
    user_data: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user details."""
    user_service = UserService(db)
    user, error = await user_service.update_user(user_id, user_data, current_user)
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return create_response(
        data=UserResponse.model_validate(user),
        message="User updated successfully"
    )


@router.delete("/{user_id}", response_model=APIResponse)
async def delete_user(
    user_id: UUID,
    current_user: User = Depends(require_admin_or_above),
    db: AsyncSession = Depends(get_db)
):
    """Soft delete a user. Admin+ required."""
    user_service = UserService(db)
    success, error = await user_service.soft_delete_user(user_id, current_user)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return create_response(message="User deleted successfully")


@router.post("/{user_id}/change-password", response_model=APIResponse)
async def admin_change_password(
    user_id: UUID,
    password_data: PasswordUpdateByAdmin,
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """Change any user's password. Super Admin only."""
    auth_service = AuthService(db)
    success = await auth_service.admin_change_password(
        str(user_id),
        password_data.new_password
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return create_response(message="Password changed successfully")


@router.post("/{user_id}/change-role", response_model=APIResponse[UserResponse])
async def change_user_role(
    user_id: UUID,
    role_data: UserRoleChange,
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """Change a user's role. Super Admin only."""
    user_service = UserService(db)
    user, error = await user_service.change_user_role(
        user_id, 
        role_data.new_role, 
        current_user,
        role_data.manager_type,
        role_data.department
    )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return create_response(
        data=UserResponse.model_validate(user),
        message=f"User role changed to {role_data.new_role.value}"
    )


@router.post("/{user_id}/toggle-active", response_model=APIResponse[UserResponse])
async def toggle_user_active(
    user_id: UUID,
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """Toggle user's active status. Super Admin only."""
    user_service = UserService(db)
    user, error = await user_service.toggle_user_active(user_id, current_user)
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return create_response(
        data=UserResponse.model_validate(user),
        message=f"User is now {'active' if user.is_active else 'inactive'}"
    )