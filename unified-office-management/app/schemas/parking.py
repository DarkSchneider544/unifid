from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID

from ..models.enums import ParkingType


class ParkingAllocationBase(BaseModel):
    """Base parking allocation schema."""
    floor_plan_id: UUID
    slot_label: str = Field(..., min_length=1, max_length=50)
    cell_row: str
    cell_column: str
    parking_type: ParkingType = ParkingType.EMPLOYEE
    vehicle_number: Optional[str] = None
    notes: Optional[str] = None


class ParkingAllocationCreate(ParkingAllocationBase):
    """Parking allocation creation schema."""
    user_id: Optional[UUID] = None
    visitor_name: Optional[str] = None
    visitor_phone: Optional[str] = None
    visitor_company: Optional[str] = None


class ParkingAllocationUpdate(BaseModel):
    """Parking allocation update schema."""
    vehicle_number: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class ParkingEntryExit(BaseModel):
    """Parking entry/exit schema."""
    allocation_id: UUID
    action: str = Field(..., pattern="^(entry|exit)$")
    timestamp: Optional[datetime] = None


class ParkingAllocationResponse(BaseModel):
    """Parking allocation response schema."""
    id: UUID
    floor_plan_id: UUID
    slot_label: str
    cell_row: str
    cell_column: str
    parking_type: ParkingType
    user_id: Optional[UUID] = None
    visitor_name: Optional[str] = None
    visitor_phone: Optional[str] = None
    visitor_company: Optional[str] = None
    vehicle_number: Optional[str] = None
    entry_time: Optional[datetime] = None
    exit_time: Optional[datetime] = None
    is_active: bool
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ParkingHistoryResponse(BaseModel):
    """Parking history response schema."""
    id: UUID
    allocation_id: UUID
    floor_plan_id: UUID
    slot_label: str
    parking_type: ParkingType
    user_id: Optional[UUID] = None
    visitor_name: Optional[str] = None
    vehicle_number: Optional[str] = None
    entry_time: datetime
    exit_time: Optional[datetime] = None
    duration_minutes: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True