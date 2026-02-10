from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import Optional, List, Tuple
from uuid import UUID
from datetime import datetime, timezone, timedelta

from ..models.project import Project, ProjectMember
from ..models.user import User
from ..models.enums import ProjectStatus, UserRole
from ..schemas.project import ProjectCreate, ProjectUpdate, ProjectMemberCreate


class ProjectService:
    """Project management service."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_user_by_code(self, user_code: str) -> Optional[User]:
        """Get user by user_code."""
        result = await self.db.execute(
            select(User).where(User.user_code == user_code.upper())
        )
        return result.scalar_one_or_none()
    
    async def get_project_by_id(
        self,
        project_id: UUID
    ) -> Optional[Project]:
        """Get project by ID with members and user relationships."""
        result = await self.db.execute(
            select(Project)
            .where(Project.id == project_id)
            .options(
                selectinload(Project.members).selectinload(ProjectMember.user),
                selectinload(Project.requested_by),
                selectinload(Project.approved_by)
            )
        )
        return result.scalar_one_or_none()
    
    def generate_project_code(self) -> str:
        """Generate unique project code: PRJ-YYYYMMDD-XXXX"""
        import random
        import string
        date_str = datetime.now(timezone.utc).strftime('%Y%m%d')
        random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        return f"PRJ-{date_str}-{random_str}"
    
    async def create_project(
        self,
        project_data: ProjectCreate,
        requested_by: User
    ) -> Tuple[Optional[Project], Optional[str]]:
        """Create a new project request."""
        # Validate only Team Leads, Managers and above can create projects
        if requested_by.role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.MANAGER, UserRole.TEAM_LEAD]:
            return None, "Only Team Leads and above can create project requests"
        
        # Calculate end date
        end_date = None
        if project_data.start_date:
            end_date = project_data.start_date + timedelta(days=project_data.duration_days)
        
        project = Project(
            project_code=self.generate_project_code(),
            title=project_data.title,
            description=project_data.description,
            requested_by_code=requested_by.user_code,
            duration_days=project_data.duration_days,
            justification=project_data.justification,
            start_date=project_data.start_date,
            end_date=end_date,
            status=ProjectStatus.DRAFT
        )
        self.db.add(project)
        await self.db.flush()
        
        # Add team members - use user_code
        for member_data in project_data.members:
            # Look up user by user_code
            user = await self.get_user_by_code(member_data.user_code)
            if user:
                member = ProjectMember(
                    project_id=project.id,
                    user_code=user.user_code,
                    role=member_data.role,
                    is_active=True,
                    joined_at=datetime.now(timezone.utc)
                )
                self.db.add(member)
        
        # Add requester as lead if not already in members
        requester_in_members = any(
            m.user_code.upper() == requested_by.user_code.upper() 
            for m in project_data.members
        )
        if not requester_in_members:
            lead_member = ProjectMember(
                project_id=project.id,
                user_code=requested_by.user_code,
                role="lead",
                is_active=True,
                joined_at=datetime.now(timezone.utc)
            )
            self.db.add(lead_member)
        
        await self.db.commit()
        
        # Reload with members
        project = await self.get_project_by_id(project.id)
        return project, None
    
    async def update_project(
        self,
        project_id: UUID,
        project_data: ProjectUpdate,
        user: User
    ) -> Tuple[Optional[Project], Optional[str]]:
        """Update a project."""
        project = await self.get_project_by_id(project_id)
        if not project:
            return None, "Project not found"
        
        if str(project.requested_by_id) != str(user.id):
            if user.role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.MANAGER]:
                return None, "Cannot update another user's project"
        
        if project.status not in [ProjectStatus.DRAFT, ProjectStatus.PENDING]:
            return None, "Can only update draft or pending projects"
        
        update_data = project_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(project, field, value)
        
        # Recalculate end date if duration changed
        if project_data.duration_days and project.start_date:
            project.end_date = project.start_date + timedelta(days=project_data.duration_days)
        
        await self.db.commit()
        await self.db.refresh(project)
        
        return project, None
    
    async def submit_project(
        self,
        project_id: UUID,
        user: User
    ) -> Tuple[Optional[Project], Optional[str]]:
        """Submit project for approval."""
        project = await self.get_project_by_id(project_id)
        if not project:
            return None, "Project not found"
        
        if str(project.requested_by_id) != str(user.id):
            return None, "Only the project creator can submit"
        
        if project.status != ProjectStatus.DRAFT:
            return None, "Only draft projects can be submitted"
        
        project.status = ProjectStatus.PENDING
        
        await self.db.commit()
        await self.db.refresh(project)
        
        return project, None
    
    async def approve_project(
        self,
        project_id: UUID,
        approver: User,
        notes: Optional[str] = None
    ) -> Tuple[Optional[Project], Optional[str]]:
        """Approve a project."""
        project = await self.get_project_by_id(project_id)
        if not project:
            return None, "Project not found"
        
        if project.status != ProjectStatus.PENDING:
            return None, "Only pending projects can be approved"
        
        if approver.role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.MANAGER]:
            return None, "Insufficient permissions"
        
        project.status = ProjectStatus.APPROVED
        project.approved_by_id = approver.id
        project.approved_at = datetime.now(timezone.utc)
        project.approval_notes = notes
        
        await self.db.commit()
        await self.db.refresh(project)
        
        return project, None
    
    async def reject_project(
        self,
        project_id: UUID,
        approver: User,
        reason: str
    ) -> Tuple[Optional[Project], Optional[str]]:
        """Reject a project."""
        project = await self.get_project_by_id(project_id)
        if not project:
            return None, "Project not found"
        
        if project.status != ProjectStatus.PENDING:
            return None, "Only pending projects can be rejected"
        
        project.status = ProjectStatus.REJECTED
        project.approved_by_id = approver.id
        project.approved_at = datetime.now(timezone.utc)
        project.rejection_reason = reason
        
        await self.db.commit()
        await self.db.refresh(project)
        
        return project, None
    
    async def start_project(
        self,
        project_id: UUID,
        user: User
    ) -> Tuple[Optional[Project], Optional[str]]:
        """Start an approved project."""
        project = await self.get_project_by_id(project_id)
        if not project:
            return None, "Project not found"
        
        if project.status != ProjectStatus.APPROVED:
            return None, "Only approved projects can be started"
        
        project.status = ProjectStatus.IN_PROGRESS
        if not project.start_date:
            project.start_date = datetime.now(timezone.utc).date()
            project.end_date = project.start_date + timedelta(days=project.duration_days)
        
        await self.db.commit()
        await self.db.refresh(project)
        
        return project, None
    
    async def complete_project(
        self,
        project_id: UUID,
        user: User
    ) -> Tuple[Optional[Project], Optional[str]]:
        """Complete a project."""
        project = await self.get_project_by_id(project_id)
        if not project:
            return None, "Project not found"
        
        if project.status != ProjectStatus.IN_PROGRESS:
            return None, "Only in-progress projects can be completed"
        
        project.status = ProjectStatus.COMPLETED
        
        await self.db.commit()
        await self.db.refresh(project)
        
        return project, None
    
    async def add_member(
        self,
        project_id: UUID,
        member_data: ProjectMemberCreate,
        user: User
    ) -> Tuple[Optional[ProjectMember], Optional[str]]:
        """Add a member to a project."""
        project = await self.get_project_by_id(project_id)
        if not project:
            return None, "Project not found"
        
        # Check if already a member
        for m in project.members:
            if str(m.user_id) == str(member_data.user_id):
                return None, "User is already a project member"
        
        member = ProjectMember(
            project_id=project_id,
            user_id=member_data.user_id,
            role=member_data.role,
            is_active=True
        )
        self.db.add(member)
        
        await self.db.commit()
        await self.db.refresh(member)
        
        return member, None
    
    async def list_projects(
        self,
        requested_by_id: Optional[UUID] = None,
        requested_by_code: Optional[str] = None,
        status: Optional[ProjectStatus] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Project], int]:
        """List projects with filtering."""
        query = select(Project).options(
            selectinload(Project.members).selectinload(ProjectMember.user),
            selectinload(Project.requested_by),
            selectinload(Project.approved_by)
        )
        count_query = select(func.count(Project.id))
        
        if requested_by_code:
            query = query.where(Project.requested_by_code == requested_by_code.upper())
            count_query = count_query.where(Project.requested_by_code == requested_by_code.upper())
        elif requested_by_id:
            # Look up user_code from user_id for backward compatibility
            user = await self.db.execute(select(User).where(User.id == requested_by_id))
            user = user.scalar_one_or_none()
            if user:
                query = query.where(Project.requested_by_code == user.user_code)
                count_query = count_query.where(Project.requested_by_code == user.user_code)
        
        if status:
            query = query.where(Project.status == status)
            count_query = count_query.where(Project.status == status)
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        query = query.offset((page - 1) * page_size).limit(page_size)
        query = query.order_by(Project.created_at.desc())
        
        result = await self.db.execute(query)
        projects = result.scalars().unique().all()
        
        return list(projects), total