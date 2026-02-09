from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID
from datetime import date

from ....core.database import get_db
from ....core.dependencies import get_current_active_user, require_team_lead_or_above
from ....models.user import User
from ....models.enums import AttendanceStatus
from ....schemas.attendance import (
    AttendanceResponse, AttendanceApproval, AttendanceCheckIn, AttendanceCheckOut
)
from ....schemas.base import APIResponse, PaginatedResponse
from ....services.attendance_service import AttendanceService
from ....utils.response import create_response, create_paginated_response

router = APIRouter()


@router.post("/check-in", response_model=APIResponse[AttendanceResponse])
async def check_in(
    check_in_data: Optional[AttendanceCheckIn] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Record check-in for current user."""
    attendance_service = AttendanceService(db)
    notes = check_in_data.notes if check_in_data else None
    attendance, error = await attendance_service.check_in(current_user, notes)
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return create_response(
        data=AttendanceResponse.model_validate(attendance),
        message="Check-in recorded successfully"
    )


@router.post("/check-out", response_model=APIResponse[AttendanceResponse])
async def check_out(
    check_out_data: AttendanceCheckOut,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Record check-out for current user."""
    attendance_service = AttendanceService(db)
    attendance, error = await attendance_service.check_out(
        current_user,
        check_out_data.entry_id,
        check_out_data.notes
    )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return create_response(
        data=AttendanceResponse.model_validate(attendance),
        message="Check-out recorded successfully"
    )


@router.post("/{attendance_id}/submit", response_model=APIResponse[AttendanceResponse])
async def submit_for_approval(
    attendance_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Submit attendance for manager approval."""
    attendance_service = AttendanceService(db)
    attendance, error = await attendance_service.submit_for_approval(
        current_user, attendance_id
    )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return create_response(
        data=AttendanceResponse.model_validate(attendance),
        message="Attendance submitted for approval"
    )


@router.post("/{attendance_id}/approve", response_model=APIResponse[AttendanceResponse])
async def approve_attendance(
    attendance_id: UUID,
    approval_data: AttendanceApproval,
    current_user: User = Depends(require_team_lead_or_above),
    db: AsyncSession = Depends(get_db)
):
    """Approve or reject attendance. Team Lead+ required."""
    attendance_service = AttendanceService(db)
    
    if approval_data.action == "approve":
        attendance, error = await attendance_service.approve_attendance(
            current_user, attendance_id, approval_data.notes
        )
    else:
        if not approval_data.rejection_reason:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rejection reason is required"
            )
        attendance, error = await attendance_service.reject_attendance(
            current_user, attendance_id, approval_data.rejection_reason
        )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return create_response(
        data=AttendanceResponse.model_validate(attendance),
        message=f"Attendance {approval_data.action}d successfully"
    )


@router.get("", response_model=PaginatedResponse[AttendanceResponse])
async def list_attendances(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: Optional[UUID] = None,
    status: Optional[AttendanceStatus] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List attendance records."""
    from ....models.enums import UserRole
    
    # Non-managers can only see their own attendance
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.MANAGER, UserRole.TEAM_LEAD]:
        user_id = current_user.id
    
    attendance_service = AttendanceService(db)
    attendances, total = await attendance_service.list_attendances(
        user_id=user_id,
        status=status,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size
    )
    
    return create_paginated_response(
        data=[AttendanceResponse.model_validate(a) for a in attendances],
        total=total,
        page=page,
        page_size=page_size,
        message="Attendance records retrieved successfully"
    )


@router.get("/my", response_model=PaginatedResponse[AttendanceResponse])
async def get_my_attendance(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's attendance records."""
    attendance_service = AttendanceService(db)
    attendances, total = await attendance_service.list_attendances(
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size
    )
    
    return create_paginated_response(
        data=[AttendanceResponse.model_validate(a) for a in attendances],
        total=total,
        page=page,
        page_size=page_size,
        message="Your attendance records retrieved successfully"
    )


@router.get("/pending-approvals", response_model=PaginatedResponse[AttendanceResponse])
async def get_pending_approvals(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_team_lead_or_above),
    db: AsyncSession = Depends(get_db)
):
    """Get pending attendance approvals. Team Lead+ required."""
    attendance_service = AttendanceService(db)
    attendances, total = await attendance_service.get_pending_approvals(
        current_user, page=page, page_size=page_size
    )
    
    return create_paginated_response(
        data=[AttendanceResponse.model_validate(a) for a in attendances],
        total=total,
        page=page,
        page_size=page_size,
        message="Pending approvals retrieved successfully"
    )


@router.get("/{attendance_id}", response_model=APIResponse[AttendanceResponse])
async def get_attendance(
    attendance_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get attendance by ID."""
    attendance_service = AttendanceService(db)
    attendance = await attendance_service.get_attendance_by_id(attendance_id)
    
    if not attendance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attendance record not found"
        )
    
    return create_response(
        data=AttendanceResponse.model_validate(attendance),
        message="Attendance record retrieved successfully"
    )