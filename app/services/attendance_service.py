from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from typing import Optional, List, Tuple
from uuid import UUID
from datetime import datetime, date, timezone, timedelta

from ..models.attendance import Attendance, AttendanceEntry
from ..models.user import User
from ..models.enums import AttendanceStatus, UserRole


class AttendanceService:
    """
    Attendance management service with hierarchical approval.
    
    Approval Hierarchy:
    - EMPLOYEE: Approved by their TEAM_LEAD
    - TEAM_LEAD: Approved by their MANAGER
    - MANAGER: Approved by SUPER_ADMIN
    
    All attendance uses user_code as the primary identifier.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_attendance_by_id(
        self,
        attendance_id: UUID
    ) -> Optional[Attendance]:
        """Get attendance by ID with entries."""
        result = await self.db.execute(
            select(Attendance)
            .where(Attendance.id == attendance_id)
            .options(selectinload(Attendance.entries))
        )
        return result.scalar_one_or_none()
    
    async def get_user_attendance_for_date(
        self,
        user_code: str,
        attendance_date: date
    ) -> Optional[Attendance]:
        """Get user's attendance for a specific date by user_code."""
        result = await self.db.execute(
            select(Attendance)
            .where(
                Attendance.user_code == user_code.upper(),
                Attendance.date == attendance_date
            )
            .options(selectinload(Attendance.entries))
        )
        return result.scalar_one_or_none()
    
    async def check_in(
        self,
        user: User,
        notes: Optional[str] = None
    ) -> Tuple[Optional[Attendance], Optional[str]]:
        """
        Record check-in for user.
        
        Creates or updates attendance record for today.
        Tracks first_check_in and allows multiple entries.
        """
        today = datetime.now(timezone.utc).date()
        now = datetime.now(timezone.utc)
        
        # Get or create attendance record
        attendance = await self.get_user_attendance_for_date(user.user_code, today)
        
        if not attendance:
            attendance = Attendance(
                user_code=user.user_code,
                date=today,
                status=AttendanceStatus.DRAFT,
                first_check_in=now.time()  # Use .time() for Time column
            )
            self.db.add(attendance)
            await self.db.flush()
            # Reload the attendance record with entries to avoid MissingGreenlet error
            attendance = await self.get_attendance_by_id(attendance.id)
        
        # Check if there's an open entry (no checkout)
        for entry in attendance.entries:
            if entry.check_out is None:
                return None, "Already checked in. Please check out first."
        
        # Create new entry
        entry = AttendanceEntry(
            attendance_id=attendance.id,
            check_in=now,
            entry_type="regular",
            notes=notes
        )
        self.db.add(entry)
        
        await self.db.commit()
        await self.db.refresh(attendance)
        
        # Reload with entries
        attendance = await self.get_attendance_by_id(attendance.id)
        
        return attendance, None
    
    async def check_out(
        self,
        user: User,
        entry_id: UUID,
        notes: Optional[str] = None
    ) -> Tuple[Optional[Attendance], Optional[str]]:
        """
        Record check-out for user.
        
        Updates last_check_out and calculates total_hours.
        """
        today = datetime.now(timezone.utc).date()
        now = datetime.now(timezone.utc)
        
        attendance = await self.get_user_attendance_for_date(user.user_code, today)
        if not attendance:
            return None, "No attendance record found for today"
        
        # Find the entry
        entry = None
        for e in attendance.entries:
            if str(e.id) == str(entry_id):
                entry = e
                break
        
        if not entry:
            return None, "Entry not found"
        
        if entry.check_out is not None:
            return None, "Already checked out"
        
        entry.check_out = now
        
        # Calculate duration for this entry
        duration = (entry.check_out - entry.check_in).total_seconds() / 3600
        entry.duration_hours = round(duration, 2)
        
        if notes:
            entry.notes = (entry.notes or "") + f" | Checkout: {notes}"
        
        # Update attendance summary fields
        attendance.last_check_out = now.time()  # Use .time() for Time column
        
        # Recalculate total hours
        total_hours = 0.0
        for e in attendance.entries:
            if e.duration_hours:
                total_hours += e.duration_hours
            elif e.check_out and e.check_in:
                total_hours += (e.check_out - e.check_in).total_seconds() / 3600
        attendance.total_hours = round(total_hours, 2)
        
        await self.db.commit()
        
        attendance = await self.get_attendance_by_id(attendance.id)
        return attendance, None
    
    async def submit_for_approval(
        self,
        user: User,
        attendance_id: UUID,
        notes: Optional[str] = None
    ) -> Tuple[Optional[Attendance], Optional[str]]:
        """
        Submit attendance for hierarchical approval.
        
        Approval is sent to:
        - EMPLOYEE -> TEAM_LEAD
        - TEAM_LEAD -> MANAGER
        - MANAGER -> SUPER_ADMIN
        """
        attendance = await self.get_attendance_by_id(attendance_id)
        if not attendance:
            return None, "Attendance record not found"
        
        if attendance.user_code != user.user_code:
            return None, "Cannot submit another user's attendance"
        
        if attendance.status != AttendanceStatus.DRAFT:
            return None, f"Cannot submit attendance with status {attendance.status.value}"
        
        # Check all entries are closed
        for entry in attendance.entries:
            if entry.check_out is None:
                return None, "Please check out before submitting"
        
        attendance.status = AttendanceStatus.PENDING_APPROVAL
        attendance.submitted_at = datetime.now(timezone.utc)
        
        # Determine approver based on user role
        if user.role == UserRole.EMPLOYEE:
            attendance.approver_code = user.team_lead_code
        elif user.role == UserRole.TEAM_LEAD:
            attendance.approver_code = user.manager_code
        elif user.role == UserRole.MANAGER:
            # Find super admin
            result = await self.db.execute(
                select(User.user_code).where(
                    User.role == UserRole.SUPER_ADMIN,
                    User.is_deleted == False,
                    User.is_active == True
                ).limit(1)
            )
            super_admin_code = result.scalar_one_or_none()
            attendance.approver_code = super_admin_code
        
        await self.db.commit()
        await self.db.refresh(attendance)
        
        return attendance, None
    
    async def approve_attendance(
        self,
        approver: User,
        attendance_id: UUID,
        notes: Optional[str] = None
    ) -> Tuple[Optional[Attendance], Optional[str]]:
        """
        Approve attendance record.
        
        Approval Permission Logic:
        - SUPER_ADMIN: Can approve any attendance
        - MANAGER: Can approve team lead's attendance (if manager_code matches)
        - TEAM_LEAD: Can approve employee's attendance (if team_lead_code matches)
        """
        attendance = await self.get_attendance_by_id(attendance_id)
        if not attendance:
            return None, "Attendance record not found"
        
        if attendance.status != AttendanceStatus.PENDING_APPROVAL:
            return None, f"Cannot approve attendance with status {attendance.status.value}"
        
        # Validate approver has permission
        can_approve, error = await self._can_approve_attendance(approver, attendance)
        if not can_approve:
            return None, error
        
        attendance.status = AttendanceStatus.APPROVED
        attendance.approved_by_code = approver.user_code
        attendance.approved_at = datetime.now(timezone.utc)
        attendance.approval_notes = notes
        
        await self.db.commit()
        await self.db.refresh(attendance)
        
        return attendance, None
    
    async def _can_approve_attendance(
        self,
        approver: User,
        attendance: Attendance
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if approver can approve the attendance.
        
        Uses hierarchical approval:
        - Check if approver's user_code matches the attendance.approver_code
        - Or if approver is SUPER_ADMIN (can approve anything)
        """
        # Super Admin can approve anyone
        if approver.role == UserRole.SUPER_ADMIN:
            return True, None
        
        # Check if this approver is the designated approver
        if attendance.approver_code == approver.user_code:
            return True, None
        
        # Get the employee's user info to check hierarchy
        result = await self.db.execute(
            select(User).where(
                User.user_code == attendance.user_code,
                User.is_deleted == False
            )
        )
        employee = result.scalar_one_or_none()
        if not employee:
            return False, "Employee not found"
        
        # Team Lead can approve their direct reports (employees)
        if approver.role == UserRole.TEAM_LEAD:
            if employee.role == UserRole.EMPLOYEE and employee.team_lead_code == approver.user_code:
                return True, None
            return False, "You can only approve attendance for your team members"
        
        # Manager can approve their direct reports (team leads)
        if approver.role == UserRole.MANAGER:
            if employee.role == UserRole.TEAM_LEAD and employee.manager_code == approver.user_code:
                return True, None
            return False, "You can only approve attendance for your direct reports"
        
        return False, "Insufficient permissions to approve attendance"
    
    async def reject_attendance(
        self,
        approver: User,
        attendance_id: UUID,
        reason: str
    ) -> Tuple[Optional[Attendance], Optional[str]]:
        """Reject attendance record with reason."""
        attendance = await self.get_attendance_by_id(attendance_id)
        if not attendance:
            return None, "Attendance record not found"
        
        if attendance.status != AttendanceStatus.PENDING_APPROVAL:
            return None, f"Cannot reject attendance with status {attendance.status.value}"
        
        # Validate approver has permission
        can_approve, error = await self._can_approve_attendance(approver, attendance)
        if not can_approve:
            return None, error
        
        attendance.status = AttendanceStatus.REJECTED
        attendance.approved_by_code = approver.user_code
        attendance.approved_at = datetime.now(timezone.utc)
        attendance.rejection_reason = reason
        
        await self.db.commit()
        await self.db.refresh(attendance)
        
        return attendance, None
    
    async def list_attendances(
        self,
        user_code: Optional[str] = None,
        user_id: Optional[UUID] = None,
        status: Optional[AttendanceStatus] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Attendance], int]:
        """List attendance records with filtering."""
        query = select(Attendance).options(selectinload(Attendance.entries))
        count_query = select(func.count(Attendance.id))
        
        # If user_id is provided, get user_code from User model
        if user_id and not user_code:
            user_result = await self.db.execute(
                select(User).where(User.id == user_id)
            )
            user = user_result.scalar_one_or_none()
            if user:
                user_code = user.user_code
        
        if user_code:
            query = query.where(Attendance.user_code == user_code.upper())
            count_query = count_query.where(Attendance.user_code == user_code.upper())
        
        if status:
            query = query.where(Attendance.status == status)
            count_query = count_query.where(Attendance.status == status)
        
        if start_date:
            query = query.where(Attendance.date >= start_date)
            count_query = count_query.where(Attendance.date >= start_date)
        
        if end_date:
            query = query.where(Attendance.date <= end_date)
            count_query = count_query.where(Attendance.date <= end_date)
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        query = query.offset((page - 1) * page_size).limit(page_size)
        query = query.order_by(Attendance.date.desc())
        
        result = await self.db.execute(query)
        attendances = result.scalars().unique().all()
        
        return list(attendances), total
    
    async def get_pending_approvals(
        self,
        approver: User,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Attendance], int]:
        """
        Get pending attendance approvals based on hierarchy.
        
        - SUPER_ADMIN: See all pending approvals
        - MANAGER: See pending approvals from team leads reporting to them
        - TEAM_LEAD: See pending approvals from employees reporting to them
        """
        base_query = select(Attendance).where(
            Attendance.status == AttendanceStatus.PENDING_APPROVAL
        ).options(selectinload(Attendance.entries))
        count_query = select(func.count(Attendance.id)).where(
            Attendance.status == AttendanceStatus.PENDING_APPROVAL
        )
        
        # Filter based on role
        if approver.role == UserRole.SUPER_ADMIN:
            # See all pending approvals
            pass
        elif approver.role == UserRole.MANAGER:
            # See approvals where they are the designated approver
            # (team leads who report to this manager)
            base_query = base_query.where(
                Attendance.approver_code == approver.user_code
            )
            count_query = count_query.where(
                Attendance.approver_code == approver.user_code
            )
        elif approver.role == UserRole.TEAM_LEAD:
            # See approvals where they are the designated approver
            # (employees who report to this team lead)
            base_query = base_query.where(
                Attendance.approver_code == approver.user_code
            )
            count_query = count_query.where(
                Attendance.approver_code == approver.user_code
            )
        else:
            # No approvals for employees
            return [], 0
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        query = base_query.offset((page - 1) * page_size).limit(page_size)
        query = query.order_by(Attendance.date.desc())
        
        result = await self.db.execute(query)
        attendances = result.scalars().unique().all()
        
        return list(attendances), total
    
    async def get_team_attendance(
        self,
        supervisor: User,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Attendance], int]:
        """
        Get attendance records for team members.
        
        - TEAM_LEAD: Gets attendance for employees reporting to them
        - MANAGER: Gets attendance for team leads and their employees
        """
        # Get direct report user codes
        if supervisor.role == UserRole.TEAM_LEAD:
            result = await self.db.execute(
                select(User.user_code).where(
                    User.team_lead_code == supervisor.user_code,
                    User.is_deleted == False,
                    User.is_active == True
                )
            )
        elif supervisor.role == UserRole.MANAGER:
            # Get team leads and their employees
            tl_result = await self.db.execute(
                select(User.user_code).where(
                    User.manager_code == supervisor.user_code,
                    User.is_deleted == False,
                    User.is_active == True
                )
            )
            team_lead_codes = [r for r in tl_result.scalars().all()]
            
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
        
        if supervisor.role == UserRole.TEAM_LEAD:
            member_codes = [r for r in result.scalars().all()]
        
        if not member_codes:
            return [], 0
        
        query = select(Attendance).where(
            Attendance.user_code.in_(member_codes)
        ).options(selectinload(Attendance.entries))
        count_query = select(func.count(Attendance.id)).where(
            Attendance.user_code.in_(member_codes)
        )
        
        if start_date:
            query = query.where(Attendance.date >= start_date)
            count_query = count_query.where(Attendance.date >= start_date)
        
        if end_date:
            query = query.where(Attendance.date <= end_date)
            count_query = count_query.where(Attendance.date <= end_date)
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        query = query.offset((page - 1) * page_size).limit(page_size)
        query = query.order_by(Attendance.date.desc())
        
        result = await self.db.execute(query)
        attendances = result.scalars().unique().all()
        
        return list(attendances), total