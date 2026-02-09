from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List

from .database import get_db
from .security import decode_token
from ..models.user import User
from ..models.enums import UserRole, ManagerDomain

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


class DomainChecker:
    """Dependency for checking manager domain access."""
    
    def __init__(self, required_domains: List[ManagerDomain]):
        self.required_domains = required_domains
    
    async def __call__(
        self,
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        # Super Admin and Admin have access to all domains
        if current_user.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
            return current_user
        
        # Managers must have the required domain
        if current_user.role == UserRole.MANAGER:
            if current_user.manager_domain not in self.required_domains:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Domain access denied"
                )
        
        return current_user


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