from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from uuid import UUID

from ....core.database import get_db
from ....core.dependencies import get_current_active_user, require_team_lead_or_above, require_manager_or_above
from ....models.user import User
from ....models.enums import ProjectStatus
from ....schemas.project import (
    ProjectCreate, ProjectUpdate, ProjectResponse,
    ProjectMemberCreate, ProjectApproval
)
from ....schemas.base import APIResponse, PaginatedResponse
from ....services.project_service import ProjectService
from ....utils.response import create_response, create_paginated_response

router = APIRouter()


def build_project_response(project) -> dict:
    """Build project response with computed user name fields."""
    requested_by_name = ""
    if project.requested_by:
        requested_by_name = f"{project.requested_by.first_name} {project.requested_by.last_name}"
    
    approved_by_name = None
    if project.approved_by:
        approved_by_name = f"{project.approved_by.first_name} {project.approved_by.last_name}"
    
    return {
        "id": project.id,
        "project_code": project.project_code,
        "title": project.title,
        "description": project.description,
        "requested_by_code": project.requested_by_code,
        "requested_by_name": requested_by_name,
        "duration_days": project.duration_days,
        "justification": project.justification,
        "start_date": project.start_date,
        "end_date": project.end_date,
        "status": project.status,
        "approved_by_code": project.approved_by_code,
        "approved_by_name": approved_by_name,
        "approved_at": project.approved_at,
        "approval_notes": project.approval_notes,
        "rejection_reason": project.rejection_reason,
        "member_count": len(project.members) if project.members else 0,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
    }


@router.post("", response_model=APIResponse[ProjectResponse])
async def create_project(
    project_data: ProjectCreate,
    current_user: User = Depends(require_team_lead_or_above),
    db: AsyncSession = Depends(get_db)
):
    """Create a new project request. Team Lead+ required."""
    project_service = ProjectService(db)
    project, error = await project_service.create_project(project_data, current_user)
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return create_response(
        data=build_project_response(project),
        message="Project created successfully"
    )


@router.get("", response_model=PaginatedResponse[ProjectResponse])
async def list_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    requested_by_id: Optional[UUID] = None,
    status: Optional[ProjectStatus] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List projects."""
    project_service = ProjectService(db)
    projects, total = await project_service.list_projects(
        requested_by_id=requested_by_id,
        status=status,
        page=page,
        page_size=page_size
    )
    
    return create_paginated_response(
        data=[build_project_response(p) for p in projects],
        total=total,
        page=page,
        page_size=page_size,
        message="Projects retrieved successfully"
    )


@router.get("/{project_id}", response_model=APIResponse[ProjectResponse])
async def get_project(
    project_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get project by ID."""
    project_service = ProjectService(db)
    project = await project_service.get_project_by_id(project_id)
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    return create_response(
        data=build_project_response(project),
        message="Project retrieved successfully"
    )


@router.put("/{project_id}", response_model=APIResponse[ProjectResponse])
async def update_project(
    project_id: UUID,
    project_data: ProjectUpdate,
    current_user: User = Depends(require_team_lead_or_above),
    db: AsyncSession = Depends(get_db)
):
    """Update a project. Team Lead+ required."""
    project_service = ProjectService(db)
    project, error = await project_service.update_project(
        project_id, project_data, current_user
    )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    # Reload project with relationships
    project = await project_service.get_project_by_id(project_id)
    
    return create_response(
        data=build_project_response(project),
        message="Project updated successfully"
    )


@router.post("/{project_id}/submit", response_model=APIResponse[ProjectResponse])
async def submit_project(
    project_id: UUID,
    current_user: User = Depends(require_team_lead_or_above),
    db: AsyncSession = Depends(get_db)
):
    """Submit project for approval. Team Lead+ required."""
    project_service = ProjectService(db)
    project, error = await project_service.submit_project(project_id, current_user)
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    # Reload project with relationships
    project = await project_service.get_project_by_id(project_id)
    
    return create_response(
        data=build_project_response(project),
        message="Project submitted for approval"
    )


@router.post("/{project_id}/approve", response_model=APIResponse[ProjectResponse])
async def approve_project(
    project_id: UUID,
    approval_data: ProjectApproval,
    current_user: User = Depends(require_manager_or_above),
    db: AsyncSession = Depends(get_db)
):
    """Approve or reject a project. Manager+ required."""
    project_service = ProjectService(db)
    
    if approval_data.action == "approve":
        project, error = await project_service.approve_project(
            project_id, current_user, approval_data.notes
        )
    else:
        if not approval_data.rejection_reason:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rejection reason is required"
            )
        project, error = await project_service.reject_project(
            project_id, current_user, approval_data.rejection_reason
        )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    # Reload project with relationships
    project = await project_service.get_project_by_id(project_id)
    
    return create_response(
        data=build_project_response(project),
        message=f"Project {approval_data.action}d successfully"
    )


@router.post("/{project_id}/start", response_model=APIResponse[ProjectResponse])
async def start_project(
    project_id: UUID,
    current_user: User = Depends(require_team_lead_or_above),
    db: AsyncSession = Depends(get_db)
):
    """Start an approved project. Team Lead+ required."""
    project_service = ProjectService(db)
    project, error = await project_service.start_project(project_id, current_user)
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    # Reload project with relationships
    project = await project_service.get_project_by_id(project_id)
    
    return create_response(
        data=build_project_response(project),
        message="Project started successfully"
    )


@router.post("/{project_id}/complete", response_model=APIResponse[ProjectResponse])
async def complete_project(
    project_id: UUID,
    current_user: User = Depends(require_team_lead_or_above),
    db: AsyncSession = Depends(get_db)
):
    """Complete a project. Team Lead+ required."""
    project_service = ProjectService(db)
    project, error = await project_service.complete_project(project_id, current_user)
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    # Reload project with relationships
    project = await project_service.get_project_by_id(project_id)
    
    return create_response(
        data=build_project_response(project),
        message="Project completed successfully"
    )


@router.post("/{project_id}/members", response_model=APIResponse[ProjectResponse])
async def add_project_member(
    project_id: UUID,
    member_data: ProjectMemberCreate,
    current_user: User = Depends(require_team_lead_or_above),
    db: AsyncSession = Depends(get_db)
):
    """Add a member to a project. Team Lead+ required."""
    project_service = ProjectService(db)
    member, error = await project_service.add_member(
        project_id, member_data, current_user
    )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    # Reload project with members
    project = await project_service.get_project_by_id(project_id)
    
    return create_response(
        data=build_project_response(project),
        message="Member added to project successfully"
    )