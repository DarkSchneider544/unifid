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
    """
    Leave management service with two-level hierarchical approval.
    
    Approval Hierarchy:
    - EMPLOYEE: Level 1 by TEAM_LEAD, then Level 2 by MANAGER
    - TEAM_LEAD: Approved directly by MANAGER
    - MANAGER: Approved by SUPER_ADMIN
    
    All leave uses user_code as the primary identifier.
    """
    
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
    
    async def get_user_by_code(
        self,
        user_code: str
    ) -> Optional[User]:
        """Get user by user_code."""
        result = await self.db.execute(
            select(User).where(
                User.user_code == user_code.upper(),
                User.is_deleted == False
            )
        )
        return result.scalar_one_or_none()
    
    async def get_leave_balance(
        self,
        user_code: str,
        leave_type: LeaveType,
        year: int
    ) -> Optional[LeaveBalance]:
        """Get leave balance for a user by user_code."""
        result = await self.db.execute(
            select(LeaveBalance)
            .join(LeaveTypeModel)
            .where(
                LeaveBalance.user_code == user_code.upper(),
                LeaveTypeModel.code == leave_type,
                LeaveBalance.year == year
            )
        )
        return result.scalar_one_or_none()
    
    async def get_all_balances(
        self,
        user_code: str,
        year: int
    ) -> List[LeaveBalance]:
        """Get all leave balances for a user."""
        result = await self.db.execute(
            select(LeaveBalance)
            .where(
                LeaveBalance.user_code == user_code.upper(),
                LeaveBalance.year == year
            )
        )
        return list(result.scalars().all())
    
    async def initialize_leave_balance(
        self,
        user_code: str,
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
                    LeaveBalance.user_code == user_code.upper(),
                    LeaveBalance.leave_type_id == lt.id,
                    LeaveBalance.year == year
                )
            )
            if existing.scalar_one_or_none():
                continue
            
            balance = LeaveBalance(
                user_code=user_code.upper(),
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
    
    def calculate_days(
        self,
        start_date: date,
        end_date: date,
        is_half_day: bool = False
    ) -> Decimal:
        """Calculate number of days between dates (inclusive)."""
        if is_half_day:
            return Decimal("0.5")
        delta = end_date - start_date
        return Decimal(str(delta.days + 1))
    
    async def create_leave_request(
        self,
        user: User,
        leave_type: LeaveType,
        start_date: date,
        end_date: date,
        reason: Optional[str] = None,
        is_half_day: bool = False,
        half_day_type: Optional[str] = None,  # "first_half" or "second_half"
        emergency_contact: Optional[str] = None,
        emergency_phone: Optional[str] = None
    ) -> Tuple[Optional[LeaveRequest], Optional[str]]:
        """
        Create a new leave request with hierarchical approval setup.
        
        Determines approvers based on employee role:
        - EMPLOYEE: level1 = team_lead_code, final = manager_code
        - TEAM_LEAD: level1 = None, final = manager_code
        - MANAGER: level1 = None, final = super_admin
        """
        year = start_date.year
        
        # Validate half day
        if is_half_day and start_date != end_date:
            return None, "Half day leave must be for a single day"
        
        # Get leave type
        result = await self.db.execute(
            select(LeaveTypeModel).where(LeaveTypeModel.code == leave_type)
        )
        leave_type_obj = result.scalar_one_or_none()
        if not leave_type_obj:
            return None, "Invalid leave type"
        
        # Calculate total days
        total_days = self.calculate_days(start_date, end_date, is_half_day)
        
        # Check balance (skip for unpaid leave)
        balance = None
        if leave_type != LeaveType.UNPAID:
            balance = await self.get_leave_balance(user.user_code, leave_type, year)
            if not balance:
                # Initialize balance
                await self.initialize_leave_balance(user.user_code, year)
                balance = await self.get_leave_balance(user.user_code, leave_type, year)
            
            if balance:
                available = float(balance.total_days) - float(balance.used_days) - float(balance.pending_days)
                if float(total_days) > available:
                    return None, f"Insufficient leave balance. Available: {available} days"
        
        # Check for overlapping requests
        overlap_result = await self.db.execute(
            select(LeaveRequest).where(
                LeaveRequest.user_code == user.user_code,
                LeaveRequest.status.in_([
                    LeaveStatus.PENDING, 
                    LeaveStatus.APPROVED_BY_TEAM_LEAD, 
                    LeaveStatus.APPROVED
                ]),
                LeaveRequest.start_date <= end_date,
                LeaveRequest.end_date >= start_date
            )
        )
        if overlap_result.scalar_one_or_none():
            return None, "Overlapping leave request exists"
        
        # Determine approvers based on role
        level1_approver_code = None
        final_approver_code = None
        
        if user.role == UserRole.EMPLOYEE:
            # Employee: Team Lead -> Manager
            level1_approver_code = user.team_lead_code
            # Get manager code from team lead
            if user.team_lead_code:
                tl = await self.get_user_by_code(user.team_lead_code)
                if tl:
                    final_approver_code = tl.manager_code
        elif user.role == UserRole.TEAM_LEAD:
            # Team Lead: Direct to Manager
            final_approver_code = user.manager_code
        elif user.role == UserRole.MANAGER:
            # Manager: Direct to Super Admin
            result = await self.db.execute(
                select(User.user_code).where(
                    User.role == UserRole.SUPER_ADMIN,
                    User.is_deleted == False,
                    User.is_active == True
                ).limit(1)
            )
            final_approver_code = result.scalar_one_or_none()
        
        # Create request
        leave_request = LeaveRequest(
            user_code=user.user_code,
            leave_type_id=leave_type_obj.id,
            start_date=start_date,
            end_date=end_date,
            total_days=total_days,
            reason=reason,
            is_half_day=is_half_day,
            half_day_type=half_day_type,
            emergency_contact=emergency_contact,
            emergency_phone=emergency_phone,
            status=LeaveStatus.PENDING,
            level1_approver_code=level1_approver_code,
            final_approver_code=final_approver_code
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
        """
        Team Lead approves leave request (Level 1).
        
        Only applicable for Employee leave requests.
        After Level 1 approval, request goes to Manager for final approval.
        """
        leave_request = await self.get_leave_request_by_id(request_id)
        if not leave_request:
            return None, "Leave request not found"
        
        if leave_request.status != LeaveStatus.PENDING:
            return None, f"Cannot approve request with status {leave_request.status.value}"
        
        # Verify approver is the designated level1 approver
        if leave_request.level1_approver_code != approver.user_code:
            # Super admin can approve any
            if approver.role != UserRole.SUPER_ADMIN:
                return None, "You are not authorized to approve this request at Level 1"
        
        leave_request.status = LeaveStatus.APPROVED_BY_TEAM_LEAD
        leave_request.level1_approved_by_code = approver.user_code
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
        """
        Manager/Super Admin approves leave request (Final).
        
        - For Employees: After Team Lead approval
        - For Team Leads: Direct approval by Manager
        - For Managers: Approval by Super Admin
        """
        leave_request = await self.get_leave_request_by_id(request_id)
        if not leave_request:
            return None, "Leave request not found"
        
        # Get the requestor to check their role
        requestor = await self.get_user_by_code(leave_request.user_code)
        if not requestor:
            return None, "Requestor not found"
        
        # Check valid status for final approval
        if requestor.role == UserRole.EMPLOYEE:
            # Employee requests need Level 1 approval first
            if leave_request.status != LeaveStatus.APPROVED_BY_TEAM_LEAD:
                return None, "Employee leave requests must be approved by Team Lead first"
        else:
            # Team Lead and Manager requests can be approved directly
            if leave_request.status != LeaveStatus.PENDING:
                return None, f"Cannot approve request with status {leave_request.status.value}"
        
        # Verify approver is the designated final approver
        if leave_request.final_approver_code != approver.user_code:
            # Super admin can approve any
            if approver.role != UserRole.SUPER_ADMIN:
                return None, "You are not authorized to give final approval"
        
        leave_request.status = LeaveStatus.APPROVED
        leave_request.final_approved_by_code = approver.user_code
        leave_request.final_approved_at = datetime.now(timezone.utc)
        leave_request.final_notes = notes
        
        # Update balance - move from pending to used
        result = await self.db.execute(
            select(LeaveTypeModel).where(LeaveTypeModel.id == leave_request.leave_type_id)
        )
        leave_type = result.scalar_one_or_none()
        
        if leave_type and leave_type.code != LeaveType.UNPAID:
            balance = await self.get_leave_balance(
                leave_request.user_code,
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
        """Reject leave request at any approval level."""
        leave_request = await self.get_leave_request_by_id(request_id)
        if not leave_request:
            return None, "Leave request not found"
        
        if leave_request.status not in [LeaveStatus.PENDING, LeaveStatus.APPROVED_BY_TEAM_LEAD]:
            return None, f"Cannot reject request with status {leave_request.status.value}"
        
        # Verify approver has permission
        can_reject = False
        if approver.role == UserRole.SUPER_ADMIN:
            can_reject = True
        elif leave_request.level1_approver_code == approver.user_code:
            can_reject = True
        elif leave_request.final_approver_code == approver.user_code:
            can_reject = True
        
        if not can_reject:
            return None, "You are not authorized to reject this request"
        
        leave_request.status = LeaveStatus.REJECTED
        leave_request.rejection_reason = reason
        leave_request.rejected_by_code = approver.user_code
        leave_request.rejected_at = datetime.now(timezone.utc)
        
        # Return pending days to balance
        result = await self.db.execute(
            select(LeaveTypeModel).where(LeaveTypeModel.id == leave_request.leave_type_id)
        )
        leave_type = result.scalar_one_or_none()
        
        if leave_type and leave_type.code != LeaveType.UNPAID:
            balance = await self.get_leave_balance(
                leave_request.user_code,
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
        request_id: UUID,
        reason: Optional[str] = None
    ) -> Tuple[Optional[LeaveRequest], Optional[str]]:
        """Cancel leave request by employee."""
        leave_request = await self.get_leave_request_by_id(request_id)
        if not leave_request:
            return None, "Leave request not found"
        
        if leave_request.user_code != user.user_code:
            return None, "Cannot cancel another user's request"
        
        if leave_request.status not in [LeaveStatus.PENDING, LeaveStatus.APPROVED_BY_TEAM_LEAD]:
            return None, "Cannot cancel approved or rejected requests"
        
        leave_request.status = LeaveStatus.CANCELLED
        leave_request.cancelled_at = datetime.now(timezone.utc)
        leave_request.cancellation_reason = reason
        
        # Return pending days to balance
        result = await self.db.execute(
            select(LeaveTypeModel).where(LeaveTypeModel.id == leave_request.leave_type_id)
        )
        leave_type = result.scalar_one_or_none()
        
        if leave_type and leave_type.code != LeaveType.UNPAID:
            balance = await self.get_leave_balance(
                leave_request.user_code,
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
        user_code: Optional[str] = None,
        user_id: Optional[UUID] = None,
        status: Optional[LeaveStatus] = None,
        leave_type: Optional[LeaveType] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[LeaveRequest], int]:
        """List leave requests with filtering."""
        query = select(LeaveRequest)
        count_query = select(func.count(LeaveRequest.id))
        
        # If user_id provided, get user_code
        if user_id and not user_code:
            user_result = await self.db.execute(
                select(User).where(User.id == user_id)
            )
            user = user_result.scalar_one_or_none()
            if user:
                user_code = user.user_code
        
        if user_code:
            query = query.where(LeaveRequest.user_code == user_code.upper())
            count_query = count_query.where(LeaveRequest.user_code == user_code.upper())
        
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
    
    async def get_pending_approvals(
        self,
        approver: User,
        level: str = "all",  # "level1", "final", "all"
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[LeaveRequest], int]:
        """
        Get pending leave approvals based on hierarchy.
        
        - SUPER_ADMIN: See all pending approvals
        - MANAGER: See Level 2 approvals (Team Lead approved) for their team leads
        - TEAM_LEAD: See Level 1 approvals for their employees
        """
        base_query = select(LeaveRequest)
        count_query = select(func.count(LeaveRequest.id))
        
        if approver.role == UserRole.SUPER_ADMIN:
            # See all pending and level1 approved
            if level == "level1":
                base_query = base_query.where(LeaveRequest.status == LeaveStatus.PENDING)
                count_query = count_query.where(LeaveRequest.status == LeaveStatus.PENDING)
            elif level == "final":
                base_query = base_query.where(LeaveRequest.status == LeaveStatus.APPROVED_BY_TEAM_LEAD)
                count_query = count_query.where(LeaveRequest.status == LeaveStatus.APPROVED_BY_TEAM_LEAD)
            else:
                base_query = base_query.where(
                    LeaveRequest.status.in_([LeaveStatus.PENDING, LeaveStatus.APPROVED_BY_TEAM_LEAD])
                )
                count_query = count_query.where(
                    LeaveRequest.status.in_([LeaveStatus.PENDING, LeaveStatus.APPROVED_BY_TEAM_LEAD])
                )
        elif approver.role == UserRole.MANAGER:
            # See final approvals where they are the final approver
            base_query = base_query.where(
                LeaveRequest.final_approver_code == approver.user_code,
                LeaveRequest.status.in_([LeaveStatus.PENDING, LeaveStatus.APPROVED_BY_TEAM_LEAD])
            )
            count_query = count_query.where(
                LeaveRequest.final_approver_code == approver.user_code,
                LeaveRequest.status.in_([LeaveStatus.PENDING, LeaveStatus.APPROVED_BY_TEAM_LEAD])
            )
        elif approver.role == UserRole.TEAM_LEAD:
            # See Level 1 approvals where they are the level1 approver
            base_query = base_query.where(
                LeaveRequest.level1_approver_code == approver.user_code,
                LeaveRequest.status == LeaveStatus.PENDING
            )
            count_query = count_query.where(
                LeaveRequest.level1_approver_code == approver.user_code,
                LeaveRequest.status == LeaveStatus.PENDING
            )
        else:
            return [], 0
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        query = base_query.offset((page - 1) * page_size).limit(page_size)
        query = query.order_by(LeaveRequest.created_at.desc())
        
        result = await self.db.execute(query)
        requests = result.scalars().all()
        
        return list(requests), total
    
    async def get_team_leave_requests(
        self,
        supervisor: User,
        status: Optional[LeaveStatus] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[LeaveRequest], int]:
        """
        Get leave requests for team members.
        
        - TEAM_LEAD: Gets requests from employees reporting to them
        - MANAGER: Gets requests from team leads and their employees
        """
        # Get team member codes
        if supervisor.role == UserRole.TEAM_LEAD:
            result = await self.db.execute(
                select(User.user_code).where(
                    User.team_lead_code == supervisor.user_code,
                    User.is_deleted == False,
                    User.is_active == True
                )
            )
            member_codes = [r for r in result.scalars().all()]
        elif supervisor.role == UserRole.MANAGER:
            # Get team leads
            tl_result = await self.db.execute(
                select(User.user_code).where(
                    User.manager_code == supervisor.user_code,
                    User.is_deleted == False,
                    User.is_active == True
                )
            )
            team_lead_codes = [r for r in tl_result.scalars().all()]
            
            # Get employees of those team leads
            emp_result = await self.db.execute(
                select(User.user_code).where(
                    User.team_lead_code.in_(team_lead_codes),
                    User.is_deleted == False,
                    User.is_active == True
                )
            )
            employee_codes = [r for r in emp_result.scalars().all()]
            
            member_codes = team_lead_codes + employee_codes
        else:
            return [], 0
        
        if not member_codes:
            return [], 0
        
        query = select(LeaveRequest).where(LeaveRequest.user_code.in_(member_codes))
        count_query = select(func.count(LeaveRequest.id)).where(LeaveRequest.user_code.in_(member_codes))
        
        if status:
            query = query.where(LeaveRequest.status == status)
            count_query = count_query.where(LeaveRequest.status == status)
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        query = query.offset((page - 1) * page_size).limit(page_size)
        query = query.order_by(LeaveRequest.created_at.desc())
        
        result = await self.db.execute(query)
        requests = result.scalars().all()
        
        return list(requests), total