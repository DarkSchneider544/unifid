from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from typing import Optional, List, Tuple, Any
from uuid import UUID

from ..models.floor_plan import FloorPlan, FloorPlanVersion
from ..models.user import User
from ..models.enums import CellType, FloorPlanType, ManagerType, UserRole
from ..schemas.floor_plan import FloorPlanCreate, FloorPlanUpdate, FloorPlanVersionCreate


# Mapping between FloorPlanType and ManagerType
PLAN_TYPE_TO_MANAGER_TYPE = {
    FloorPlanType.DESK_AREA: ManagerType.DESK_CONFERENCE,
    FloorPlanType.CAFETERIA: ManagerType.CAFETERIA,
    FloorPlanType.PARKING: ManagerType.PARKING,
}

# Valid cell types for each floor plan type
VALID_CELL_TYPES = {
    FloorPlanType.DESK_AREA: [CellType.DESK, CellType.PATH, CellType.WALL, CellType.ENTRY, CellType.EXIT, CellType.EMPTY],
    FloorPlanType.CAFETERIA: [CellType.CAFETERIA_TABLE, CellType.PATH, CellType.WALL, CellType.ENTRY, CellType.EXIT, CellType.EMPTY],
    FloorPlanType.PARKING: [CellType.PARKING_SLOT, CellType.PATH, CellType.WALL, CellType.ENTRY, CellType.EXIT, CellType.EMPTY],
}


class FloorPlanService:
    """
    Floor plan management service with manager type access control.
    
    Access Control:
    - SUPER_ADMIN: Can manage all floor plan types
    - ADMIN: Can manage all floor plan types
    - DESK_CONFERENCE Manager: Can only manage DESK_AREA floor plans
    - CAFETERIA Manager: Can only manage CAFETERIA floor plans
    - PARKING Manager: Can only manage PARKING floor plans
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    def can_manage_plan_type(self, user: User, plan_type: FloorPlanType) -> bool:
        """Check if user can manage a specific floor plan type."""
        if user.role == UserRole.SUPER_ADMIN:
            return True
        
        if user.role == UserRole.ADMIN:
            return True  # Admins can manage all floor plans
        
        if user.role != UserRole.MANAGER or not user.manager_type:
            return False
        
        required_manager_type = PLAN_TYPE_TO_MANAGER_TYPE.get(plan_type)
        return user.manager_type == required_manager_type
    
    async def get_floor_plan_by_id(
        self, 
        floor_plan_id: UUID,
        include_versions: bool = False
    ) -> Optional[FloorPlan]:
        """Get floor plan by ID."""
        query = select(FloorPlan).where(FloorPlan.id == floor_plan_id)
        if include_versions:
            query = query.options(selectinload(FloorPlan.versions))
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_latest_version(
        self,
        floor_plan_id: UUID
    ) -> Optional[FloorPlanVersion]:
        """Get the latest version of a floor plan."""
        result = await self.db.execute(
            select(FloorPlanVersion)
            .where(FloorPlanVersion.floor_plan_id == floor_plan_id)
            .order_by(FloorPlanVersion.version.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    async def get_version(
        self,
        floor_plan_id: UUID,
        version: int
    ) -> Optional[FloorPlanVersion]:
        """Get a specific version of a floor plan."""
        result = await self.db.execute(
            select(FloorPlanVersion)
            .where(
                and_(
                    FloorPlanVersion.floor_plan_id == floor_plan_id,
                    FloorPlanVersion.version == version
                )
            )
        )
        return result.scalar_one_or_none()
    
    def validate_grid_data(
        self,
        grid_data: List[List[dict]],
        rows: int,
        columns: int,
        plan_type: FloorPlanType
    ) -> Tuple[bool, Optional[str]]:
        """Validate grid data consistency and cell types for plan type."""
        if len(grid_data) != rows:
            return False, f"Grid must have exactly {rows} rows"
        
        valid_types = VALID_CELL_TYPES.get(plan_type, [])
        valid_type_values = [ct.value for ct in valid_types]
        
        for row_idx, row in enumerate(grid_data):
            if len(row) != columns:
                return False, f"Row {row_idx} must have exactly {columns} columns"
            
            for col_idx, cell in enumerate(row):
                cell_type = cell.get("cell_type")
                if not cell_type:
                    return False, f"Cell at ({row_idx}, {col_idx}) missing cell_type"
                
                # Validate cell type is valid for this plan type
                if cell_type not in valid_type_values:
                    return False, f"Invalid cell_type '{cell_type}' for {plan_type.value} plan at ({row_idx}, {col_idx}). Valid types: {valid_type_values}"
        
        return True, None
    
    async def create_floor_plan(
        self,
        floor_plan_data: FloorPlanCreate,
        created_by: User
    ) -> Tuple[Optional[FloorPlan], Optional[str]]:
        """Create a new floor plan with initial version."""
        # Check access control
        if not self.can_manage_plan_type(created_by, floor_plan_data.plan_type):
            return None, f"You don't have permission to create {floor_plan_data.plan_type.value} floor plans"
        
        # Check for duplicate name with same type
        existing = await self.db.execute(
            select(FloorPlan).where(
                and_(
                    FloorPlan.name == floor_plan_data.name,
                    FloorPlan.plan_type == floor_plan_data.plan_type
                )
            )
        )
        if existing.scalar_one_or_none():
            return None, f"A {floor_plan_data.plan_type.value} floor plan with this name already exists"
        
        # Validate grid data
        valid, error = self.validate_grid_data(
            floor_plan_data.grid_data,
            floor_plan_data.rows,
            floor_plan_data.columns,
            floor_plan_data.plan_type
        )
        if not valid:
            return None, error
        
        # Create floor plan
        floor_plan = FloorPlan(
            name=floor_plan_data.name,
            plan_type=floor_plan_data.plan_type,
            rows=floor_plan_data.rows,
            columns=floor_plan_data.columns,
            description=floor_plan_data.description,
            current_version=1,
            created_by_id=created_by.id
        )
        self.db.add(floor_plan)
        await self.db.flush()
        
        # Create initial version
        version = FloorPlanVersion(
            floor_plan_id=floor_plan.id,
            version=1,
            grid_data=floor_plan_data.grid_data,
            is_active=True,
            created_by_id=created_by.id,
            change_notes="Initial version"
        )
        self.db.add(version)
        
        await self.db.commit()
        await self.db.refresh(floor_plan)
        
        return floor_plan, None
    
    async def create_version(
        self,
        floor_plan_id: UUID,
        version_data: FloorPlanVersionCreate,
        created_by: User
    ) -> Tuple[Optional[FloorPlanVersion], Optional[str]]:
        """Create a new version of a floor plan."""
        floor_plan = await self.get_floor_plan_by_id(floor_plan_id)
        if not floor_plan:
            return None, "Floor plan not found"
        
        # Check access control
        if not self.can_manage_plan_type(created_by, floor_plan.plan_type):
            return None, f"You don't have permission to modify {floor_plan.plan_type.value} floor plans"
        
        # Validate grid data
        valid, error = self.validate_grid_data(
            version_data.grid_data,
            floor_plan.rows,
            floor_plan.columns,
            floor_plan.plan_type
        )
        if not valid:
            return None, error
        
        # Get next version number
        new_version_num = floor_plan.current_version + 1
        
        # Create new version
        version = FloorPlanVersion(
            floor_plan_id=floor_plan_id,
            version=new_version_num,
            grid_data=version_data.grid_data,
            is_active=True,
            created_by_id=created_by.id,
            change_notes=version_data.change_notes
        )
        self.db.add(version)
        
        # Update floor plan current version
        floor_plan.current_version = new_version_num
        
        await self.db.commit()
        await self.db.refresh(version)
        
        return version, None
    
    async def update_floor_plan(
        self,
        floor_plan_id: UUID,
        floor_plan_data: FloorPlanUpdate,
        updated_by: User
    ) -> Tuple[Optional[FloorPlan], Optional[str]]:
        """Update floor plan metadata."""
        floor_plan = await self.get_floor_plan_by_id(floor_plan_id)
        if not floor_plan:
            return None, "Floor plan not found"
        
        # Check access control
        if not self.can_manage_plan_type(updated_by, floor_plan.plan_type):
            return None, f"You don't have permission to modify {floor_plan.plan_type.value} floor plans"
        
        update_data = floor_plan_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(floor_plan, field, value)
        
        await self.db.commit()
        await self.db.refresh(floor_plan)
        
        return floor_plan, None
    
    async def list_floor_plans(
        self,
        plan_type: Optional[FloorPlanType] = None,
        page: int = 1,
        page_size: int = 20,
        is_active: Optional[bool] = None,
        requesting_user: Optional[User] = None
    ) -> Tuple[List[FloorPlan], int]:
        """
        List floor plans with filtering.
        
        Access Control:
        - SUPER_ADMIN: See all
        - ADMIN: See all
        - Specific Manager: Only see floor plans of their type
        - Others: See all active floor plans (read-only)
        """
        query = select(FloorPlan)
        count_query = select(func.count(FloorPlan.id))
        
        # Filter by manager type access
        if requesting_user and requesting_user.role == UserRole.MANAGER:
            if requesting_user.manager_type:
                # Get plan type for this manager
                for pt, mt in PLAN_TYPE_TO_MANAGER_TYPE.items():
                    if mt == requesting_user.manager_type:
                        query = query.where(FloorPlan.plan_type == pt)
                        count_query = count_query.where(FloorPlan.plan_type == pt)
                        break
        
        if plan_type:
            query = query.where(FloorPlan.plan_type == plan_type)
            count_query = count_query.where(FloorPlan.plan_type == plan_type)
        
        if is_active is not None:
            query = query.where(FloorPlan.is_active == is_active)
            count_query = count_query.where(FloorPlan.is_active == is_active)
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        query = query.offset((page - 1) * page_size).limit(page_size)
        query = query.order_by(FloorPlan.name)
        
        result = await self.db.execute(query)
        floor_plans = result.scalars().all()
        
        return list(floor_plans), total
    
    async def list_versions(
        self,
        floor_plan_id: UUID
    ) -> List[FloorPlanVersion]:
        """List all versions of a floor plan."""
        result = await self.db.execute(
            select(FloorPlanVersion)
            .where(FloorPlanVersion.floor_plan_id == floor_plan_id)
            .order_by(FloorPlanVersion.version.desc())
        )
        return list(result.scalars().all())
    
    async def get_cells_by_type(
        self,
        floor_plan_id: UUID,
        cell_type: CellType
    ) -> List[dict]:
        """Get all cells of a specific type from latest version."""
        version = await self.get_latest_version(floor_plan_id)
        if not version:
            return []
        
        cells = []
        for row_idx, row in enumerate(version.grid_data):
            for col_idx, cell in enumerate(row):
                if cell.get("cell_type") == cell_type.value:
                    cells.append({
                        "row": row_idx,
                        "column": col_idx,
                        **cell
                    })
        
        return cells
    
    async def get_available_slots(
        self,
        floor_plan_id: UUID,
        slot_type: CellType
    ) -> List[dict]:
        """Get all available (unoccupied) slots of a specific type."""
        version = await self.get_latest_version(floor_plan_id)
        if not version:
            return []
        
        slots = []
        for row_idx, row in enumerate(version.grid_data):
            for col_idx, cell in enumerate(row):
                if cell.get("cell_type") == slot_type.value:
                    if cell.get("is_active", True) and not cell.get("is_occupied", False):
                        slots.append({
                            "row": row_idx,
                            "column": col_idx,
                            "label": cell.get("label"),
                            **cell
                        })
        
        return slots
    
    async def delete_floor_plan(
        self,
        floor_plan_id: UUID,
        deleted_by: User
    ) -> Tuple[bool, Optional[str]]:
        """Soft delete a floor plan (set is_active to False)."""
        floor_plan = await self.get_floor_plan_by_id(floor_plan_id)
        if not floor_plan:
            return False, "Floor plan not found"
        
        # Check access control
        if not self.can_manage_plan_type(deleted_by, floor_plan.plan_type):
            return False, f"You don't have permission to delete {floor_plan.plan_type.value} floor plans"
        
        floor_plan.is_active = False
        await self.db.commit()
        
        return True, None
