from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID

from ....core.database import get_db
from ....core.dependencies import (
    get_current_active_user,
    require_it_support_manager,
    is_manager_of_type
)
from ....models.user import User
from ....models.enums import ITRequestType, ITRequestStatus, UserRole, ManagerType
from ....schemas.it_request import (
    ITRequestCreate, ITRequestUpdate, ITRequestResponse,
    ITRequestApproval, ITRequestStatusUpdate
)
from ....schemas.base import APIResponse, PaginatedResponse
from ....services.it_request_service import ITRequestService
from ....utils.response import create_response, create_paginated_response

router = APIRouter()


# ========== MANAGEMENT APIs - IT Support Manager Only ==========
# These APIs are for MANAGING IT requests (approving, assigning, completing)
# Only IT Support Manager, Admin, or Super Admin can access these

@router.post("/{request_id}/approve", response_model=APIResponse[ITRequestResponse])
async def approve_it_request(
    request_id: UUID,
    approval_data: ITRequestApproval,
    current_user: User = Depends(require_it_support_manager),
    db: AsyncSession = Depends(get_db)
):
    """
    Approve or reject an IT request.
    
    **IT Support Manager only**
    """
    request_service = ITRequestService(db)
    
    if approval_data.action == "approve":
        it_request, error = await request_service.approve_request(
            request_id, current_user, approval_data.notes, approval_data.assigned_to_id
        )
    else:
        if not approval_data.rejection_reason:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rejection reason is required"
            )
        it_request, error = await request_service.reject_request(
            request_id, current_user, approval_data.rejection_reason
        )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return create_response(
        data=ITRequestResponse.model_validate(it_request),
        message=f"IT request {approval_data.action}d successfully"
    )


@router.post("/{request_id}/start", response_model=APIResponse[ITRequestResponse])
async def start_it_request(
    request_id: UUID,
    current_user: User = Depends(require_it_support_manager),
    db: AsyncSession = Depends(get_db)
):
    """
    Start working on an IT request.
    
    **IT Support Manager only**
    """
    request_service = ITRequestService(db)
    it_request, error = await request_service.start_work(request_id, current_user)
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return create_response(
        data=ITRequestResponse.model_validate(it_request),
        message="Work started on IT request"
    )


@router.post("/{request_id}/complete", response_model=APIResponse[ITRequestResponse])
async def complete_it_request(
    request_id: UUID,
    notes: Optional[str] = None,
    current_user: User = Depends(require_it_support_manager),
    db: AsyncSession = Depends(get_db)
):
    """
    Complete an IT request.
    
    **IT Support Manager only**
    """
    request_service = ITRequestService(db)
    it_request, error = await request_service.complete_request(
        request_id, current_user, notes
    )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return create_response(
        data=ITRequestResponse.model_validate(it_request),
        message="IT request completed successfully"
    )


# ========== USER APIs - All Authenticated Users ==========
# These APIs are for USING IT request services (creating, viewing own requests)
# All authenticated users can access these


def build_it_request_response(it_request) -> dict:
    """Build IT request response with user names from relationships."""
    return {
        "id": it_request.id,
        "request_number": it_request.request_number,
        "user_code": it_request.user_code,
        "user_name": f"{it_request.user.first_name} {it_request.user.last_name}" if it_request.user else "",
        "request_type": it_request.request_type,
        "related_asset_id": it_request.asset_id,
        "related_asset_code": it_request.asset.asset_code if it_request.asset else None,
        "title": it_request.title,
        "description": it_request.description,
        "priority": it_request.priority,
        "status": it_request.status,
        "approved_by_code": it_request.approved_by_code,
        "approved_by_name": f"{it_request.approved_by.first_name} {it_request.approved_by.last_name}" if it_request.approved_by else None,
        "approved_at": it_request.approved_at,
        "approval_notes": it_request.approval_notes,
        "assigned_to_code": it_request.assigned_to_code,
        "assigned_to_name": f"{it_request.assigned_to.first_name} {it_request.assigned_to.last_name}" if it_request.assigned_to else None,
        "assigned_at": it_request.assigned_at,
        "started_at": it_request.in_progress_at,
        "completed_at": it_request.completed_at,
        "resolution_notes": it_request.resolution_summary,
        "rejection_reason": it_request.rejection_reason,
        "created_at": it_request.created_at,
        "updated_at": it_request.updated_at,
    }


@router.post("", response_model=APIResponse[ITRequestResponse])
async def create_it_request(
    request_data: ITRequestCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new IT request.
    
    **All authenticated users** can submit IT requests.
    """
    request_service = ITRequestService(db)
    it_request, error = await request_service.create_request(request_data, current_user)
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    # Build response with user name
    response_data = build_it_request_response(it_request)
    
    return create_response(
        data=response_data,
        message="IT request created successfully"
    )


@router.get("", response_model=PaginatedResponse[ITRequestResponse])
async def list_it_requests(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: Optional[UUID] = None,
    request_type: Optional[ITRequestType] = None,
    status: Optional[ITRequestStatus] = None,
    priority: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List IT requests.
    
    - **IT Support Manager** can see all requests
    - **Regular users** can only see their own requests
    """
    # Only IT Support Manager can see all requests
    # Regular users can only see their own requests
    is_it_manager = is_manager_of_type(current_user, [ManagerType.IT_SUPPORT])
    if not is_it_manager:
        user_id = current_user.id
    
    request_service = ITRequestService(db)
    requests, total = await request_service.list_requests(
        user_id=user_id,
        request_type=request_type,
        status=status,
        priority=priority,
        page=page,
        page_size=page_size
    )
    
    return create_paginated_response(
        data=[build_it_request_response(r) for r in requests],
        total=total,
        page=page,
        page_size=page_size,
        message="IT requests retrieved successfully"
    )


@router.get("/{request_id}", response_model=APIResponse[ITRequestResponse])
async def get_it_request(
    request_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get IT request by ID.
    
    **All authenticated users** can view their own requests.
    IT Support Manager can view any request.
    """
    request_service = ITRequestService(db)
    it_request = await request_service.get_request_by_id(request_id)
    
    if not it_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="IT request not found"
        )
    
    # Check if user can view this request
    is_it_manager = is_manager_of_type(current_user, [ManagerType.IT_SUPPORT])
    if not is_it_manager and it_request.requester_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own IT requests"
        )
    
    return create_response(
        data=ITRequestResponse.model_validate(it_request),
        message="IT request retrieved successfully"
    )


@router.put("/{request_id}", response_model=APIResponse[ITRequestResponse])
async def update_it_request(
    request_id: UUID,
    request_data: ITRequestUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update an IT request.
    
    **Users** can update their own pending requests.
    **IT Support Manager** can update any request.
    """
    request_service = ITRequestService(db)
    it_request, error = await request_service.update_request(
        request_id, request_data, current_user
    )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return create_response(
        data=ITRequestResponse.model_validate(it_request),
        message="IT request updated successfully"
    )
