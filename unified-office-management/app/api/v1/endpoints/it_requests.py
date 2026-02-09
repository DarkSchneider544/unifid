from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID

from ....core.database import get_db
from ....core.dependencies import get_current_active_user, require_manager_or_above
from ....models.user import User
from ....models.enums import ITRequestType, ITRequestStatus
from ....schemas.it_request import (
    ITRequestCreate, ITRequestUpdate, ITRequestResponse,
    ITRequestApproval, ITRequestStatusUpdate
)
from ....schemas.base import APIResponse, PaginatedResponse
from ....services.it_request_service import ITRequestService
from ....utils.response import create_response, create_paginated_response

router = APIRouter()


@router.post("", response_model=APIResponse[ITRequestResponse])
async def create_it_request(
    request_data: ITRequestCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new IT request."""
    request_service = ITRequestService(db)
    it_request, error = await request_service.create_request(request_data, current_user)
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return create_response(
        data=ITRequestResponse.model_validate(it_request),
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
    """List IT requests."""
    from ....models.enums import UserRole
    
    # Non-IT managers can only see their own requests
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.MANAGER]:
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
        data=[ITRequestResponse.model_validate(r) for r in requests],
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
    """Get IT request by ID."""
    request_service = ITRequestService(db)
    it_request = await request_service.get_request_by_id(request_id)
    
    if not it_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="IT request not found"
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
    """Update an IT request."""
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


@router.post("/{request_id}/approve", response_model=APIResponse[ITRequestResponse])
async def approve_it_request(
    request_id: UUID,
    approval_data: ITRequestApproval,
    current_user: User = Depends(require_manager_or_above),
    db: AsyncSession = Depends(get_db)
):
    """Approve or reject an IT request. Manager+ required."""
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
    current_user: User = Depends(require_manager_or_above),
    db: AsyncSession = Depends(get_db)
):
    """Start working on an IT request. Manager+ required."""
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
    current_user: User = Depends(require_manager_or_above),
    db: AsyncSession = Depends(get_db)
):
    """Complete an IT request. Manager+ required."""
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