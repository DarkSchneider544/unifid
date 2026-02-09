from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime, date, time
from uuid import UUID

from ..models.enums import BookingStatus


class CafeteriaBookingBase(BaseModel):
    """Base cafeteria booking schema."""
    floor_plan_id: UUID
    table_label: str = Field(..., min_length=1, max_length=50)
    cell_row: str
    cell_column: str
    booking_date: date
    start_time: time
    end_time: time
    guest_count: str = "1"
    notes: Optional[str] = None
    
    @field_validator('end_time')
    @classmethod
    def validate_time_range(cls, v, info):
        start = info.data.get('start_time')
        if start and v <= start:
            raise ValueError('End time must be after start time')
        return v


class CafeteriaBookingCreate(CafeteriaBookingBase):
    """Cafeteria booking creation schema."""
    pass


class CafeteriaBookingUpdate(BaseModel):
    """Cafeteria booking update schema."""
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    guest_count: Optional[str] = None
    status: Optional[BookingStatus] = None
    notes: Optional[str] = None


class CafeteriaBookingResponse(BaseModel):
    """Cafeteria booking response schema."""
    id: UUID
    floor_plan_id: UUID
    table_label: str
    cell_row: str
    cell_column: str
    user_id: UUID
    booking_date: date
    start_time: time
    end_time: time
    guest_count: str
    status: BookingStatus
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True