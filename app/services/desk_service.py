from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from typing import Optional, List, Tuple
from uuid import UUID
from datetime import date, time

from ..models.desk import DeskBooking
from ..models.floor_plan import FloorPlan, FloorPlanVersion
from ..models.user import User
from ..models.enums import CellType, BookingStatus
from ..schemas.desk import DeskBookingCreate, DeskBookingUpdate


class DeskService:
    """Desk booking service."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_booking_by_id(
        self,
        booking_id: UUID
    ) -> Optional[DeskBooking]:
        """Get desk booking by ID."""
        result = await self.db.execute(
            select(DeskBooking).where(DeskBooking.id == booking_id)
        )
        return result.scalar_one_or_none()
    
    async def validate_desk_cell(
        self,
        floor_plan_id: UUID,
        cell_row: str,
        cell_column: str
    ) -> Tuple[bool, Optional[str], Optional[int]]:
        """Validate that the cell is a valid desk."""
        result = await self.db.execute(
            select(FloorPlanVersion)
            .where(FloorPlanVersion.floor_plan_id == floor_plan_id)
            .order_by(FloorPlanVersion.version.desc())
            .limit(1)
        )
        version = result.scalar_one_or_none()
        
        if not version:
            return False, "Floor plan not found", None
        
        row_idx = int(cell_row)
        col_idx = int(cell_column)
        
        if row_idx >= len(version.grid_data) or col_idx >= len(version.grid_data[0]):
            return False, "Cell coordinates out of bounds", None
        
        cell = version.grid_data[row_idx][col_idx]
        if cell.get("cell_type") != CellType.DESK.value:
            return False, "Cell is not a desk", None
        
        if not cell.get("is_active", True):
            return False, "Desk is not active", None
        
        return True, None, version.version
    
    async def check_booking_overlap(
        self,
        floor_plan_id: UUID,
        desk_label: str,
        booking_date: date,
        start_time: time,
        end_time: time,
        exclude_booking_id: Optional[UUID] = None
    ) -> bool:
        """Check if there's an overlapping booking."""
        query = select(DeskBooking).where(
            and_(
                DeskBooking.floor_plan_id == floor_plan_id,
                DeskBooking.desk_label == desk_label,
                DeskBooking.booking_date == booking_date,
                DeskBooking.status.in_([BookingStatus.PENDING, BookingStatus.CONFIRMED]),
                or_(
                    and_(
                        DeskBooking.start_time <= start_time,
                        DeskBooking.end_time > start_time
                    ),
                    and_(
                        DeskBooking.start_time < end_time,
                        DeskBooking.end_time >= end_time
                    ),
                    and_(
                        DeskBooking.start_time >= start_time,
                        DeskBooking.end_time <= end_time
                    )
                )
            )
        )
        
        if exclude_booking_id:
            query = query.where(DeskBooking.id != exclude_booking_id)
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none() is not None
    
    async def create_booking(
        self,
        booking_data: DeskBookingCreate,
        user: User
    ) -> Tuple[Optional[DeskBooking], Optional[str]]:
        """Create a new desk booking."""
        # Validate desk cell
        valid, error, version = await self.validate_desk_cell(
            booking_data.floor_plan_id,
            booking_data.cell_row,
            booking_data.cell_column
        )
        if not valid:
            return None, error
        
        # Check for overlapping bookings
        has_overlap = await self.check_booking_overlap(
            booking_data.floor_plan_id,
            booking_data.desk_label,
            booking_data.booking_date,
            booking_data.start_time,
            booking_data.end_time
        )
        if has_overlap:
            return None, "Time slot overlaps with existing booking"
        
        booking = DeskBooking(
            floor_plan_id=booking_data.floor_plan_id,
            floor_plan_version=str(version),
            desk_label=booking_data.desk_label,
            cell_row=booking_data.cell_row,
            cell_column=booking_data.cell_column,
            user_id=user.id,
            booking_date=booking_data.booking_date,
            start_time=booking_data.start_time,
            end_time=booking_data.end_time,
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
        booking_data: DeskBookingUpdate,
        user: User
    ) -> Tuple[Optional[DeskBooking], Optional[str]]:
        """Update a desk booking."""
        booking = await self.get_booking_by_id(booking_id)
        if not booking:
            return None, "Booking not found"
        
        # Check ownership or admin access
        if str(booking.user_id) != str(user.id):
            from ..models.enums import UserRole
            if user.role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
                return None, "Cannot modify another user's booking"
        
        # If updating time, check for overlaps
        if booking_data.start_time or booking_data.end_time:
            start = booking_data.start_time or booking.start_time
            end = booking_data.end_time or booking.end_time
            
            has_overlap = await self.check_booking_overlap(
                booking.floor_plan_id,
                booking.desk_label,
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
        """Cancel a desk booking."""
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
    ) -> Tuple[List[DeskBooking], int]:
        """List desk bookings with filtering."""
        query = select(DeskBooking)
        count_query = select(func.count(DeskBooking.id))
        
        if floor_plan_id:
            query = query.where(DeskBooking.floor_plan_id == floor_plan_id)
            count_query = count_query.where(DeskBooking.floor_plan_id == floor_plan_id)
        
        if user_id:
            query = query.where(DeskBooking.user_id == user_id)
            count_query = count_query.where(DeskBooking.user_id == user_id)
        
        if booking_date:
            query = query.where(DeskBooking.booking_date == booking_date)
            count_query = count_query.where(DeskBooking.booking_date == booking_date)
        
        if status:
            query = query.where(DeskBooking.status == status)
            count_query = count_query.where(DeskBooking.status == status)
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        query = query.offset((page - 1) * page_size).limit(page_size)
        query = query.order_by(DeskBooking.booking_date, DeskBooking.start_time)
        
        result = await self.db.execute(query)
        bookings = result.scalars().all()
        
        return list(bookings), total
    
    async def get_available_desks(
        self,
        floor_plan_id: UUID,
        booking_date: date,
        start_time: time,
        end_time: time
    ) -> List[dict]:
        """Get all available desks for a time slot."""
        # Get latest version grid
        result = await self.db.execute(
            select(FloorPlanVersion)
            .where(FloorPlanVersion.floor_plan_id == floor_plan_id)
            .order_by(FloorPlanVersion.version.desc())
            .limit(1)
        )
        version = result.scalar_one_or_none()
        
        if not version:
            return []
        
        # Get all booked desks for this time slot
        booked_result = await self.db.execute(
            select(DeskBooking.desk_label).where(
                and_(
                    DeskBooking.floor_plan_id == floor_plan_id,
                    DeskBooking.booking_date == booking_date,
                    DeskBooking.status.in_([BookingStatus.PENDING, BookingStatus.CONFIRMED]),
                    or_(
                        and_(
                            DeskBooking.start_time <= start_time,
                            DeskBooking.end_time > start_time
                        ),
                        and_(
                            DeskBooking.start_time < end_time,
                            DeskBooking.end_time >= end_time
                        ),
                        and_(
                            DeskBooking.start_time >= start_time,
                            DeskBooking.end_time <= end_time
                        )
                    )
                )
            )
        )
        booked_desks = set(row[0] for row in booked_result.fetchall())
        
        # Find available desks from grid
        available = []
        for row_idx, row in enumerate(version.grid_data):
            for col_idx, cell in enumerate(row):
                if cell.get("cell_type") == CellType.DESK.value:
                    if cell.get("is_active", True):
                        label = cell.get("label", f"Desk-{row_idx}-{col_idx}")
                        if label not in booked_desks:
                            available.append({
                                "row": row_idx,
                                "column": col_idx,
                                "label": label,
                                "direction": cell.get("direction")
                            })
        
        return available