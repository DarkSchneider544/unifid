from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime, date, time
from uuid import UUID

from ..models.enums import BookingStatus


# ==================== Cafeteria Table Schemas ====================

class CafeteriaTableBase(BaseModel):
    """Base cafeteria table schema."""
    table_label: str = Field(..., min_length=1, max_length=50)
    cell_row: int = Field(..., ge=0)
    cell_column: int = Field(..., ge=0)
    capacity: int = Field(..., ge=1, le=20)


class CafeteriaTableCreate(CafeteriaTableBase):
    """Cafeteria table creation schema."""
    floor_plan_id: UUID


class CafeteriaTableUpdate(BaseModel):
    """Cafeteria table update schema."""
    table_label: Optional[str] = Field(None, min_length=1, max_length=50)
    capacity: Optional[int] = Field(None, ge=1, le=20)
    is_active: Optional[bool] = None


class CafeteriaTableResponse(BaseModel):
    """Cafeteria table response schema."""
    id: UUID
    floor_plan_id: UUID
    table_label: str
    cell_row: int
    cell_column: int
    capacity: int
    is_available: bool
    is_active: bool
    current_booking: Optional["CafeteriaBookingResponse"] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class CafeteriaTableListResponse(BaseModel):
    """Cafeteria table list response schema."""
    tables: List[CafeteriaTableResponse]
    total: int
    available: int
    booked: int


# ==================== Cafeteria Booking Schemas ====================

class CafeteriaBookingBase(BaseModel):
    """
    Base cafeteria booking schema.
    
    Available to: EMPLOYEE, TEAM_LEAD, MANAGER roles
    Managed by: CAFETERIA admin
    """
    booking_date: date
    start_time: time
    end_time: time
    guest_count: int = Field(1, ge=1, le=20)
    guest_names: Optional[List[str]] = None
    notes: Optional[str] = Field(None, max_length=500)
    
    @field_validator('end_time')
    @classmethod
    def validate_time_range(cls, v, info):
        start = info.data.get('start_time')
        if start and v <= start:
            raise ValueError('End time must be after start time')
        return v
    
    @field_validator('guest_names')
    @classmethod
    def validate_guest_names(cls, v, info):
        guest_count = info.data.get('guest_count', 1)
        if v and len(v) > guest_count:
            raise ValueError('Guest names cannot exceed guest count')
        return v


class CafeteriaBookingCreate(CafeteriaBookingBase):
    """
    Cafeteria booking creation schema.
    
    Employees can book tables for themselves and guests.
    """
    table_id: UUID
    
    @field_validator('booking_date')
    @classmethod
    def validate_booking_date(cls, v):
        if v < date.today():
            raise ValueError('Cannot book for past dates')
        return v


class CafeteriaBookingUpdate(BaseModel):
    """Cafeteria booking update schema."""
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    guest_count: Optional[int] = Field(None, ge=1, le=20)
    guest_names: Optional[List[str]] = None
    notes: Optional[str] = None
    
    @field_validator('end_time')
    @classmethod
    def validate_time_range(cls, v, info):
        start = info.data.get('start_time')
        if start and v and v <= start:
            raise ValueError('End time must be after start time')
        return v


class CafeteriaBookingResponse(BaseModel):
    """Cafeteria booking response schema."""
    id: UUID
    table_id: UUID
    table_label: str  # From table
    table_capacity: int  # From table
    floor_plan_id: UUID  # From table
    user_code: str
    user_name: str
    booking_date: date
    start_time: time
    end_time: time
    guest_count: int
    guest_names: Optional[List[str]] = None
    status: BookingStatus
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class CafeteriaBookingListResponse(BaseModel):
    """Cafeteria booking list response schema."""
    bookings: List[CafeteriaBookingResponse]
    total: int
    page: int
    page_size: int


class MyCafeteriaBookingResponse(BaseModel):
    """User's cafeteria bookings response."""
    today_booking: Optional[CafeteriaBookingResponse] = None
    upcoming_bookings: List[CafeteriaBookingResponse] = []


# ==================== Cafeteria Statistics ====================

class CafeteriaStatistics(BaseModel):
    """Cafeteria statistics for dashboard."""
    total_tables: int
    available_tables: int
    booked_tables: int
    total_capacity: int
    current_occupancy: int
    occupancy_percentage: float


# Forward reference resolution
CafeteriaTableResponse.model_rebuild()