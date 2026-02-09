from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class BuildingBase(BaseModel):
    """Base building schema."""
    name: str = Field(..., min_length=1, max_length=200)
    code: str = Field(..., min_length=1, max_length=50)
    address: Optional[str] = None
    total_floors: int = Field(default=1, ge=1)
    has_basement: bool = False
    basement_floors: int = Field(default=0, ge=0)
    description: Optional[str] = None


class BuildingCreate(BuildingBase):
    """Building creation schema."""
    pass


class BuildingUpdate(BaseModel):
    """Building update schema."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    address: Optional[str] = None
    total_floors: Optional[int] = Field(None, ge=1)
    has_basement: Optional[bool] = None
    basement_floors: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None
    description: Optional[str] = None


class BuildingResponse(BaseModel):
    """Building response schema."""
    id: UUID
    name: str
    code: str
    address: Optional[str] = None
    total_floors: int
    has_basement: bool
    basement_floors: int
    is_active: bool
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True