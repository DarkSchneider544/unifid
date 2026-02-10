from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID
import re

from ..models.enums import AssetStatus, AssetType


# ==================== IT Asset Schemas ====================

class ITAssetBase(BaseModel):
    """Base IT asset schema."""
    name: str = Field(..., min_length=1, max_length=200)
    asset_type: AssetType
    description: Optional[str] = Field(None, max_length=1000)
    vendor: Optional[str] = Field(None, max_length=200)
    model: Optional[str] = Field(None, max_length=200)
    serial_number: Optional[str] = Field(None, max_length=100)
    specifications: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    purchase_date: Optional[date] = None
    purchase_price: Optional[Decimal] = Field(None, ge=0)
    warranty_expiry: Optional[date] = None
    location: Optional[str] = Field(None, max_length=200)
    notes: Optional[str] = Field(None, max_length=1000)


class ITAssetCreate(ITAssetBase):
    """
    IT asset creation schema.
    
    asset_code is auto-generated based on asset_type (e.g., LAP-0001, MON-0001)
    Only IT admin can create assets.
    """
    pass


class ITAssetUpdate(BaseModel):
    """IT asset update schema."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
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
    asset_code: str  # Auto-generated: LAP-0001, MON-0001, etc.
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
    warranty_status: Optional[str] = None  # "valid", "expiring", "expired"
    status: AssetStatus
    location: Optional[str] = None
    is_active: bool
    notes: Optional[str] = None
    current_assignment: Optional["ITAssetAssignmentResponse"] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ITAssetListResponse(BaseModel):
    """IT asset list response schema."""
    assets: List[ITAssetResponse]
    total: int
    page: int
    page_size: int


class ITAssetSummary(BaseModel):
    """IT asset summary for quick view."""
    id: UUID
    asset_code: str
    name: str
    asset_type: AssetType
    status: AssetStatus
    assigned_to_code: Optional[str] = None
    assigned_to_name: Optional[str] = None


# ==================== IT Asset Assignment Schemas ====================

class ITAssetAssignmentCreate(BaseModel):
    """
    IT asset assignment creation schema.
    
    Only IT admin can assign assets to users.
    """
    asset_id: UUID
    user_code: str = Field(..., description="User code of the employee to assign the asset to")
    notes: Optional[str] = Field(None, max_length=500)
    
    @field_validator('user_code')
    @classmethod
    def validate_user_code(cls, v):
        if not re.match(r'^[A-Z]{2}\d{4}$', v.upper()):
            raise ValueError('Invalid user code format. Expected format: AA0000')
        return v.upper()


class ITAssetReturnRequest(BaseModel):
    """IT asset return request schema."""
    assignment_id: UUID
    return_condition: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = Field(None, max_length=500)


class ITAssetReturnAcknowledge(BaseModel):
    """IT asset return acknowledgement schema."""
    assignment_id: UUID
    condition_notes: Optional[str] = Field(None, max_length=500)
    

class ITAssetAssignmentResponse(BaseModel):
    """IT asset assignment response schema."""
    id: UUID
    asset_id: UUID
    asset_code: str
    asset_name: str
    asset_type: AssetType
    user_code: str
    user_name: str
    assigned_by_code: str
    assigned_by_name: str
    assigned_at: datetime
    returned_at: Optional[datetime] = None
    returned_to_code: Optional[str] = None
    returned_to_name: Optional[str] = None
    return_condition: Optional[str] = None
    return_acknowledged: bool = False
    acknowledgement_date: Optional[datetime] = None
    is_active: bool
    notes: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class ITAssetAssignmentListResponse(BaseModel):
    """IT asset assignment list response schema."""
    assignments: List[ITAssetAssignmentResponse]
    total: int
    page: int
    page_size: int


class MyAssetsResponse(BaseModel):
    """User's assigned assets response."""
    assets: List[ITAssetAssignmentResponse] = []
    total: int


# ==================== IT Asset Statistics ====================

class ITAssetStatistics(BaseModel):
    """IT asset statistics for dashboard."""
    total_assets: int
    available_assets: int
    assigned_assets: int
    maintenance_assets: int
    retired_assets: int
    expiring_warranty_count: int  # Warranty expiring in 30 days
    by_type: Dict[str, int]  # Asset count by type


# Forward reference resolution
ITAssetResponse.model_rebuild()