from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from uuid import UUID
from datetime import date

from ....core.database import get_db
from ....core.dependencies import get_current_active_user
from ....models.user import User
from ....models.enums import BookingStatus
from ....schemas.cafeteria import (
    CafeteriaBookingCreate, CafeteriaBookingUpdate, CafeteriaBookingResponse
)
from ....schemas.base import APIResponse, PaginatedResponse
from ....services.cafeteria_service import CafeteriaService
from ....utils.response import create_response, create_paginated_response

router = APIRouter()


@router.post("/bookings", response_model=APIResponse[CafeteriaBookingResponse])
async def create_table_booking(
    booking_data: CafeteriaBookingCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new cafeteria table booking."""
    cafeteria_service = CafeteriaService(db)
    booking, error = await cafeteria_service.create_booking(booking_data, current_user)
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return create_response(
        data=CafeteriaBookingResponse.model_validate(booking),
        message="Table booking created successfully"
    )


@router.get("/bookings", response_model=PaginatedResponse[CafeteriaBookingResponse])
async def list_table_bookings(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    floor_plan_id: Optional[UUID] = None,
    user_id: Optional[UUID] = None,
    booking_date: Optional[date] = None,
    status: Optional[BookingStatus] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List cafeteria table bookings."""
    cafeteria_service = CafeteriaService(db)
    bookings, total = await cafeteria_service.list_bookings(
        floor_plan_id=floor_plan_id,
        user_id=user_id,
        booking_date=booking_date,
        status=status,
        page=page,
        page_size=page_size
    )
    
    return create_paginated_response(
        data=[CafeteriaBookingResponse.model_validate(b) for b in bookings],
        total=total,
        page=page,
        page_size=page_size,
        message="Table bookings retrieved successfully"
    )


@router.get("/bookings/{booking_id}", response_model=APIResponse[CafeteriaBookingResponse])
async def get_table_booking(
    booking_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get table booking by ID."""
    cafeteria_service = CafeteriaService(db)
    booking = await cafeteria_service.get_booking_by_id(booking_id)
    
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table booking not found"
        )
    
    return create_response(
        data=CafeteriaBookingResponse.model_validate(booking),
        message="Table booking retrieved successfully"
    )


@router.put("/bookings/{booking_id}", response_model=APIResponse[CafeteriaBookingResponse])
async def update_table_booking(
    booking_id: UUID,
    booking_data: CafeteriaBookingUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a table booking."""
    cafeteria_service = CafeteriaService(db)
    booking, error = await cafeteria_service.update_booking(
        booking_id, booking_data, current_user
    )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return create_response(
        data=CafeteriaBookingResponse.model_validate(booking),
        message="Table booking updated successfully"
    )


@router.delete("/bookings/{booking_id}", response_model=APIResponse)
async def cancel_table_booking(
    booking_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Cancel a table booking."""
    cafeteria_service = CafeteriaService(db)
    success, error = await cafeteria_service.cancel_booking(booking_id, current_user)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return create_response(message="Table booking cancelled successfully")