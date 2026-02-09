from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID

from ....core.database import get_db
from ....core.dependencies import require_admin_or_above, get_current_active_user
from ....models.user import User
from ....schemas.building import BuildingCreate, BuildingUpdate, BuildingResponse
from ....schemas.base import APIResponse, PaginatedResponse
from ....services.building_service import BuildingService
from ....utils.response import create_response, create_paginated_response

router = APIRouter()


@router.post("", response_model=APIResponse[BuildingResponse])
async def create_building(
    building_data: BuildingCreate,
    current_user: User = Depends(require_admin_or_above),
    db: AsyncSession = Depends(get_db)
):
    """Create a new building. Admin+ required."""
    building_service = BuildingService(db)
    building, error = await building_service.create_building(building_data)
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return create_response(
        data=BuildingResponse.model_validate(building),
        message="Building created successfully"
    )


@router.get("", response_model=PaginatedResponse[BuildingResponse])
async def list_buildings(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    is_active: Optional[bool] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List all buildings."""
    building_service = BuildingService(db)
    buildings, total = await building_service.list_buildings(
        page=page,
        page_size=page_size,
        is_active=is_active
    )
    
    return create_paginated_response(
        data=[BuildingResponse.model_validate(b) for b in buildings],
        total=total,
        page=page,
        page_size=page_size,
        message="Buildings retrieved successfully"
    )


@router.get("/{building_id}", response_model=APIResponse[BuildingResponse])
async def get_building(
    building_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get building by ID."""
    building_service = BuildingService(db)
    building = await building_service.get_building_by_id(building_id)
    
    if not building:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Building not found"
        )
    
    return create_response(
        data=BuildingResponse.model_validate(building),
        message="Building retrieved successfully"
    )


@router.put("/{building_id}", response_model=APIResponse[BuildingResponse])
async def update_building(
    building_id: UUID,
    building_data: BuildingUpdate,
    current_user: User = Depends(require_admin_or_above),
    db: AsyncSession = Depends(get_db)
):
    """Update building details. Admin+ required."""
    building_service = BuildingService(db)
    building, error = await building_service.update_building(building_id, building_data)
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return create_response(
        data=BuildingResponse.model_validate(building),
        message="Building updated successfully"
    )


@router.delete("/{building_id}", response_model=APIResponse)
async def delete_building(
    building_id: UUID,
    current_user: User = Depends(require_admin_or_above),
    db: AsyncSession = Depends(get_db)
):
    """Deactivate a building. Admin+ required."""
    building_service = BuildingService(db)
    success, error = await building_service.delete_building(building_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return create_response(message="Building deactivated successfully")