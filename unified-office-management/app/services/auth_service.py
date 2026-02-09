from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, Tuple
from datetime import timedelta

from ..models.user import User
from ..core.security import (
    verify_password, get_password_hash, 
    create_access_token, create_refresh_token, decode_token
)
from ..core.config import settings
from ..schemas.auth import LoginResponse


class AuthService:
    """Authentication service."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def authenticate_user(
        self, 
        email: str, 
        password: str
    ) -> Optional[User]:
        """Authenticate user with email and password."""
        result = await self.db.execute(
            select(User).where(
                User.email == email,
                User.is_deleted == False
            )
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        if not user.is_active:
            return None
        
        return user
    
    def create_tokens(self, user: User) -> LoginResponse:
        """Create access and refresh tokens for user."""
        token_data = {
            "user_id": str(user.id),
            "role": user.role.value,
            "manager_domain": user.manager_domain.value if user.manager_domain else None,
            "is_team_lead": user.is_team_lead
        }
        
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)
        
        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user_id=str(user.id),
            role=user.role.value,
            manager_domain=user.manager_domain.value if user.manager_domain else None,
            is_team_lead=user.is_team_lead
        )
    
    async def refresh_access_token(
        self, 
        refresh_token: str
    ) -> Optional[Tuple[str, int]]:
        """Refresh access token using refresh token."""
        payload = decode_token(refresh_token)
        
        if not payload:
            return None
        if payload.get("type") != "refresh":
            return None
        
        user_id = payload.get("user_id")
        if not user_id:
            return None
        
        # Verify user still exists and is active
        result = await self.db.execute(
            select(User).where(
                User.id == user_id,
                User.is_active == True,
                User.is_deleted == False
            )
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return None
        
        # Create new access token
        token_data = {
            "user_id": str(user.id),
            "role": user.role.value,
            "manager_domain": user.manager_domain.value if user.manager_domain else None,
            "is_team_lead": user.is_team_lead
        }
        
        new_access_token = create_access_token(token_data)
        expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        
        return new_access_token, expires_in
    
    async def change_password(
        self,
        user: User,
        current_password: str,
        new_password: str
    ) -> bool:
        """Change user's own password."""
        if not verify_password(current_password, user.hashed_password):
            return False
        
        user.hashed_password = get_password_hash(new_password)
        await self.db.commit()
        
        return True
    
    async def admin_change_password(
        self,
        target_user_id: str,
        new_password: str
    ) -> bool:
        """Admin changes another user's password."""
        result = await self.db.execute(
            select(User).where(
                User.id == target_user_id,
                User.is_deleted == False
            )
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return False
        
        user.hashed_password = get_password_hash(new_password)
        await self.db.commit()
        
        return True