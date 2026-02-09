from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from uuid import UUID
from datetime import datetime

from ....core.database import get_db
from ....core.dependencies import get_current_active_user, require_manager_or_above
from ....models.user import User
from ....models.enums import ParkingType
from ....schemas.parking import (
    ParkingAllocationCreate, ParkingAllocationUpdate,
    ParkingAllocationResponse, ParkingHistoryResponse
)
from ....schemas.base import APIResponse, PaginatedResponse
from ....services.parking_service import ParkingService
from ....utils.response import create_response, create_paginated_response

router = APIRouter()


@router.post("/allocations", response_model=APIResponse[ParkingAllocationResponse])
async def create_parking_allocation(
    allocation_data: ParkingAllocationCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new parking allocation."""
    parking_service = ParkingService(db)
    allocation, error = await parking_service.create_allocation(
        allocation_data, current_user
    )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return create_response(
        data=ParkingAllocationResponse.model_validate(allocation),
        message="Parking allocation created successfully"
    )


@router.get("/allocations", response_model=PaginatedResponse[ParkingAllocationResponse])
async def list_parking_allocations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    floor_plan_id: Optional[UUID] = None,
    parking_type: Optional[ParkingType] = None,
    is_active: Optional[bool] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List parking allocations with filtering."""
    parking_service = ParkingService(db)
    allocations, total = await parking_service.list_allocations(
        floor_plan_id=floor_plan_id,
        parking_type=parking_type,
        is_active=is_active,
        page=page,
        page_size=page_size
    )
    
    return create_paginated_response(
        data=[ParkingAllocationResponse.model_validate(a) for a in allocations],
        total=total,
        page=page,
        page_size=page_size,
        message="Parking allocations retrieved successfully"
    )


@router.get("/allocations/{allocation_id}", response_model=APIResponse[ParkingAllocationResponse])
async def get_parking_allocation(
    allocation_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get parking allocation by ID."""
    parking_service = ParkingService(db)
    allocation = await parking_service.get_allocation_by_id(allocation_id)
    
    if not allocation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parking allocation not found"
        )
    
    return create_response(
        data=ParkingAllocationResponse.model_validate(allocation),
        message="Parking allocation retrieved successfully"
    )


@router.post("/allocations/{allocation_id}/entry", response_model=APIResponse[ParkingAllocationResponse])
async def record_parking_entry(
    allocation_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Record parking entry time."""
    parking_service = ParkingService(db)
    allocation, error = await parking_service.record_entry(allocation_id)
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return create_response(
        data=ParkingAllocationResponse.model_validate(allocation),
        message="Parking entry recorded successfully"
    )


@router.post("/allocations/{allocation_id}/exit", response_model=APIResponse[ParkingAllocationResponse])
async def record_parking_exit(
    allocation_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Record parking exit time."""
    parking_service = ParkingService(db)
    allocation, error = await parking_service.record_exit(allocation_id)
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return create_response(
        data=ParkingAllocationResponse.model_validate(allocation),
        message="Parking exit recorded successfully"
    )


@router.get("/history", response_model=PaginatedResponse[ParkingHistoryResponse])
async def get_parking_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: Optional[UUID] = None,
    floor_plan_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get parking history with filtering."""
    parking_service = ParkingService(db)
    history, total = await parking_service.get_parking_history(
        user_id=user_id,
        floor_plan_id=floor_plan_id,
        page=page,
        page_size=page_size
    )
    
    return create_paginated_response(
        data=[ParkingHistoryResponse.model_validate(h) for h in history],
        total=total,
        page=page,
        page_size=page_size,
        message="Parking history retrieved successfully"
    )


@router.get("/available/{floor_plan_id}", response_model=APIResponse[List[dict]])
async def get_available_slots(
    floor_plan_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all available parking slots on a floor."""
    parking_service = ParkingService(db)
    slots = await parking_service.get_available_slots(floor_plan_id)
    
    return create_response(
        data=slots,
        message="Available parking slots retrieved successfully"
    )