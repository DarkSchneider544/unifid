from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List, Callable

from .database import get_db
from .security import decode_token
from ..models.user import User
from ..models.enums import UserRole, ManagerType

# JWT Bearer token authentication
bearer_scheme = HTTPBearer(
    scheme_name="JWT",
    description="Enter your JWT access token",
    auto_error=True
)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get the current authenticated user from JWT Bearer token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = credentials.credentials
    payload = decode_token(token)
    if payload is None:
        raise credentials_exception
    
    if payload.get("type") != "access":
        raise credentials_exception
    
    user_id: Optional[str] = payload.get("user_id")
    if user_id is None:
        raise credentials_exception
    
    result = await db.execute(
        select(User).where(User.id == user_id, User.is_deleted == False)
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated"
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Ensure the current user is active."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


class RoleChecker:
    """Dependency for checking user roles."""
    
    def __init__(self, allowed_roles: List[UserRole]):
        self.allowed_roles = allowed_roles
    
    async def __call__(
        self,
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return current_user


class ManagerTypeChecker:
    """
    Dependency for checking manager type access for MANAGEMENT operations.
    
    This is for operations that ONLY managers of specific types (or admins) can perform.
    Examples: Managing parking slots, approving IT requests, etc.
    """
    
    def __init__(self, required_types: List[ManagerType]):
        self.required_types = required_types
    
    async def __call__(
        self,
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        # Super Admin has access to all manager types
        if current_user.role == UserRole.SUPER_ADMIN:
            return current_user
        
        # Admin has access to all manager types
        if current_user.role == UserRole.ADMIN:
            return current_user
        
        # Managers must have the required manager type
        if current_user.role == UserRole.MANAGER:
            if current_user.manager_type not in self.required_types:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Only {', '.join([t.value for t in self.required_types])} Manager can perform this action"
                )
            return current_user
        
        # Non-managers denied for management operations
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Manager access required"
        )


def is_manager_of_type(user: User, manager_types: List[ManagerType]) -> bool:
    """
    Helper function to check if user is a manager of specific type(s).
    Returns True for Super Admin and Admin as well.
    """
    if user.role == UserRole.SUPER_ADMIN:
        return True
    if user.role == UserRole.ADMIN:
        return True
    if user.role == UserRole.MANAGER and user.manager_type in manager_types:
        return True
    return False


def check_manager_permission(user: User, required_types: List[ManagerType], action: str = "perform this action") -> None:
    """
    Helper function to check manager permissions in endpoints.
    Raises HTTPException if user doesn't have permission.
    
    Usage in endpoints:
        check_manager_permission(current_user, [ManagerType.PARKING], "manage parking")
    """
    if not is_manager_of_type(user, required_types):
        type_names = ', '.join([t.value.replace('_', ' ').title() for t in required_types])
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Only {type_names} Manager can {action}"
        )


# Common role combinations
require_super_admin = RoleChecker([UserRole.SUPER_ADMIN])
require_admin_or_above = RoleChecker([UserRole.SUPER_ADMIN, UserRole.ADMIN])
require_manager_or_above = RoleChecker([
    UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.MANAGER
])
require_team_lead_or_above = RoleChecker([
    UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.MANAGER, UserRole.TEAM_LEAD
])
require_any_authenticated = RoleChecker([
    UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.MANAGER, 
    UserRole.TEAM_LEAD, UserRole.EMPLOYEE
])

# Manager type specific checkers for MANAGEMENT operations
# Use these when ONLY managers of that type (+ admins) should have access
require_parking_manager = ManagerTypeChecker([ManagerType.PARKING])
require_attendance_manager = ManagerTypeChecker([ManagerType.ATTENDANCE])
require_desk_conference_manager = ManagerTypeChecker([ManagerType.DESK_CONFERENCE])
require_cafeteria_manager = ManagerTypeChecker([ManagerType.CAFETERIA])
require_it_support_manager = ManagerTypeChecker([ManagerType.IT_SUPPORT])