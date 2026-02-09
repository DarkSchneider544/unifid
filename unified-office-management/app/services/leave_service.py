from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from typing import Optional, List, Tuple
from uuid import UUID
from datetime import datetime, date, timezone
from decimal import Decimal

from ..models.leave import LeaveType as LeaveTypeModel, LeaveBalance, LeaveRequest
from ..models.user import User
from ..models.enums import LeaveType, LeaveStatus, UserRole


class LeaveService:
    """Leave management service."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_leave_request_by_id(
        self,
        request_id: UUID
    ) -> Optional[LeaveRequest]:
        """Get leave request by ID."""
        result = await self.db.execute(
            select(LeaveRequest).where(LeaveRequest.id == request_id)
        )
        return result.scalar_one_or_none()
    
    async def get_leave_balance(
        self,
        user_id: UUID,
        leave_type: LeaveType,
        year: int
    ) -> Optional[LeaveBalance]:
        """Get leave balance for a user."""
        result = await self.db.execute(
            select(LeaveBalance)
            .join(LeaveTypeModel)
            .where(
                LeaveBalance.user_id == user_id,
                LeaveTypeModel.code == leave_type,
                LeaveBalance.year == year
            )
        )
        return result.scalar_one_or_none()
    
    async def get_all_balances(
        self,
        user_id: UUID,
        year: int
    ) -> List[LeaveBalance]:
        """Get all leave balances for a user."""
        result = await self.db.execute(
            select(LeaveBalance)
            .where(
                LeaveBalance.user_id == user_id,
                LeaveBalance.year == year
            )
        )
        return list(result.scalars().all())
    
    async def initialize_leave_balance(
        self,
        user_id: UUID,
        year: int
    ) -> List[LeaveBalance]:
        """Initialize leave balances for a user for a year."""
        # Get all leave types
        result = await self.db.execute(
            select(LeaveTypeModel).where(LeaveTypeModel.is_active == True)
        )
        leave_types = result.scalars().all()
        
        balances = []
        for lt in leave_types:
            # Check if balance already exists
            existing = await self.db.execute(
                select(LeaveBalance).where(
                    LeaveBalance.user_id == user_id,
                    LeaveBalance.leave_type_id == lt.id,
                    LeaveBalance.year == year
                )
            )
            if existing.scalar_one_or_none():
                continue
            
            balance = LeaveBalance(
                user_id=user_id,
                leave_type_id=lt.id,
                year=year,
                total_days=Decimal(str(lt.default_days)),
                used_days=Decimal("0"),
                pending_days=Decimal("0")
            )
            self.db.add(balance)
            balances.append(balance)
        
        await self.db.commit()
        return balances
    
    def calculate_days(self, start_date: date, end_date: date) -> Decimal:
        """Calculate number of days between dates (inclusive)."""
        delta = end_date - start_date
        return Decimal(str(delta.days + 1))
    
    async def create_leave_request(
        self,
        user: User,
        leave_type: LeaveType,
        start_date: date,
        end_date: date,
        reason: Optional[str] = None
    ) -> Tuple[Optional[LeaveRequest], Optional[str]]:
        """Create a new leave request."""
        year = start_date.year
        
        # Get leave type
        result = await self.db.execute(
            select(LeaveTypeModel).where(LeaveTypeModel.code == leave_type)
        )
        leave_type_obj = result.scalar_one_or_none()
        if not leave_type_obj:
            return None, "Invalid leave type"
        
        # Calculate total days
        total_days = self.calculate_days(start_date, end_date)
        
        # Check balance (skip for unpaid leave)
        if leave_type != LeaveType.UNPAID:
            balance = await self.get_leave_balance(user.id, leave_type, year)
            if not balance:
                # Initialize balance
                await self.initialize_leave_balance(user.id, year)
                balance = await self.get_leave_balance(user.id, leave_type, year)
            
            if balance:
                available = float(balance.total_days) - float(balance.used_days) - float(balance.pending_days)
                if float(total_days) > available:
                    return None, f"Insufficient leave balance. Available: {available} days"
        
        # Check for overlapping requests
        overlap_result = await self.db.execute(
            select(LeaveRequest).where(
                LeaveRequest.user_id == user.id,
                LeaveRequest.status.in_([
                    LeaveStatus.PENDING, 
                    LeaveStatus.APPROVED_LEVEL1, 
                    LeaveStatus.APPROVED
                ]),
                LeaveRequest.start_date <= end_date,
                LeaveRequest.end_date >= start_date
            )
        )
        if overlap_result.scalar_one_or_none():
            return None, "Overlapping leave request exists"
        
        # Create request
        leave_request = LeaveRequest(
            user_id=user.id,
            leave_type_id=leave_type_obj.id,
            start_date=start_date,
            end_date=end_date,
            total_days=total_days,
            reason=reason,
            status=LeaveStatus.PENDING
        )
        self.db.add(leave_request)
        
        # Update pending days in balance
        if leave_type != LeaveType.UNPAID and balance:
            balance.pending_days = balance.pending_days + total_days
        
        await self.db.commit()
        await self.db.refresh(leave_request)
        
        return leave_request, None
    
    async def approve_level1(
        self,
        approver: User,
        request_id: UUID,
        notes: Optional[str] = None
    ) -> Tuple[Optional[LeaveRequest], Optional[str]]:
        """Team Lead approves leave request (Level 1)."""
        leave_request = await self.get_leave_request_by_id(request_id)
        if not leave_request:
            return None, "Leave request not found"
        
        if leave_request.status != LeaveStatus.PENDING:
            return None, f"Cannot approve request with status {leave_request.status.value}"
        
        # Verify approver is team lead of the employee
        if approver.role == UserRole.TEAM_LEAD:
            result = await self.db.execute(
                select(User).where(User.id == leave_request.user_id)
            )
            employee = result.scalar_one_or_none()
            if not employee or str(employee.team_lead_id) != str(approver.id):
                return None, "Cannot approve leave for non-team members"
        
        leave_request.status = LeaveStatus.APPROVED_LEVEL1
        leave_request.level1_approved_by_id = approver.id
        leave_request.level1_approved_at = datetime.now(timezone.utc)
        leave_request.level1_notes = notes
        
        await self.db.commit()
        await self.db.refresh(leave_request)
        
        return leave_request, None
    
    async def approve_final(
        self,
        approver: User,
        request_id: UUID,
        notes: Optional[str] = None
    ) -> Tuple[Optional[LeaveRequest], Optional[str]]:
        """Manager approves leave request (Final)."""
        leave_request = await self.get_leave_request_by_id(request_id)
        if not leave_request:
            return None, "Leave request not found"
        
        if leave_request.status not in [LeaveStatus.PENDING, LeaveStatus.APPROVED_LEVEL1]:
            return None, f"Cannot approve request with status {leave_request.status.value}"
        
        # Validate approver
        if approver.role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.MANAGER]:
            return None, "Insufficient permissions"
        
        leave_request.status = LeaveStatus.APPROVED
        leave_request.approved_by_id = approver.id
        leave_request.approved_at = datetime.now(timezone.utc)
        leave_request.approval_notes = notes
        
        # Update balance - move from pending to used
        result = await self.db.execute(
            select(LeaveTypeModel).where(LeaveTypeModel.id == leave_request.leave_type_id)
        )
        leave_type = result.scalar_one_or_none()
        
        if leave_type and leave_type.code != LeaveType.UNPAID:
            balance = await self.get_leave_balance(
                leave_request.user_id,
                leave_type.code,
                leave_request.start_date.year
            )
            if balance:
                balance.pending_days = balance.pending_days - leave_request.total_days
                balance.used_days = balance.used_days + leave_request.total_days
        
        await self.db.commit()
        await self.db.refresh(leave_request)
        
        return leave_request, None
    
    async def reject_leave(
        self,
        approver: User,
        request_id: UUID,
        reason: str
    ) -> Tuple[Optional[LeaveRequest], Optional[str]]:
        """Reject leave request."""
        leave_request = await self.get_leave_request_by_id(request_id)
        if not leave_request:
            return None, "Leave request not found"
        
        if leave_request.status not in [LeaveStatus.PENDING, LeaveStatus.APPROVED_LEVEL1]:
            return None, f"Cannot reject request with status {leave_request.status.value}"
        
        leave_request.status = LeaveStatus.REJECTED
        leave_request.approved_by_id = approver.id
        leave_request.approved_at = datetime.now(timezone.utc)
        leave_request.rejection_reason = reason
        
        # Return pending days to balance
        result = await self.db.execute(
            select(LeaveTypeModel).where(LeaveTypeModel.id == leave_request.leave_type_id)
        )
        leave_type = result.scalar_one_or_none()
        
        if leave_type and leave_type.code != LeaveType.UNPAID:
            balance = await self.get_leave_balance(
                leave_request.user_id,
                leave_type.code,
                leave_request.start_date.year
            )
            if balance:
                balance.pending_days = balance.pending_days - leave_request.total_days
        
        await self.db.commit()
        await self.db.refresh(leave_request)
        
        return leave_request, None
    
    async def cancel_leave(
        self,
        user: User,
        request_id: UUID
    ) -> Tuple[Optional[LeaveRequest], Optional[str]]:
        """Cancel leave request by employee."""
        leave_request = await self.get_leave_request_by_id(request_id)
        if not leave_request:
            return None, "Leave request not found"
        
        if str(leave_request.user_id) != str(user.id):
            return None, "Cannot cancel another user's request"
        
        if leave_request.status not in [LeaveStatus.PENDING, LeaveStatus.APPROVED_LEVEL1]:
            return None, "Cannot cancel approved or rejected requests"
        
        leave_request.status = LeaveStatus.CANCELLED
        leave_request.cancelled_at = datetime.now(timezone.utc)
        
        # Return pending days to balance
        result = await self.db.execute(
            select(LeaveTypeModel).where(LeaveTypeModel.id == leave_request.leave_type_id)
        )
        leave_type = result.scalar_one_or_none()
        
        if leave_type and leave_type.code != LeaveType.UNPAID:
            balance = await self.get_leave_balance(
                leave_request.user_id,
                leave_type.code,
                leave_request.start_date.year
            )
            if balance:
                balance.pending_days = balance.pending_days - leave_request.total_days
        
        await self.db.commit()
        await self.db.refresh(leave_request)
        
        return leave_request, None
    
    async def list_leave_requests(
        self,
        user_id: Optional[UUID] = None,
        status: Optional[LeaveStatus] = None,
        leave_type: Optional[LeaveType] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[LeaveRequest], int]:
        """List leave requests with filtering."""
        query = select(LeaveRequest)
        count_query = select(func.count(LeaveRequest.id))
        
        if user_id:
            query = query.where(LeaveRequest.user_id == user_id)
            count_query = count_query.where(LeaveRequest.user_id == user_id)
        
        if status:
            query = query.where(LeaveRequest.status == status)
            count_query = count_query.where(LeaveRequest.status == status)
        
        if leave_type:
            query = query.join(LeaveTypeModel).where(LeaveTypeModel.code == leave_type)
            count_query = count_query.join(LeaveTypeModel).where(LeaveTypeModel.code == leave_type)
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        query = query.offset((page - 1) * page_size).limit(page_size)
        query = query.order_by(LeaveRequest.created_at.desc())
        
        result = await self.db.execute(query)
        requests = result.scalars().all()
        
        return list(requests), total