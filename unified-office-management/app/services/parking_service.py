from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Optional, List, Tuple
from uuid import UUID
from datetime import datetime, timezone

from ..models.parking import ParkingAllocation, ParkingHistory
from ..models.floor_plan import FloorPlan, FloorPlanVersion
from ..models.user import User
from ..models.enums import CellType, ParkingType
from ..schemas.parking import ParkingAllocationCreate, ParkingAllocationUpdate


class ParkingService:
    """Parking management service."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_allocation_by_id(
        self,
        allocation_id: UUID
    ) -> Optional[ParkingAllocation]:
        """Get parking allocation by ID."""
        result = await self.db.execute(
            select(ParkingAllocation).where(ParkingAllocation.id == allocation_id)
        )
        return result.scalar_one_or_none()
    
    async def validate_parking_slot(
        self,
        floor_plan_id: UUID,
        cell_row: str,
        cell_column: str
    ) -> Tuple[bool, Optional[str]]:
        """Validate that the cell is a valid parking slot."""
        # Get latest floor plan version
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
        if cell.get("cell_type") != CellType.PARKING_SLOT.value:
            return False, "Cell is not a parking slot"
        
        return True, None
    
    async def check_user_active_parking(
        self,
        user_id: UUID
    ) -> Optional[ParkingAllocation]:
        """Check if user has an active parking allocation."""
        result = await self.db.execute(
            select(ParkingAllocation).where(
                and_(
                    ParkingAllocation.user_id == user_id,
                    ParkingAllocation.is_active == True,
                    ParkingAllocation.exit_time.is_(None)
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def check_slot_availability(
        self,
        floor_plan_id: UUID,
        slot_label: str
    ) -> bool:
        """Check if a parking slot is available."""
        result = await self.db.execute(
            select(ParkingAllocation).where(
                and_(
                    ParkingAllocation.floor_plan_id == floor_plan_id,
                    ParkingAllocation.slot_label == slot_label,
                    ParkingAllocation.is_active == True,
                    ParkingAllocation.exit_time.is_(None)
                )
            )
        )
        return result.scalar_one_or_none() is None
    
    async def create_allocation(
        self,
        allocation_data: ParkingAllocationCreate,
        created_by: User
    ) -> Tuple[Optional[ParkingAllocation], Optional[str]]:
        """Create a new parking allocation."""
        # Validate parking slot
        valid, error = await self.validate_parking_slot(
            allocation_data.floor_plan_id,
            allocation_data.cell_row,
            allocation_data.cell_column
        )
        if not valid:
            return None, error
        
        # Check slot availability
        if not await self.check_slot_availability(
            allocation_data.floor_plan_id,
            allocation_data.slot_label
        ):
            return None, "Parking slot is already occupied"
        
        # For employee parking, check if user already has active parking
        if allocation_data.parking_type == ParkingType.EMPLOYEE:
            if not allocation_data.user_id:
                return None, "User ID required for employee parking"
            
            existing = await self.check_user_active_parking(allocation_data.user_id)
            if existing:
                return None, "User already has an active parking allocation"
        
        # For visitor parking, validate visitor info
        if allocation_data.parking_type == ParkingType.VISITOR:
            if not allocation_data.visitor_name:
                return None, "Visitor name required for visitor parking"
        
        allocation = ParkingAllocation(
            floor_plan_id=allocation_data.floor_plan_id,
            slot_label=allocation_data.slot_label,
            cell_row=allocation_data.cell_row,
            cell_column=allocation_data.cell_column,
            parking_type=allocation_data.parking_type,
            user_id=allocation_data.user_id,
            visitor_name=allocation_data.visitor_name,
            visitor_phone=allocation_data.visitor_phone,
            visitor_company=allocation_data.visitor_company,
            vehicle_number=allocation_data.vehicle_number,
            notes=allocation_data.notes,
            is_active=True
        )
        
        self.db.add(allocation)
        await self.db.commit()
        await self.db.refresh(allocation)
        
        return allocation, None
    
    async def record_entry(
        self,
        allocation_id: UUID,
        timestamp: Optional[datetime] = None
    ) -> Tuple[Optional[ParkingAllocation], Optional[str]]:
        """Record parking entry time."""
        allocation = await self.get_allocation_by_id(allocation_id)
        if not allocation:
            return None, "Allocation not found"
        
        if allocation.entry_time:
            return None, "Entry already recorded"
        
        allocation.entry_time = timestamp or datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(allocation)
        
        return allocation, None
    
    async def record_exit(
        self,
        allocation_id: UUID,
        timestamp: Optional[datetime] = None
    ) -> Tuple[Optional[ParkingAllocation], Optional[str]]:
        """Record parking exit time and create history."""
        allocation = await self.get_allocation_by_id(allocation_id)
        if not allocation:
            return None, "Allocation not found"
        
        if not allocation.entry_time:
            return None, "No entry recorded"
        
        if allocation.exit_time:
            return None, "Exit already recorded"
        
        exit_time = timestamp or datetime.now(timezone.utc)
        allocation.exit_time = exit_time
        allocation.is_active = False
        
        # Calculate duration
        duration = exit_time - allocation.entry_time
        duration_minutes = int(duration.total_seconds() / 60)
        
        # Create history record
        history = ParkingHistory(
            allocation_id=allocation.id,
            floor_plan_id=allocation.floor_plan_id,
            slot_label=allocation.slot_label,
            parking_type=allocation.parking_type,
            user_id=allocation.user_id,
            visitor_name=allocation.visitor_name,
            vehicle_number=allocation.vehicle_number,
            entry_time=allocation.entry_time,
            exit_time=exit_time,
            duration_minutes=str(duration_minutes)
        )
        self.db.add(history)
        
        await self.db.commit()
        await self.db.refresh(allocation)
        
        return allocation, None
    
    async def list_allocations(
        self,
        floor_plan_id: Optional[UUID] = None,
        parking_type: Optional[ParkingType] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[ParkingAllocation], int]:
        """List parking allocations with filtering."""
        query = select(ParkingAllocation)
        count_query = select(func.count(ParkingAllocation.id))
        
        if floor_plan_id:
            query = query.where(ParkingAllocation.floor_plan_id == floor_plan_id)
            count_query = count_query.where(ParkingAllocation.floor_plan_id == floor_plan_id)
        
        if parking_type:
            query = query.where(ParkingAllocation.parking_type == parking_type)
            count_query = count_query.where(ParkingAllocation.parking_type == parking_type)
        
        if is_active is not None:
            query = query.where(ParkingAllocation.is_active == is_active)
            count_query = count_query.where(ParkingAllocation.is_active == is_active)
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        query = query.offset((page - 1) * page_size).limit(page_size)
        query = query.order_by(ParkingAllocation.created_at.desc())
        
        result = await self.db.execute(query)
        allocations = result.scalars().all()
        
        return list(allocations), total
    
    async def get_parking_history(
        self,
        user_id: Optional[UUID] = None,
        floor_plan_id: Optional[UUID] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[ParkingHistory], int]:
        """Get parking history with filtering."""
        query = select(ParkingHistory)
        count_query = select(func.count(ParkingHistory.id))
        
        if user_id:
            query = query.where(ParkingHistory.user_id == user_id)
            count_query = count_query.where(ParkingHistory.user_id == user_id)
        
        if floor_plan_id:
            query = query.where(ParkingHistory.floor_plan_id == floor_plan_id)
            count_query = count_query.where(ParkingHistory.floor_plan_id == floor_plan_id)
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        query = query.offset((page - 1) * page_size).limit(page_size)
        query = query.order_by(ParkingHistory.entry_time.desc())
        
        result = await self.db.execute(query)
        history = result.scalars().all()
        
        return list(history), total
    
    async def get_available_slots(
        self,
        floor_plan_id: UUID
    ) -> List[dict]:
        """Get all available parking slots on a floor."""
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
        
        # Get all occupied slots
        occupied_result = await self.db.execute(
            select(ParkingAllocation.slot_label).where(
                and_(
                    ParkingAllocation.floor_plan_id == floor_plan_id,
                    ParkingAllocation.is_active == True,
                    ParkingAllocation.exit_time.is_(None)
                )
            )
        )
        occupied_slots = set(row[0] for row in occupied_result.fetchall())
        
        # Find available slots from grid
        available = []
        for row_idx, row in enumerate(version.grid_data):
            for col_idx, cell in enumerate(row):
                if cell.get("cell_type") == CellType.PARKING_SLOT.value:
                    label = cell.get("label", f"Slot-{row_idx}-{col_idx}")
                    if label not in occupied_slots:
                        available.append({
                            "row": row_idx,
                            "column": col_idx,
                            "label": label,
                            "direction": cell.get("direction")
                        })
        
        return available