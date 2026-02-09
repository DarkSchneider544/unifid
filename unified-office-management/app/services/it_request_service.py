from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List, Tuple
from uuid import UUID
from datetime import datetime, timezone
import uuid as uuid_lib

from ..models.it_request import ITRequest
from ..models.user import User
from ..models.enums import ITRequestType, ITRequestStatus, UserRole
from ..schemas.it_request import ITRequestCreate, ITRequestUpdate


class ITRequestService:
    """IT Request management service."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_request_by_id(
        self,
        request_id: UUID
    ) -> Optional[ITRequest]:
        """Get IT request by ID."""
        result = await self.db.execute(
            select(ITRequest).where(ITRequest.id == request_id)
        )
        return result.scalar_one_or_none()
    
    def generate_request_number(self) -> str:
        """Generate unique request number."""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_part = str(uuid_lib.uuid4())[:6].upper()
        return f"ITR-{timestamp}-{random_part}"
    
    async def create_request(
        self,
        request_data: ITRequestCreate,
        user: User
    ) -> Tuple[Optional[ITRequest], Optional[str]]:
        """Create a new IT request."""
        it_request = ITRequest(
            request_number=self.generate_request_number(),
            user_id=user.id,
            request_type=request_data.request_type,
            asset_id=request_data.asset_id,
            title=request_data.title,
            description=request_data.description,
            priority=request_data.priority,
            status=ITRequestStatus.PENDING
        )
        
        self.db.add(it_request)
        await self.db.commit()
        await self.db.refresh(it_request)
        
        return it_request, None
    
    async def update_request(
        self,
        request_id: UUID,
        request_data: ITRequestUpdate,
        user: User
    ) -> Tuple[Optional[ITRequest], Optional[str]]:
        """Update an IT request."""
        it_request = await self.get_request_by_id(request_id)
        if not it_request:
            return None, "Request not found"
        
        if str(it_request.user_id) != str(user.id):
            if user.role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.MANAGER]:
                return None, "Cannot update another user's request"
        
        if it_request.status != ITRequestStatus.PENDING:
            return None, "Can only update pending requests"
        
        update_data = request_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(it_request, field, value)
        
        await self.db.commit()
        await self.db.refresh(it_request)
        
        return it_request, None
    
    async def approve_request(
        self,
        request_id: UUID,
        approver: User,
        notes: Optional[str] = None,
        assigned_to_id: Optional[UUID] = None
    ) -> Tuple[Optional[ITRequest], Optional[str]]:
        """Approve an IT request."""
        it_request = await self.get_request_by_id(request_id)
        if not it_request:
            return None, "Request not found"
        
        if it_request.status != ITRequestStatus.PENDING:
            return None, f"Cannot approve request with status {it_request.status.value}"
        
        it_request.status = ITRequestStatus.APPROVED
        it_request.approved_by_id = approver.id
        it_request.approved_at = datetime.now(timezone.utc)
        it_request.approval_notes = notes
        
        if assigned_to_id:
            it_request.assigned_to_id = assigned_to_id
            it_request.assigned_at = datetime.now(timezone.utc)
        
        await self.db.commit()
        await self.db.refresh(it_request)
        
        return it_request, None
    
    async def reject_request(
        self,
        request_id: UUID,
        approver: User,
        reason: str
    ) -> Tuple[Optional[ITRequest], Optional[str]]:
        """Reject an IT request."""
        it_request = await self.get_request_by_id(request_id)
        if not it_request:
            return None, "Request not found"
        
        if it_request.status != ITRequestStatus.PENDING:
            return None, f"Cannot reject request with status {it_request.status.value}"
        
        it_request.status = ITRequestStatus.REJECTED
        it_request.approved_by_id = approver.id
        it_request.approved_at = datetime.now(timezone.utc)
        it_request.rejection_reason = reason
        
        await self.db.commit()
        await self.db.refresh(it_request)
        
        return it_request, None
    
    async def start_work(
        self,
        request_id: UUID,
        technician: User
    ) -> Tuple[Optional[ITRequest], Optional[str]]:
        """Mark request as in progress."""
        it_request = await self.get_request_by_id(request_id)
        if not it_request:
            return None, "Request not found"
        
        if it_request.status != ITRequestStatus.APPROVED:
            return None, "Request must be approved before starting work"
        
        it_request.status = ITRequestStatus.IN_PROGRESS
        if not it_request.assigned_to_id:
            it_request.assigned_to_id = technician.id
            it_request.assigned_at = datetime.now(timezone.utc)
        
        await self.db.commit()
        await self.db.refresh(it_request)
        
        return it_request, None
    
    async def complete_request(
        self,
        request_id: UUID,
        technician: User,
        notes: Optional[str] = None
    ) -> Tuple[Optional[ITRequest], Optional[str]]:
        """Mark request as completed."""
        it_request = await self.get_request_by_id(request_id)
        if not it_request:
            return None, "Request not found"
        
        if it_request.status != ITRequestStatus.IN_PROGRESS:
            return None, "Request must be in progress to complete"
        
        it_request.status = ITRequestStatus.COMPLETED
        it_request.completed_at = datetime.now(timezone.utc)
        it_request.completion_notes = notes
        
        await self.db.commit()
        await self.db.refresh(it_request)
        
        return it_request, None
    
    async def list_requests(
        self,
        user_id: Optional[UUID] = None,
        request_type: Optional[ITRequestType] = None,
        status: Optional[ITRequestStatus] = None,
        priority: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[ITRequest], int]:
        """List IT requests with filtering."""
        query = select(ITRequest)
        count_query = select(func.count(ITRequest.id))
        
        if user_id:
            query = query.where(ITRequest.user_id == user_id)
            count_query = count_query.where(ITRequest.user_id == user_id)
        
        if request_type:
            query = query.where(ITRequest.request_type == request_type)
            count_query = count_query.where(ITRequest.request_type == request_type)
        
        if status:
            query = query.where(ITRequest.status == status)
            count_query = count_query.where(ITRequest.status == status)
        
        if priority:
            query = query.where(ITRequest.priority == priority)
            count_query = count_query.where(ITRequest.priority == priority)
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        query = query.offset((page - 1) * page_size).limit(page_size)
        query = query.order_by(ITRequest.created_at.desc())
        
        result = await self.db.execute(query)
        requests = result.scalars().all()
        
        return list(requests), total