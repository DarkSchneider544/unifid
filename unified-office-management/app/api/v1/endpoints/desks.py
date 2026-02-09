from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from uuid import UUID
from datetime import date, time

from ....core.database import get_db
from ....core.dependencies import get_current_active_user
from ....models.user import User
from ....models.enums import BookingStatus
from ....schemas.desk import DeskBookingCreate, DeskBookingUpdate, DeskBookingResponse
from ....schemas.base import APIResponse, PaginatedResponse
from ....services.desk_service import DeskService
from ....utils.response import create_response, create_paginated_response

router = APIRouter()


@router.post("/bookings", response_model=APIResponse[DeskBookingResponse])
async def create_desk_booking(
    booking_data: DeskBookingCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new desk booking."""
    desk_service = DeskService(db)
    booking, error = await desk_service.create_booking(booking_data, current_user)
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return create_response(
        data=DeskBookingResponse.model_validate(booking),
        message="Desk booking created successfully"
    )


@router.get("/bookings", response_model=PaginatedResponse[DeskBookingResponse])
async def list_desk_bookings(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    floor_plan_id: Optional[UUID] = None,
    user_id: Optional[UUID] = None,
    booking_date: Optional[date] = None,
    status: Optional[BookingStatus] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List desk bookings with filtering."""
    desk_service = DeskService(db)
    bookings, total = await desk_service.list_bookings(
        floor_plan_id=floor_plan_id,
        user_id=user_id,
        booking_date=booking_date,
        status=status,
        page=page,
        page_size=page_size
    )
    
    return create_paginated_response(
        data=[DeskBookingResponse.model_validate(b) for b in bookings],
        total=total,
        page=page,
        page_size=page_size,
        message="Desk bookings retrieved successfully"
    )


@router.get("/bookings/{booking_id}", response_model=APIResponse[DeskBookingResponse])
async def get_desk_booking(
    booking_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get desk booking by ID."""
    desk_service = DeskService(db)
    booking = await desk_service.get_booking_by_id(booking_id)
    
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Desk booking not found"
        )
    
    return create_response(
        data=DeskBookingResponse.model_validate(booking),
        message="Desk booking retrieved successfully"
    )


@router.put("/bookings/{booking_id}", response_model=APIResponse[DeskBookingResponse])
async def update_desk_booking(
    booking_id: UUID,
    booking_data: DeskBookingUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a desk booking."""
    desk_service = DeskService(db)
    booking, error = await desk_service.update_booking(
        booking_id, booking_data, current_user
    )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return create_response(
        data=DeskBookingResponse.model_validate(booking),
        message="Desk booking updated successfully"
    )


@router.delete("/bookings/{booking_id}", response_model=APIResponse)
async def cancel_desk_booking(
    booking_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Cancel a desk booking."""
    desk_service = DeskService(db)
    success, error = await desk_service.cancel_booking(booking_id, current_user)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return create_response(message="Desk booking cancelled successfully")


@router.get("/available/{floor_plan_id}", response_model=APIResponse[List[dict]])
async def get_available_desks(
    floor_plan_id: UUID,
    booking_date: date,
    start_time: time,
    end_time: time,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all available desks for a time slot."""
    desk_service = DeskService(db)
    desks = await desk_service.get_available_desks(
        floor_plan_id, booking_date, start_time, end_time
    )
    
    return create_response(
        data=desks,
        message="Available desks retrieved successfully"
    )