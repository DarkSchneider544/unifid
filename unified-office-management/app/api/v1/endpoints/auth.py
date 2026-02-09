from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....core.dependencies import get_current_active_user
from ....models.user import User
from ....schemas.auth import (
    LoginRequest, LoginResponse, TokenRefreshRequest,
    TokenRefreshResponse, PasswordChangeRequest
)
from ....schemas.base import APIResponse
from ....services.auth_service import AuthService
from ....utils.response import create_response

router = APIRouter()


@router.post("/login", response_model=APIResponse[LoginResponse])
async def login(
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate user with email and password.
    
    Returns JWT access and refresh tokens on successful authentication.
    Use the access_token in the Authorization header as: Bearer <access_token>
    """
    auth_service = AuthService(db)
    user = await auth_service.authenticate_user(login_data.email, login_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    login_response = auth_service.create_tokens(user)
    return create_response(data=login_response, message="Login successful")


@router.post("/refresh", response_model=APIResponse[TokenRefreshResponse])
async def refresh_token(
    token_data: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db)
):
    """Refresh access token."""
    auth_service = AuthService(db)
    result = await auth_service.refresh_access_token(token_data.refresh_token)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    access_token, expires_in = result
    return create_response(
        data=TokenRefreshResponse(
            access_token=access_token,
            expires_in=expires_in
        ),
        message="Token refreshed"
    )


@router.post("/change-password", response_model=APIResponse)
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Change current user's password."""
    if password_data.new_password != password_data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New passwords do not match"
        )
    
    auth_service = AuthService(db)
    success = await auth_service.change_password(
        current_user,
        password_data.current_password,
        password_data.new_password
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    return create_response(message="Password changed successfully")


@router.get("/me", response_model=APIResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user information."""
    from ....schemas.user import UserResponse
    return create_response(
        data=UserResponse.model_validate(current_user),
        message="User info retrieved"
    )