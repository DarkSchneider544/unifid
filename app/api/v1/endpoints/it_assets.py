from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from uuid import UUID

from ....core.database import get_db
from ....core.dependencies import (
    get_current_active_user,
    require_it_support_manager,
    is_manager_of_type
)
from ....models.user import User
from ....models.enums import AssetStatus, AssetType, UserRole, ManagerType
from ....schemas.it_asset import (
    ITAssetCreate, ITAssetUpdate, ITAssetResponse,
    ITAssetAssignmentCreate, ITAssetAssignmentResponse
)
from ....schemas.base import APIResponse, PaginatedResponse
from ....services.it_asset_service import ITAssetService
from ....utils.response import create_response, create_paginated_response

router = APIRouter()


# ========== MANAGEMENT APIs - IT Support Manager Only ==========
# These APIs are for MANAGING IT assets (creating, updating, assigning)
# Only IT Support Manager, Admin, or Super Admin can access these

@router.post("", response_model=APIResponse[ITAssetResponse])
async def create_it_asset(
    asset_data: ITAssetCreate,
    current_user: User = Depends(require_it_support_manager),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new IT asset.
    
    **IT Support Manager only**
    """
    asset_service = ITAssetService(db)
    asset, error = await asset_service.create_asset(asset_data)
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return create_response(
        data=ITAssetResponse.model_validate(asset),
        message="IT asset created successfully"
    )


@router.put("/{asset_id}", response_model=APIResponse[ITAssetResponse])
async def update_it_asset(
    asset_id: UUID,
    asset_data: ITAssetUpdate,
    current_user: User = Depends(require_it_support_manager),
    db: AsyncSession = Depends(get_db)
):
    """
    Update an IT asset.
    
    **IT Support Manager only**
    """
    asset_service = ITAssetService(db)
    asset, error = await asset_service.update_asset(asset_id, asset_data)
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return create_response(
        data=ITAssetResponse.model_validate(asset),
        message="IT asset updated successfully"
    )


@router.post("/{asset_id}/assign", response_model=APIResponse[ITAssetAssignmentResponse])
async def assign_asset(
    asset_id: UUID,
    user_id: UUID,
    notes: Optional[str] = None,
    current_user: User = Depends(require_it_support_manager),
    db: AsyncSession = Depends(get_db)
):
    """
    Assign an asset to a user.
    
    **IT Support Manager only**
    """
    asset_service = ITAssetService(db)
    assignment, error = await asset_service.assign_asset(
        asset_id, user_id, current_user, notes
    )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return create_response(
        data=ITAssetAssignmentResponse.model_validate(assignment),
        message="Asset assigned successfully"
    )


@router.post("/assignments/{assignment_id}/return", response_model=APIResponse[ITAssetAssignmentResponse])
async def return_asset(
    assignment_id: UUID,
    notes: Optional[str] = None,
    current_user: User = Depends(require_it_support_manager),
    db: AsyncSession = Depends(get_db)
):
    """
    Return an assigned asset.
    
    **IT Support Manager only**
    """
    asset_service = ITAssetService(db)
    assignment, error = await asset_service.return_asset(assignment_id, notes)
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return create_response(
        data=ITAssetAssignmentResponse.model_validate(assignment),
        message="Asset returned successfully"
    )


# ========== USER APIs - All Authenticated Users ==========
# These APIs are for USING IT services (viewing assets, own assignments)
# All authenticated users can access these

@router.get("", response_model=PaginatedResponse[ITAssetResponse])
async def list_it_assets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    asset_type: Optional[AssetType] = None,
    status: Optional[AssetStatus] = None,
    is_active: Optional[bool] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List IT assets.
    
    **All authenticated users** can view available IT assets.
    """
    asset_service = ITAssetService(db)
    assets, total = await asset_service.list_assets(
        asset_type=asset_type,
        status=status,
        is_active=is_active,
        page=page,
        page_size=page_size
    )
    
    return create_paginated_response(
        data=[ITAssetResponse.model_validate(a) for a in assets],
        total=total,
        page=page,
        page_size=page_size,
        message="IT assets retrieved successfully"
    )


@router.get("/my/assignments", response_model=APIResponse[List[ITAssetAssignmentResponse]])
async def get_my_assignments(
    active_only: bool = True,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user's asset assignments.
    
    **All authenticated users** can view their own assigned assets.
    """
    asset_service = ITAssetService(db)
    assignments = await asset_service.get_user_assignments(
        current_user.id, active_only
    )
    
    return create_response(
        data=[ITAssetAssignmentResponse.model_validate(a) for a in assignments],
        message="Your asset assignments retrieved successfully"
    )


@router.get("/{asset_id}", response_model=APIResponse[ITAssetResponse])
async def get_it_asset(
    asset_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get IT asset by ID.
    
    **All authenticated users** can view IT asset details.
    """
    asset_service = ITAssetService(db)
    asset = await asset_service.get_asset_by_id(asset_id)
    
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="IT asset not found"
        )
    
    return create_response(
        data=ITAssetResponse.model_validate(asset),
        message="IT asset retrieved successfully"
    )
