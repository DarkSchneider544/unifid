from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from uuid import UUID

from ....core.database import get_db
from ....core.dependencies import require_admin_or_above, get_current_active_user
from ....models.user import User
from ....models.enums import CellType
from ....schemas.floor_plan import (
    FloorPlanCreate, FloorPlanUpdate, FloorPlanResponse,
    FloorPlanVersionCreate, FloorPlanVersionResponse
)
from ....schemas.base import APIResponse, PaginatedResponse
from ....services.floor_plan_service import FloorPlanService
from ....utils.response import create_response, create_paginated_response

router = APIRouter()


@router.post("", response_model=APIResponse[FloorPlanResponse])
async def create_floor_plan(
    floor_plan_data: FloorPlanCreate,
    current_user: User = Depends(require_admin_or_above),
    db: AsyncSession = Depends(get_db)
):
    """Create a new floor plan. Admin+ required."""
    floor_plan_service = FloorPlanService(db)
    floor_plan, error = await floor_plan_service.create_floor_plan(
        floor_plan_data, current_user
    )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return create_response(
        data=FloorPlanResponse.model_validate(floor_plan),
        message="Floor plan created successfully"
    )


@router.get("", response_model=PaginatedResponse[FloorPlanResponse])
async def list_floor_plans(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    building_id: Optional[UUID] = None,
    is_active: Optional[bool] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List floor plans with filtering."""
    floor_plan_service = FloorPlanService(db)
    floor_plans, total = await floor_plan_service.list_floor_plans(
        building_id=building_id,
        page=page,
        page_size=page_size,
        is_active=is_active
    )
    
    return create_paginated_response(
        data=[FloorPlanResponse.model_validate(fp) for fp in floor_plans],
        total=total,
        page=page,
        page_size=page_size,
        message="Floor plans retrieved successfully"
    )


@router.get("/{floor_plan_id}", response_model=APIResponse[FloorPlanResponse])
async def get_floor_plan(
    floor_plan_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get floor plan by ID with latest grid."""
    floor_plan_service = FloorPlanService(db)
    floor_plan = await floor_plan_service.get_floor_plan_by_id(floor_plan_id)
    
    if not floor_plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Floor plan not found"
        )
    
    # Get latest version
    latest_version = await floor_plan_service.get_latest_version(floor_plan_id)
    
    response = FloorPlanResponse.model_validate(floor_plan)
    if latest_version:
        response.latest_grid = latest_version.grid_data
    
    return create_response(
        data=response,
        message="Floor plan retrieved successfully"
    )


@router.put("/{floor_plan_id}", response_model=APIResponse[FloorPlanResponse])
async def update_floor_plan(
    floor_plan_id: UUID,
    floor_plan_data: FloorPlanUpdate,
    current_user: User = Depends(require_admin_or_above),
    db: AsyncSession = Depends(get_db)
):
    """Update floor plan metadata. Admin+ required."""
    floor_plan_service = FloorPlanService(db)
    floor_plan, error = await floor_plan_service.update_floor_plan(
        floor_plan_id, floor_plan_data
    )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return create_response(
        data=FloorPlanResponse.model_validate(floor_plan),
        message="Floor plan updated successfully"
    )


@router.post("/{floor_plan_id}/versions", response_model=APIResponse[FloorPlanVersionResponse])
async def create_floor_plan_version(
    floor_plan_id: UUID,
    version_data: FloorPlanVersionCreate,
    current_user: User = Depends(require_admin_or_above),
    db: AsyncSession = Depends(get_db)
):
    """Create a new version of a floor plan. Admin+ required."""
    floor_plan_service = FloorPlanService(db)
    version, error = await floor_plan_service.create_version(
        floor_plan_id, version_data, current_user
    )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return create_response(
        data=FloorPlanVersionResponse.model_validate(version),
        message="Floor plan version created successfully"
    )


@router.get("/{floor_plan_id}/versions", response_model=APIResponse[List[FloorPlanVersionResponse]])
async def list_floor_plan_versions(
    floor_plan_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List all versions of a floor plan."""
    floor_plan_service = FloorPlanService(db)
    versions = await floor_plan_service.list_versions(floor_plan_id)
    
    return create_response(
        data=[FloorPlanVersionResponse.model_validate(v) for v in versions],
        message="Floor plan versions retrieved successfully"
    )


@router.get("/{floor_plan_id}/versions/{version}", response_model=APIResponse[FloorPlanVersionResponse])
async def get_floor_plan_version(
    floor_plan_id: UUID,
    version: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific version of a floor plan."""
    floor_plan_service = FloorPlanService(db)
    floor_version = await floor_plan_service.get_version(floor_plan_id, version)
    
    if not floor_version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Floor plan version not found"
        )
    
    return create_response(
        data=FloorPlanVersionResponse.model_validate(floor_version),
        message="Floor plan version retrieved successfully"
    )


@router.post("/{floor_plan_id}/clone", response_model=APIResponse[FloorPlanResponse])
async def clone_floor_plan(
    floor_plan_id: UUID,
    target_building_id: UUID,
    target_floor_number: int,
    new_name: str,
    current_user: User = Depends(require_admin_or_above),
    db: AsyncSession = Depends(get_db)
):
    """Clone a floor plan to another location. Admin+ required."""
    floor_plan_service = FloorPlanService(db)
    clone, error = await floor_plan_service.clone_floor_plan(
        floor_plan_id,
        target_building_id,
        target_floor_number,
        new_name,
        current_user
    )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return create_response(
        data=FloorPlanResponse.model_validate(clone),
        message="Floor plan cloned successfully"
    )


@router.get("/{floor_plan_id}/cells/{cell_type}", response_model=APIResponse[List[dict]])
async def get_cells_by_type(
    floor_plan_id: UUID,
    cell_type: CellType,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all cells of a specific type from latest version."""
    floor_plan_service = FloorPlanService(db)
    cells = await floor_plan_service.get_cells_by_type(floor_plan_id, cell_type)
    
    return create_response(
        data=cells,
        message=f"{cell_type.value} cells retrieved successfully"
    )