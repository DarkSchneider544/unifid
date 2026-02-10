from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime, date, time
from uuid import UUID

from ..models.enums import BookingStatus, DeskStatus


# ==================== Desk Schemas ====================

class DeskBase(BaseModel):
    """Base desk schema."""
    desk_label: str = Field(..., min_length=1, max_length=50)
    cell_row: int = Field(..., ge=0)
    cell_column: int = Field(..., ge=0)
    has_monitor: bool = False
    has_keyboard: bool = False
    has_docking_station: bool = False


class DeskCreate(DeskBase):
    """Desk creation schema."""
    floor_plan_id: UUID


class DeskUpdate(BaseModel):
    """Desk update schema."""
    desk_label: Optional[str] = Field(None, min_length=1, max_length=50)
    has_monitor: Optional[bool] = None
    has_keyboard: Optional[bool] = None
    has_docking_station: Optional[bool] = None
    is_active: Optional[bool] = None


class DeskResponse(BaseModel):
    """Desk response schema."""
    id: UUID
    floor_plan_id: UUID
    desk_label: str
    cell_row: int
    cell_column: int
    status: DeskStatus
    has_monitor: bool
    has_keyboard: bool
    has_docking_station: bool
    is_active: bool
    current_booking: Optional["DeskBookingResponse"] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class DeskListResponse(BaseModel):
    """Desk list response schema."""
    desks: List[DeskResponse]
    total: int
    available: int
    booked: int


# ==================== Desk Booking Schemas ====================

class DeskBookingBase(BaseModel):
    """
    Base desk booking schema.
    
    Available to: EMPLOYEE, TEAM_LEAD, MANAGER roles
    Managed by: DESK admin
    """
    booking_date: date
    start_time: time
    end_time: time
    notes: Optional[str] = Field(None, max_length=500)
    
    @field_validator('end_time')
    @classmethod
    def validate_time_range(cls, v, info):
        start = info.data.get('start_time')
        if start and v <= start:
            raise ValueError('End time must be after start time')
        return v


class DeskBookingCreate(DeskBookingBase):
    """
    Desk booking creation schema.
    
    Employees can book their own desk.
    """
    desk_id: UUID
    
    @field_validator('booking_date')
    @classmethod
    def validate_booking_date(cls, v):
        if v < date.today():
            raise ValueError('Cannot book for past dates')
        return v


class DeskBookingUpdate(BaseModel):
    """Desk booking update schema."""
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    notes: Optional[str] = None
    
    @field_validator('end_time')
    @classmethod
    def validate_time_range(cls, v, info):
        start = info.data.get('start_time')
        if start and v and v <= start:
            raise ValueError('End time must be after start time')
        return v


class DeskCheckInOut(BaseModel):
    """Desk check-in/check-out schema."""
    booking_id: UUID
    action: str = Field(..., pattern="^(check_in|check_out)$")


class DeskBookingResponse(BaseModel):
    """Desk booking response schema."""
    id: UUID
    desk_id: UUID
    desk_label: str  # From desk
    floor_plan_id: UUID  # From desk
    user_code: str
    user_name: str
    booking_date: date
    start_time: time
    end_time: time
    status: BookingStatus
    check_in_time: Optional[datetime] = None
    check_out_time: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class DeskBookingListResponse(BaseModel):
    """Desk booking list response schema."""
    bookings: List[DeskBookingResponse]
    total: int
    page: int
    page_size: int


class MyDeskBookingResponse(BaseModel):
    """User's desk bookings response."""
    today_booking: Optional[DeskBookingResponse] = None
    upcoming_bookings: List[DeskBookingResponse] = []


# ==================== Conference Room Schemas ====================

class ConferenceRoomBase(BaseModel):
    """Base conference room schema."""
    room_label: str = Field(..., min_length=1, max_length=50)
    cell_row: int = Field(..., ge=0)
    cell_column: int = Field(..., ge=0)
    capacity: int = Field(..., ge=1, le=100)
    has_projector: bool = False
    has_whiteboard: bool = False
    has_video_conferencing: bool = False


class ConferenceRoomCreate(ConferenceRoomBase):
    """Conference room creation schema."""
    floor_plan_id: UUID


class ConferenceRoomUpdate(BaseModel):
    """Conference room update schema."""
    room_label: Optional[str] = Field(None, min_length=1, max_length=50)
    capacity: Optional[int] = Field(None, ge=1, le=100)
    has_projector: Optional[bool] = None
    has_whiteboard: Optional[bool] = None
    has_video_conferencing: Optional[bool] = None
    is_active: Optional[bool] = None


class ConferenceRoomResponse(BaseModel):
    """Conference room response schema."""
    id: UUID
    floor_plan_id: UUID
    room_label: str
    cell_row: int
    cell_column: int
    capacity: int
    has_projector: bool
    has_whiteboard: bool
    has_video_conferencing: bool
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class ConferenceRoomListResponse(BaseModel):
    """Conference room list response schema."""
    rooms: List[ConferenceRoomResponse]
    total: int


# ==================== Conference Room Booking Schemas ====================

class ConferenceRoomBookingBase(BaseModel):
    """Base conference room booking schema."""
    booking_date: date
    start_time: time
    end_time: time
    purpose: str = Field(..., min_length=1, max_length=200)
    attendees_count: int = Field(..., ge=1)
    notes: Optional[str] = Field(None, max_length=500)
    
    @field_validator('end_time')
    @classmethod
    def validate_time_range(cls, v, info):
        start = info.data.get('start_time')
        if start and v <= start:
            raise ValueError('End time must be after start time')
        return v


class ConferenceRoomBookingCreate(ConferenceRoomBookingBase):
    """Conference room booking creation schema."""
    room_id: UUID
    
    @field_validator('booking_date')
    @classmethod
    def validate_booking_date(cls, v):
        if v < date.today():
            raise ValueError('Cannot book for past dates')
        return v


class ConferenceRoomBookingUpdate(BaseModel):
    """Conference room booking update schema."""
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    purpose: Optional[str] = Field(None, min_length=1, max_length=200)
    attendees_count: Optional[int] = Field(None, ge=1)
    notes: Optional[str] = None


class ConferenceRoomBookingResponse(BaseModel):
    """Conference room booking response schema."""
    id: UUID
    room_id: UUID
    room_label: str  # From room
    capacity: int  # From room
    user_code: str
    user_name: str
    booking_date: date
    start_time: time
    end_time: time
    purpose: str
    attendees_count: int
    status: BookingStatus
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ConferenceRoomBookingListResponse(BaseModel):
    """Conference room booking list response schema."""
    bookings: List[ConferenceRoomBookingResponse]
    total: int
    page: int
    page_size: int


# ==================== Desk Statistics ====================

class DeskStatistics(BaseModel):
    """Desk area statistics for dashboard."""
    total_desks: int
    available_desks: int
    booked_desks: int
    maintenance_desks: int
    occupancy_percentage: float
    total_conference_rooms: int
    conference_rooms_in_use: int


# Forward reference resolution
DeskResponse.model_rebuild()