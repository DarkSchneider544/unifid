from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime, date, time
from uuid import UUID

from ..models.enums import BookingStatus


class DeskBookingBase(BaseModel):
    """Base desk booking schema."""
    floor_plan_id: UUID
    desk_label: str = Field(..., min_length=1, max_length=50)
    cell_row: str
    cell_column: str
    booking_date: date
    start_time: time
    end_time: time
    notes: Optional[str] = None
    
    @field_validator('end_time')
    @classmethod
    def validate_time_range(cls, v, info):
        start = info.data.get('start_time')
        if start and v <= start:
            raise ValueError('End time must be after start time')
        return v


class DeskBookingCreate(DeskBookingBase):
    """Desk booking creation schema."""
    pass


class DeskBookingUpdate(BaseModel):
    """Desk booking update schema."""
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    status: Optional[BookingStatus] = None
    notes: Optional[str] = None


class DeskBookingResponse(BaseModel):
    """Desk booking response schema."""
    id: UUID
    floor_plan_id: UUID
    floor_plan_version: str
    desk_label: str
    cell_row: str
    cell_column: str
    user_id: UUID
    booking_date: date
    start_time: time
    end_time: time
    status: BookingStatus
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True