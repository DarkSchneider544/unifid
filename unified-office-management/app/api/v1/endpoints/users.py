from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID

from ....core.database import get_db
from ....core.dependencies import (
    get_current_active_user, require_admin_or_above, require_super_admin
)
from ....models.user import User
from ....models.enums import UserRole
from ....schemas.user import (
    UserCreate, UserUpdate, UserResponse, PasswordUpdateByAdmin
)
from ....schemas.base import APIResponse, PaginatedResponse
from ....services.user_service import UserService
from ....services.auth_service import AuthService
from ....utils.response import create_response, create_paginated_response

router = APIRouter()


@router.post("", response_model=APIResponse[UserResponse])
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(require_admin_or_above),
    db: AsyncSession = Depends(get_db)
):
    """Create a new user. Admin+ required."""
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
    department: Optional[str] = None,
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
        department=department,
        is_active=is_active,
        search=search
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


@router.post("/{user_id}/promote-team-lead", response_model=APIResponse[UserResponse])
async def promote_to_team_lead(
    user_id: UUID,
    current_user: User = Depends(require_admin_or_above),
    db: AsyncSession = Depends(get_db)
):
    """Promote an employee to team lead. Admin+ required."""
    user_service = UserService(db)
    user, error = await user_service.promote_to_team_lead(user_id, current_user)
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return create_response(
        data=UserResponse.model_validate(user),
        message="User promoted to team lead"
    )