from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from typing import Optional, List, Tuple
from uuid import UUID
from datetime import datetime, date, timezone

from ..models.attendance import Attendance, AttendanceEntry
from ..models.user import User
from ..models.enums import AttendanceStatus, UserRole


class AttendanceService:
    """Attendance management service."""
    
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
        user_id: UUID,
        attendance_date: date
    ) -> Optional[Attendance]:
        """Get user's attendance for a specific date."""
        result = await self.db.execute(
            select(Attendance)
            .where(
                Attendance.user_id == user_id,
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
        """Record check-in for user."""
        today = datetime.now(timezone.utc).date()
        
        # Get or create attendance record
        attendance = await self.get_user_attendance_for_date(user.id, today)
        
        if not attendance:
            attendance = Attendance(
                user_id=user.id,
                date=today,
                status=AttendanceStatus.DRAFT
            )
            self.db.add(attendance)
            await self.db.flush()
        
        # Check if there's an open entry (no checkout)
        for entry in attendance.entries:
            if entry.check_out is None:
                return None, "Already checked in. Please check out first."
        
        # Create new entry
        entry = AttendanceEntry(
            attendance_id=attendance.id,
            check_in=datetime.now(timezone.utc),
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
        """Record check-out for user."""
        today = datetime.now(timezone.utc).date()
        
        attendance = await self.get_user_attendance_for_date(user.id, today)
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
        
        entry.check_out = datetime.now(timezone.utc)
        if notes:
            entry.notes = (entry.notes or "") + f" | Checkout: {notes}"
        
        await self.db.commit()
        
        attendance = await self.get_attendance_by_id(attendance.id)
        return attendance, None
    
    async def submit_for_approval(
        self,
        user: User,
        attendance_id: UUID,
        notes: Optional[str] = None
    ) -> Tuple[Optional[Attendance], Optional[str]]:
        """Submit attendance for manager approval."""
        attendance = await self.get_attendance_by_id(attendance_id)
        if not attendance:
            return None, "Attendance record not found"
        
        if str(attendance.user_id) != str(user.id):
            return None, "Cannot submit another user's attendance"
        
        if attendance.status != AttendanceStatus.DRAFT:
            return None, f"Cannot submit attendance with status {attendance.status.value}"
        
        # Check all entries are closed
        for entry in attendance.entries:
            if entry.check_out is None:
                return None, "Please check out before submitting"
        
        attendance.status = AttendanceStatus.PENDING_MANAGER
        
        await self.db.commit()
        await self.db.refresh(attendance)
        
        return attendance, None
    
    async def approve_attendance(
        self,
        approver: User,
        attendance_id: UUID,
        notes: Optional[str] = None
    ) -> Tuple[Optional[Attendance], Optional[str]]:
        """Approve attendance record."""
        attendance = await self.get_attendance_by_id(attendance_id)
        if not attendance:
            return None, "Attendance record not found"
        
        if attendance.status != AttendanceStatus.PENDING_MANAGER:
            return None, f"Cannot approve attendance with status {attendance.status.value}"
        
        # Validate approver has permission
        if approver.role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.MANAGER]:
            if approver.role == UserRole.TEAM_LEAD:
                # Team lead can only approve their team members
                result = await self.db.execute(
                    select(User).where(User.id == attendance.user_id)
                )
                employee = result.scalar_one_or_none()
                if not employee or str(employee.team_lead_id) != str(approver.id):
                    return None, "Cannot approve attendance for non-team members"
            else:
                return None, "Insufficient permissions"
        
        attendance.status = AttendanceStatus.APPROVED
        attendance.approved_by_id = approver.id
        attendance.approved_at = datetime.now(timezone.utc)
        attendance.approval_notes = notes
        
        await self.db.commit()
        await self.db.refresh(attendance)
        
        return attendance, None
    
    async def reject_attendance(
        self,
        approver: User,
        attendance_id: UUID,
        reason: str
    ) -> Tuple[Optional[Attendance], Optional[str]]:
        """Reject attendance record."""
        attendance = await self.get_attendance_by_id(attendance_id)
        if not attendance:
            return None, "Attendance record not found"
        
        if attendance.status != AttendanceStatus.PENDING_MANAGER:
            return None, f"Cannot reject attendance with status {attendance.status.value}"
        
        attendance.status = AttendanceStatus.REJECTED
        attendance.approved_by_id = approver.id
        attendance.approved_at = datetime.now(timezone.utc)
        attendance.rejection_reason = reason
        
        await self.db.commit()
        await self.db.refresh(attendance)
        
        return attendance, None
    
    async def list_attendances(
        self,
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
        
        if user_id:
            query = query.where(Attendance.user_id == user_id)
            count_query = count_query.where(Attendance.user_id == user_id)
        
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
        """Get pending attendance approvals for a manager/team lead."""
        query = select(Attendance).where(
            Attendance.status == AttendanceStatus.PENDING_MANAGER
        ).options(selectinload(Attendance.entries))
        count_query = select(func.count(Attendance.id)).where(
            Attendance.status == AttendanceStatus.PENDING_MANAGER
        )
        
        # Filter by team for team leads
        if approver.role == UserRole.TEAM_LEAD:
            team_member_ids = await self.db.execute(
                select(User.id).where(User.team_lead_id == approver.id)
            )
            member_ids = [row[0] for row in team_member_ids.fetchall()]
            if member_ids:
                query = query.where(Attendance.user_id.in_(member_ids))
                count_query = count_query.where(Attendance.user_id.in_(member_ids))
            else:
                return [], 0
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        query = query.offset((page - 1) * page_size).limit(page_size)
        query = query.order_by(Attendance.date.desc())
        
        result = await self.db.execute(query)
        attendances = result.scalars().unique().all()
        
        return list(attendances), total