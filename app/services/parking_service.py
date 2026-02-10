from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Optional, List, Tuple
from uuid import UUID
from datetime import datetime, timezone
import re

from ..models.parking import ParkingAllocation, ParkingHistory
from ..models.floor_plan import FloorPlan, FloorPlanVersion
from ..models.user import User
from ..models.enums import CellType, ParkingType, FloorPlanType, UserRole, ManagerType
from ..schemas.parking import ParkingAllocationCreate, ParkingAllocationUpdate, VisitorParkingCreate


class ParkingService:
    """Parking management service - managed by Parking Manager."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    def can_manage_parking(self, user: User) -> bool:
        """Check if user can manage parking allocations."""
        if user.role == UserRole.SUPER_ADMIN:
            return True
        if user.role == UserRole.ADMIN:
            return True
        if user.role == UserRole.MANAGER and user.manager_type == ManagerType.PARKING:
            return True
        return False
    
    async def get_allocation_by_id(
        self,
        allocation_id: UUID
    ) -> Optional[ParkingAllocation]:
        """Get parking allocation by ID."""
        result = await self.db.execute(
            select(ParkingAllocation).where(ParkingAllocation.id == allocation_id)
        )
        return result.scalar_one_or_none()
    
    async def get_parking_floor_plans(self) -> List[FloorPlan]:
        """Get all active parking floor plans."""
        result = await self.db.execute(
            select(FloorPlan).where(
                and_(
                    FloorPlan.plan_type == FloorPlanType.PARKING,
                    FloorPlan.is_active == True
                )
            )
        )
        return list(result.scalars().all())
    
    async def validate_parking_slot(
        self,
        floor_plan_id: UUID,
        cell_row: str,
        cell_column: str
    ) -> Tuple[bool, Optional[str]]:
        """Validate that the cell is a valid parking slot."""
        # Validate row and column are numeric
        if not cell_row.isdigit() or not cell_column.isdigit():
            return False, "Cell row and column must be numeric"
        
        # Get floor plan first
        floor_plan_result = await self.db.execute(
            select(FloorPlan).where(FloorPlan.id == floor_plan_id)
        )
        floor_plan = floor_plan_result.scalar_one_or_none()
        
        if not floor_plan:
            return False, "Floor plan not found"
        
        if floor_plan.plan_type != FloorPlanType.PARKING:
            return False, "Floor plan is not a parking layout"
        
        # Get latest floor plan version
        result = await self.db.execute(
            select(FloorPlanVersion)
            .where(FloorPlanVersion.floor_plan_id == floor_plan_id)
            .order_by(FloorPlanVersion.version.desc())
            .limit(1)
        )
        version = result.scalar_one_or_none()
        
        if not version:
            return False, "Floor plan version not found"
        
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
    
    async def get_available_slots(
        self,
        floor_plan_id: UUID
    ) -> List[dict]:
        """Get all available parking slots on a floor."""
        # Validate floor plan is a parking type
        floor_plan_result = await self.db.execute(
            select(FloorPlan).where(FloorPlan.id == floor_plan_id)
        )
        floor_plan = floor_plan_result.scalar_one_or_none()
        
        if not floor_plan or floor_plan.plan_type != FloorPlanType.PARKING:
            return []
        
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
    
    async def assign_visitor_slot(
        self,
        visitor_data: 'VisitorParkingCreate',
        assigned_by: User
    ) -> Tuple[Optional[ParkingAllocation], Optional[str]]:
        """
        Assign a parking slot to a visitor - Security Admin only.
        Automatically finds an available slot if not specified.
        """
        # Validate permissions
        if not self.can_manage_parking(assigned_by):
            return None, "Only Security Admin can assign visitor parking"
        
        # Validate visitor information
        if not visitor_data.visitor_name or len(visitor_data.visitor_name.strip()) < 2:
            return None, "Visitor name is required (minimum 2 characters)"
        
        # Validate phone format if provided
        if visitor_data.visitor_phone:
            phone_pattern = r'^\+?[\d\s-]{10,15}$'
            if not re.match(phone_pattern, visitor_data.visitor_phone):
                return None, "Invalid phone number format"
        
        # Get parking floor plans
        floor_plans = await self.get_parking_floor_plans()
        if not floor_plans:
            return None, "No parking floor plans available"
        
        # Find an available slot
        slot_info = None
        target_floor_plan = None
        
        if visitor_data.floor_plan_id and visitor_data.slot_label:
            # Specific slot requested
            target_floor_plan_result = await self.db.execute(
                select(FloorPlan).where(
                    and_(
                        FloorPlan.id == visitor_data.floor_plan_id,
                        FloorPlan.plan_type == FloorPlanType.PARKING
                    )
                )
            )
            target_floor_plan = target_floor_plan_result.scalar_one_or_none()
            
            if not target_floor_plan:
                return None, "Invalid parking floor plan"
            
            if not await self.check_slot_availability(
                visitor_data.floor_plan_id, 
                visitor_data.slot_label
            ):
                return None, "Requested slot is not available"
            
            # Find slot coordinates from grid
            version_result = await self.db.execute(
                select(FloorPlanVersion)
                .where(FloorPlanVersion.floor_plan_id == visitor_data.floor_plan_id)
                .order_by(FloorPlanVersion.version.desc())
                .limit(1)
            )
            version = version_result.scalar_one_or_none()
            
            if version:
                for row_idx, row in enumerate(version.grid_data):
                    for col_idx, cell in enumerate(row):
                        if cell.get("label") == visitor_data.slot_label:
                            slot_info = {
                                "row": row_idx,
                                "column": col_idx,
                                "label": visitor_data.slot_label
                            }
                            break
                    if slot_info:
                        break
            
            if not slot_info:
                return None, "Slot not found in floor plan grid"
        else:
            # Auto-assign available slot
            for fp in floor_plans:
                available = await self.get_available_slots(fp.id)
                if available:
                    slot_info = available[0]  # Take first available
                    target_floor_plan = fp
                    break
            
            if not slot_info:
                return None, "No parking slots available"
        
        # Create the allocation
        allocation = ParkingAllocation(
            floor_plan_id=target_floor_plan.id,
            slot_label=slot_info["label"],
            cell_row=str(slot_info["row"]),
            cell_column=str(slot_info["column"]),
            parking_type=ParkingType.VISITOR,
            visitor_name=visitor_data.visitor_name.strip(),
            visitor_phone=visitor_data.visitor_phone,
            visitor_company=visitor_data.visitor_company,
            vehicle_number=visitor_data.vehicle_number,
            notes=visitor_data.notes,
            is_active=True,
            entry_time=datetime.now(timezone.utc)  # Auto-record entry
        )
        
        self.db.add(allocation)
        await self.db.commit()
        await self.db.refresh(allocation)
        
        return allocation, None
    
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
        
        # For visitor parking, validate visitor info (Security Admin only)
        if allocation_data.parking_type == ParkingType.VISITOR:
            if not self.can_manage_parking(created_by):
                return None, "Only Security Admin can allocate visitor parking"
            
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
        recorded_by: User,
        timestamp: Optional[datetime] = None
    ) -> Tuple[Optional[ParkingAllocation], Optional[str]]:
        """Record parking exit time and create history."""
        allocation = await self.get_allocation_by_id(allocation_id)
        if not allocation:
            return None, "Allocation not found"
        
        # For visitor exits, only security admin can record
        if allocation.parking_type == ParkingType.VISITOR:
            if not self.can_manage_parking(recorded_by):
                return None, "Only Security Admin can record visitor exits"
        
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
    
    async def list_visitor_allocations(
        self,
        is_active: Optional[bool] = True,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[ParkingAllocation], int]:
        """List visitor parking allocations - for Security Admin dashboard."""
        return await self.list_allocations(
            parking_type=ParkingType.VISITOR,
            is_active=is_active,
            page=page,
            page_size=page_size
        )
    
    async def get_parking_history(
        self,
        user_id: Optional[UUID] = None,
        floor_plan_id: Optional[UUID] = None,
        parking_type: Optional[ParkingType] = None,
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
        
        if parking_type:
            query = query.where(ParkingHistory.parking_type == parking_type)
            count_query = count_query.where(ParkingHistory.parking_type == parking_type)
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        query = query.offset((page - 1) * page_size).limit(page_size)
        query = query.order_by(ParkingHistory.entry_time.desc())
        
        result = await self.db.execute(query)
        history = result.scalars().all()
        
        return list(history), total
    
    async def get_parking_stats(
        self,
        floor_plan_id: Optional[UUID] = None
    ) -> dict:
        """Get parking statistics for dashboard."""
        # Total slots - from floor plan grids
        floor_plans = await self.get_parking_floor_plans()
        
        total_slots = 0
        occupied_slots = 0
        visitor_count = 0
        employee_count = 0
        
        for fp in floor_plans:
            if floor_plan_id and fp.id != floor_plan_id:
                continue
            
            # Count slots from grid
            version_result = await self.db.execute(
                select(FloorPlanVersion)
                .where(FloorPlanVersion.floor_plan_id == fp.id)
                .order_by(FloorPlanVersion.version.desc())
                .limit(1)
            )
            version = version_result.scalar_one_or_none()
            
            if version:
                for row in version.grid_data:
                    for cell in row:
                        if cell.get("cell_type") == CellType.PARKING_SLOT.value:
                            total_slots += 1
        
        # Count occupied
        occupied_query = select(func.count(ParkingAllocation.id)).where(
            and_(
                ParkingAllocation.is_active == True,
                ParkingAllocation.exit_time.is_(None)
            )
        )
        
        if floor_plan_id:
            occupied_query = occupied_query.where(
                ParkingAllocation.floor_plan_id == floor_plan_id
            )
        
        result = await self.db.execute(occupied_query)
        occupied_slots = result.scalar() or 0
        
        # Count by type
        for ptype in [ParkingType.VISITOR, ParkingType.EMPLOYEE]:
            count_query = select(func.count(ParkingAllocation.id)).where(
                and_(
                    ParkingAllocation.is_active == True,
                    ParkingAllocation.exit_time.is_(None),
                    ParkingAllocation.parking_type == ptype
                )
            )
            if floor_plan_id:
                count_query = count_query.where(
                    ParkingAllocation.floor_plan_id == floor_plan_id
                )
            
            result = await self.db.execute(count_query)
            count = result.scalar() or 0
            
            if ptype == ParkingType.VISITOR:
                visitor_count = count
            else:
                employee_count = count
        
        return {
            "total_slots": total_slots,
            "occupied_slots": occupied_slots,
            "available_slots": total_slots - occupied_slots,
            "visitor_count": visitor_count,
            "employee_count": employee_count,
            "occupancy_rate": round((occupied_slots / total_slots * 100), 2) if total_slots > 0 else 0
        }
