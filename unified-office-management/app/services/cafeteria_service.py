from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from typing import Optional, List, Tuple
from uuid import UUID
from datetime import date, time

from ..models.cafeteria import CafeteriaTableBooking
from ..models.floor_plan import FloorPlanVersion
from ..models.user import User
from ..models.enums import CellType, BookingStatus
from ..schemas.cafeteria import CafeteriaBookingCreate, CafeteriaBookingUpdate


class CafeteriaService:
    """Cafeteria table booking service."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_booking_by_id(
        self,
        booking_id: UUID
    ) -> Optional[CafeteriaTableBooking]:
        """Get cafeteria booking by ID."""
        result = await self.db.execute(
            select(CafeteriaTableBooking).where(CafeteriaTableBooking.id == booking_id)
        )
        return result.scalar_one_or_none()
    
    async def validate_table_cell(
        self,
        floor_plan_id: UUID,
        cell_row: str,
        cell_column: str
    ) -> Tuple[bool, Optional[str]]:
        """Validate that the cell is a valid cafeteria table."""
        result = await self.db.execute(
            select(FloorPlanVersion)
            .where(FloorPlanVersion.floor_plan_id == floor_plan_id)
            .order_by(FloorPlanVersion.version.desc())
            .limit(1)
        )
        version = result.scalar_one_or_none()
        
        if not version:
            return False, "Floor plan not found"
        
        row_idx = int(cell_row)
        col_idx = int(cell_column)
        
        if row_idx >= len(version.grid_data) or col_idx >= len(version.grid_data[0]):
            return False, "Cell coordinates out of bounds"
        
        cell = version.grid_data[row_idx][col_idx]
        if cell.get("cell_type") != CellType.CAFETERIA_TABLE.value:
            return False, "Cell is not a cafeteria table"
        
        return True, None
    
    async def check_booking_overlap(
        self,
        floor_plan_id: UUID,
        table_label: str,
        booking_date: date,
        start_time: time,
        end_time: time,
        exclude_booking_id: Optional[UUID] = None
    ) -> bool:
        """Check if there's an overlapping booking."""
        query = select(CafeteriaTableBooking).where(
            and_(
                CafeteriaTableBooking.floor_plan_id == floor_plan_id,
                CafeteriaTableBooking.table_label == table_label,
                CafeteriaTableBooking.booking_date == booking_date,
                CafeteriaTableBooking.status.in_([BookingStatus.PENDING, BookingStatus.CONFIRMED]),
                or_(
                    and_(
                        CafeteriaTableBooking.start_time <= start_time,
                        CafeteriaTableBooking.end_time > start_time
                    ),
                    and_(
                        CafeteriaTableBooking.start_time < end_time,
                        CafeteriaTableBooking.end_time >= end_time
                    ),
                    and_(
                        CafeteriaTableBooking.start_time >= start_time,
                        CafeteriaTableBooking.end_time <= end_time
                    )
                )
            )
        )
        
        if exclude_booking_id:
            query = query.where(CafeteriaTableBooking.id != exclude_booking_id)
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none() is not None
    
    async def create_booking(
        self,
        booking_data: CafeteriaBookingCreate,
        user: User
    ) -> Tuple[Optional[CafeteriaTableBooking], Optional[str]]:
        """Create a new cafeteria table booking."""
        # Validate table cell
        valid, error = await self.validate_table_cell(
            booking_data.floor_plan_id,
            booking_data.cell_row,
            booking_data.cell_column
        )
        if not valid:
            return None, error
        
        # Check for overlapping bookings
        has_overlap = await self.check_booking_overlap(
            booking_data.floor_plan_id,
            booking_data.table_label,
            booking_data.booking_date,
            booking_data.start_time,
            booking_data.end_time
        )
        if has_overlap:
            return None, "Time slot overlaps with existing booking"
        
        booking = CafeteriaTableBooking(
            floor_plan_id=booking_data.floor_plan_id,
            table_label=booking_data.table_label,
            cell_row=booking_data.cell_row,
            cell_column=booking_data.cell_column,
            user_id=user.id,
            booking_date=booking_data.booking_date,
            start_time=booking_data.start_time,
            end_time=booking_data.end_time,
            guest_count=booking_data.guest_count,
            status=BookingStatus.CONFIRMED,
            notes=booking_data.notes
        )
        
        self.db.add(booking)
        await self.db.commit()
        await self.db.refresh(booking)
        
        return booking, None
    
    async def update_booking(
        self,
        booking_id: UUID,
        booking_data: CafeteriaBookingUpdate,
        user: User
    ) -> Tuple[Optional[CafeteriaTableBooking], Optional[str]]:
        """Update a cafeteria table booking."""
        booking = await self.get_booking_by_id(booking_id)
        if not booking:
            return None, "Booking not found"
        
        if str(booking.user_id) != str(user.id):
            from ..models.enums import UserRole
            if user.role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
                return None, "Cannot modify another user's booking"
        
        if booking_data.start_time or booking_data.end_time:
            start = booking_data.start_time or booking.start_time
            end = booking_data.end_time or booking.end_time
            
            has_overlap = await self.check_booking_overlap(
                booking.floor_plan_id,
                booking.table_label,
                booking.booking_date,
                start,
                end,
                exclude_booking_id=booking_id
            )
            if has_overlap:
                return None, "Time slot overlaps with existing booking"
        
        update_data = booking_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(booking, field, value)
        
        await self.db.commit()
        await self.db.refresh(booking)
        
        return booking, None
    
    async def cancel_booking(
        self,
        booking_id: UUID,
        user: User
    ) -> Tuple[bool, Optional[str]]:
        """Cancel a cafeteria table booking."""
        booking = await self.get_booking_by_id(booking_id)
        if not booking:
            return False, "Booking not found"
        
        if str(booking.user_id) != str(user.id):
            from ..models.enums import UserRole
            if user.role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
                return False, "Cannot cancel another user's booking"
        
        booking.status = BookingStatus.CANCELLED
        await self.db.commit()
        
        return True, None
    
    async def list_bookings(
        self,
        floor_plan_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        booking_date: Optional[date] = None,
        status: Optional[BookingStatus] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[CafeteriaTableBooking], int]:
        """List cafeteria table bookings with filtering."""
        query = select(CafeteriaTableBooking)
        count_query = select(func.count(CafeteriaTableBooking.id))
        
        if floor_plan_id:
            query = query.where(CafeteriaTableBooking.floor_plan_id == floor_plan_id)
            count_query = count_query.where(CafeteriaTableBooking.floor_plan_id == floor_plan_id)
        
        if user_id:
            query = query.where(CafeteriaTableBooking.user_id == user_id)
            count_query = count_query.where(CafeteriaTableBooking.user_id == user_id)
        
        if booking_date:
            query = query.where(CafeteriaTableBooking.booking_date == booking_date)
            count_query = count_query.where(CafeteriaTableBooking.booking_date == booking_date)
        
        if status:
            query = query.where(CafeteriaTableBooking.status == status)
            count_query = count_query.where(CafeteriaTableBooking.status == status)
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        query = query.offset((page - 1) * page_size).limit(page_size)
        query = query.order_by(CafeteriaTableBooking.booking_date, CafeteriaTableBooking.start_time)
        
        result = await self.db.execute(query)
        bookings = result.scalars().all()
        
        return list(bookings), total