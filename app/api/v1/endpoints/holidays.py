from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID

from ....core.database import get_db
from ....core.dependencies import get_current_active_user, require_super_admin
from ....models.user import User
from ....schemas.holiday import (
    HolidayCreate, HolidayUpdate, HolidayResponse
)
from ....schemas.base import APIResponse, PaginatedResponse
from ....services.holiday_service import HolidayService
from ....utils.response import create_response, create_paginated_response

router = APIRouter()


def build_holiday_response(holiday) -> dict:
    """Build holiday response with computed fields."""
    created_by_name = ""
    if holiday.created_by:
        created_by_name = f"{holiday.created_by.first_name} {holiday.created_by.last_name}"
    
    return {
        "id": holiday.id,
        "name": holiday.name,
        "description": holiday.description,
        "date": holiday.date,
        "holiday_type": holiday.holiday_type,
        "is_optional": holiday.is_optional,
        "is_active": holiday.is_active,
        "created_by_code": holiday.created_by_code,
        "created_by_name": created_by_name,
        "created_at": holiday.created_at,
        "updated_at": holiday.updated_at,
    }


@router.get("/list", response_model=PaginatedResponse[HolidayResponse])
async def list_holidays(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    upcoming_only: bool = True,
    year: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all holidays.
    
    **All authenticated users** can view holidays.
    
    - By default, returns only upcoming holidays
    - Set `upcoming_only=false` to see all holidays
    - Filter by `year` to see holidays for a specific year
    """
    holiday_service = HolidayService(db)
    holidays, total = await holiday_service.list_holidays(
        upcoming_only=upcoming_only,
        year=year,
        page=page,
        page_size=page_size
    )
    
    return create_paginated_response(
        data=[build_holiday_response(h) for h in holidays],
        total=total,
        page=page,
        page_size=page_size,
        message="Holidays retrieved successfully"
    )


@router.post("/create", response_model=APIResponse[HolidayResponse])
async def create_holiday(
    holiday_data: HolidayCreate,
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new holiday.
    
    **Super Admin only**
    """
    holiday_service = HolidayService(db)
    holiday, error = await holiday_service.create_holiday(holiday_data, current_user)
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return create_response(
        data=build_holiday_response(holiday),
        message="Holiday created successfully"
    )


@router.get("/{holiday_id}", response_model=APIResponse[HolidayResponse])
async def get_holiday(
    holiday_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get holiday by ID.
    
    **All authenticated users** can view holidays.
    """
    holiday_service = HolidayService(db)
    holiday = await holiday_service.get_holiday_by_id(holiday_id)
    
    if not holiday:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Holiday not found"
        )
    
    return create_response(
        data=build_holiday_response(holiday),
        message="Holiday retrieved successfully"
    )


@router.put("/{holiday_id}", response_model=APIResponse[HolidayResponse])
async def update_holiday(
    holiday_id: UUID,
    holiday_data: HolidayUpdate,
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a holiday.
    
    **Super Admin only**
    """
    holiday_service = HolidayService(db)
    holiday, error = await holiday_service.update_holiday(
        holiday_id, holiday_data, current_user
    )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return create_response(
        data=build_holiday_response(holiday),
        message="Holiday updated successfully"
    )


@router.delete("/{holiday_id}", response_model=APIResponse[dict])
async def delete_holiday(
    holiday_id: UUID,
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a holiday (soft delete).
    
    **Super Admin only**
    """
    holiday_service = HolidayService(db)
    success, error = await holiday_service.delete_holiday(holiday_id, current_user)
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return create_response(
        data={"deleted": True},
        message="Holiday deleted successfully"
    )
