from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID

from ..models.enums import AssetStatus, AssetType


class ITAssetBase(BaseModel):
    """Base IT asset schema."""
    asset_id: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=200)
    asset_type: AssetType
    description: Optional[str] = None
    vendor: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    specifications: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    purchase_date: Optional[date] = None
    purchase_price: Optional[Decimal] = None
    warranty_expiry: Optional[date] = None
    location: Optional[str] = None
    notes: Optional[str] = None


class ITAssetCreate(ITAssetBase):
    """IT asset creation schema."""
    pass


class ITAssetUpdate(BaseModel):
    """IT asset update schema."""
    name: Optional[str] = None
    description: Optional[str] = None
    vendor: Optional[str] = None
    model: Optional[str] = None
    specifications: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    warranty_expiry: Optional[date] = None
    status: Optional[AssetStatus] = None
    location: Optional[str] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class ITAssetResponse(BaseModel):
    """IT asset response schema."""
    id: UUID
    asset_id: str
    name: str
    asset_type: AssetType
    description: Optional[str] = None
    vendor: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    specifications: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    purchase_date: Optional[date] = None
    purchase_price: Optional[Decimal] = None
    warranty_expiry: Optional[date] = None
    status: AssetStatus
    location: Optional[str] = None
    is_active: bool
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ITAssetAssignmentCreate(BaseModel):
    """IT asset assignment creation schema."""
    asset_id: UUID
    user_id: UUID
    notes: Optional[str] = None


class ITAssetAssignmentResponse(BaseModel):
    """IT asset assignment response schema."""
    id: UUID
    asset_id: UUID
    user_id: UUID
    assigned_by_id: UUID
    assigned_at: datetime
    returned_at: Optional[datetime] = None
    is_active: bool
    notes: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True