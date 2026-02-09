from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class LoginRequest(BaseModel):
    """Login request schema."""
    email: EmailStr
    password: str = Field(..., min_length=8)


class LoginResponse(BaseModel):
    """Login response schema."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    role: str
    manager_domain: Optional[str] = None
    is_team_lead: bool = False


class TokenRefreshRequest(BaseModel):
    """Token refresh request schema."""
    refresh_token: str


class TokenRefreshResponse(BaseModel):
    """Token refresh response schema."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class PasswordChangeRequest(BaseModel):
    """Password change request schema."""
    current_password: str = Field(..., min_length=8)
    new_password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)


class TokenPayload(BaseModel):
    """JWT token payload schema."""
    user_id: str
    role: str
    manager_domain: Optional[str] = None
    is_team_lead: bool = False
    exp: datetime
    type: str  # access or refresh