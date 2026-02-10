from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from uuid import UUID

from ....core.database import get_db
from ....core.dependencies import require_admin_or_above, get_current_active_user
from ....models.user import User
from ....models.enums import CellType, FloorPlanType, UserRole, ManagerType
from ....schemas.floor_plan import (
    FloorPlanCreate, FloorPlanUpdate, FloorPlanResponse,
    FloorPlanVersionCreate, FloorPlanVersionResponse, FloorPlanListResponse
)
from ....schemas.base import APIResponse, PaginatedResponse
from ....services.floor_plan_service import FloorPlanService
from ....utils.response import create_response, create_paginated_response

router = APIRouter()


def check_floor_plan_access(user: User, plan_type: FloorPlanType) -> None:
    """Check if user has access to manage a specific floor plan type."""
    # Super Admin has full access
    if user.role == UserRole.SUPER_ADMIN:
        return
    
    # Admin has full access
    if user.role == UserRole.ADMIN:
        return
    
    # For MANAGER role, check manager type matches plan type
    if user.role == UserRole.MANAGER:
        type_mapping = {
            FloorPlanType.DESK_AREA: ManagerType.DESK_CONFERENCE,
            FloorPlanType.CAFETERIA: ManagerType.CAFETERIA,
            FloorPlanType.PARKING: ManagerType.PARKING,
        }
        
        required_type = type_mapping.get(plan_type)
        if user.manager_type != required_type:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Only {required_type.value if required_type else 'appropriate'} manager can manage {plan_type.value} floor plans"
            )
        return
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Manager or Admin access required"
    )


@router.post("", response_model=APIResponse[FloorPlanResponse])
async def create_floor_plan(
    floor_plan_data: FloorPlanCreate,
    current_user: User = Depends(require_admin_or_above),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new floor plan.
    
    - DESK_CONFERENCE manager can create DESK_AREA plans
    - CAFETERIA manager can create CAFETERIA plans
    - PARKING manager can create PARKING plans
    - SUPER_ADMIN can create any type
    """
    # Check access based on plan type
    check_floor_plan_access(current_user, floor_plan_data.plan_type)
    
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


@router.get("", response_model=PaginatedResponse[FloorPlanListResponse])
async def list_floor_plans(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    plan_type: Optional[FloorPlanType] = None,
    is_active: Optional[bool] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List floor plans with filtering.
    
    - Admins see only their type's floor plans
    - Super Admin sees all
    """
    floor_plan_service = FloorPlanService(db)
    
    # Determine which plan types to show based on role
    if current_user.role == UserRole.SUPER_ADMIN:
        # Super admin can see all or filter
        filter_type = plan_type
    elif current_user.role == UserRole.ADMIN:
        # Admins can see all
        filter_type = plan_type
    elif current_user.role == UserRole.MANAGER:
        # Managers can only see their type
        type_mapping = {
            ManagerType.DESK_CONFERENCE: FloorPlanType.DESK_AREA,
            ManagerType.CAFETERIA: FloorPlanType.CAFETERIA,
            ManagerType.PARKING: FloorPlanType.PARKING,
        }
        filter_type = type_mapping.get(current_user.manager_type)
        if plan_type and plan_type != filter_type:
            # Trying to filter to a different type they don't have access to
            return create_paginated_response(
                data=[],
                total=0,
                page=page,
                page_size=page_size,
                message="No floor plans available"
            )
    else:
        # Other users see all for viewing purposes
        filter_type = plan_type
    
    floor_plans, total = await floor_plan_service.list_floor_plans(
        plan_type=filter_type,
        page=page,
        page_size=page_size,
        is_active=is_active
    )
    
    return create_paginated_response(
        data=[FloorPlanListResponse.model_validate(fp) for fp in floor_plans],
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
    """Update floor plan metadata. Requires appropriate admin type."""
    floor_plan_service = FloorPlanService(db)
    
    # Get existing floor plan to check access
    floor_plan = await floor_plan_service.get_floor_plan_by_id(floor_plan_id)
    if not floor_plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Floor plan not found"
        )
    
    # Check access
    check_floor_plan_access(current_user, floor_plan.plan_type)
    
    floor_plan, error = await floor_plan_service.update_floor_plan(
        floor_plan_id, floor_plan_data, current_user
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
    """Create a new version of a floor plan. Requires appropriate admin type."""
    floor_plan_service = FloorPlanService(db)
    
    # Get floor plan to check access
    floor_plan = await floor_plan_service.get_floor_plan_by_id(floor_plan_id)
    if not floor_plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Floor plan not found"
        )
    
    # Check access
    check_floor_plan_access(current_user, floor_plan.plan_type)
    
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


@router.delete("/{floor_plan_id}", response_model=APIResponse)
async def delete_floor_plan(
    floor_plan_id: UUID,
    current_user: User = Depends(require_admin_or_above),
    db: AsyncSession = Depends(get_db)
):
    """Delete (soft) a floor plan. Requires appropriate admin type."""
    floor_plan_service = FloorPlanService(db)
    
    # Get floor plan to check access
    floor_plan = await floor_plan_service.get_floor_plan_by_id(floor_plan_id)
    if not floor_plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Floor plan not found"
        )
    
    # Check access
    check_floor_plan_access(current_user, floor_plan.plan_type)
    
    success, error = await floor_plan_service.delete_floor_plan(floor_plan_id, current_user)
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return create_response(
        data=None,
        message="Floor plan deleted successfully"
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
