from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date
from uuid import UUID


# ==================== Holiday Schemas ====================

class HolidayBase(BaseModel):
    """Base holiday schema."""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    date: date
    holiday_type: str = Field(default="company", max_length=50)
    is_optional: bool = False


class HolidayCreate(HolidayBase):
    """
    Holiday creation schema.
    
    Only Super Admin can create holidays.
    """
    pass


class HolidayUpdate(BaseModel):
    """Holiday update schema."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    date: Optional[date] = None
    holiday_type: Optional[str] = Field(None, max_length=50)
    is_optional: Optional[bool] = None
    is_active: Optional[bool] = None


class HolidayResponse(BaseModel):
    """Holiday response schema."""
    id: UUID
    name: str
    description: Optional[str] = None
    date: date
    holiday_type: str
    is_optional: bool
    is_active: bool
    created_by_code: str
    created_by_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class HolidayListResponse(BaseModel):
    """Holiday list response schema."""
    holidays: List[HolidayResponse]
    total: int
