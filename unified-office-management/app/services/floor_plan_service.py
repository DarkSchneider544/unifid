from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from typing import Optional, List, Tuple, Any
from uuid import UUID
import json

from ..models.floor_plan import FloorPlan, FloorPlanVersion
from ..models.building import Building
from ..models.user import User
from ..models.enums import CellType
from ..schemas.floor_plan import FloorPlanCreate, FloorPlanUpdate, FloorPlanVersionCreate


class FloorPlanService:
    """Floor plan management service."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
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
        columns: int
    ) -> Tuple[bool, Optional[str]]:
        """Validate grid data consistency."""
        if len(grid_data) != rows:
            return False, f"Grid must have exactly {rows} rows"
        
        for row_idx, row in enumerate(grid_data):
            if len(row) != columns:
                return False, f"Row {row_idx} must have exactly {columns} columns"
            
            for col_idx, cell in enumerate(row):
                cell_type = cell.get("cell_type")
                if not cell_type:
                    return False, f"Cell at ({row_idx}, {col_idx}) missing cell_type"
                
                try:
                    CellType(cell_type)
                except ValueError:
                    return False, f"Invalid cell_type '{cell_type}' at ({row_idx}, {col_idx})"
        
        return True, None
    
    async def create_floor_plan(
        self,
        floor_plan_data: FloorPlanCreate,
        created_by: User
    ) -> Tuple[Optional[FloorPlan], Optional[str]]:
        """Create a new floor plan with initial version."""
        # Verify building exists
        result = await self.db.execute(
            select(Building).where(Building.id == floor_plan_data.building_id)
        )
        building = result.scalar_one_or_none()
        if not building:
            return None, "Building not found"
        
        # Check for duplicate floor number in building
        existing = await self.db.execute(
            select(FloorPlan).where(
                and_(
                    FloorPlan.building_id == floor_plan_data.building_id,
                    FloorPlan.floor_number == floor_plan_data.floor_number
                )
            )
        )
        if existing.scalar_one_or_none():
            return None, "Floor number already exists in this building"
        
        # Validate grid data
        valid, error = self.validate_grid_data(
            floor_plan_data.grid_data,
            floor_plan_data.rows,
            floor_plan_data.columns
        )
        if not valid:
            return None, error
        
        # Create floor plan
        floor_plan = FloorPlan(
            building_id=floor_plan_data.building_id,
            name=floor_plan_data.name,
            floor_number=floor_plan_data.floor_number,
            rows=floor_plan_data.rows,
            columns=floor_plan_data.columns,
            is_basement=floor_plan_data.is_basement,
            description=floor_plan_data.description,
            current_version=1
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
        
        # Validate grid data
        valid, error = self.validate_grid_data(
            version_data.grid_data,
            floor_plan.rows,
            floor_plan.columns
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
        floor_plan_data: FloorPlanUpdate
    ) -> Tuple[Optional[FloorPlan], Optional[str]]:
        """Update floor plan metadata."""
        floor_plan = await self.get_floor_plan_by_id(floor_plan_id)
        if not floor_plan:
            return None, "Floor plan not found"
        
        update_data = floor_plan_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(floor_plan, field, value)
        
        await self.db.commit()
        await self.db.refresh(floor_plan)
        
        return floor_plan, None
    
    async def clone_floor_plan(
        self,
        source_floor_plan_id: UUID,
        target_building_id: UUID,
        target_floor_number: int,
        new_name: str,
        created_by: User
    ) -> Tuple[Optional[FloorPlan], Optional[str]]:
        """Clone a floor plan to another building/floor."""
        source = await self.get_floor_plan_by_id(source_floor_plan_id)
        if not source:
            return None, "Source floor plan not found"
        
        source_version = await self.get_latest_version(source_floor_plan_id)
        if not source_version:
            return None, "Source floor plan has no versions"
        
        # Check target doesn't exist
        existing = await self.db.execute(
            select(FloorPlan).where(
                and_(
                    FloorPlan.building_id == target_building_id,
                    FloorPlan.floor_number == target_floor_number
                )
            )
        )
        if existing.scalar_one_or_none():
            return None, "Target floor already exists"
        
        # Create clone
        clone = FloorPlan(
            building_id=target_building_id,
            name=new_name,
            floor_number=target_floor_number,
            rows=source.rows,
            columns=source.columns,
            is_basement=source.is_basement,
            description=f"Cloned from {source.name}",
            current_version=1
        )
        self.db.add(clone)
        await self.db.flush()
        
        # Clone version
        version = FloorPlanVersion(
            floor_plan_id=clone.id,
            version=1,
            grid_data=source_version.grid_data,
            is_active=True,
            created_by_id=created_by.id,
            change_notes=f"Cloned from {source.name} version {source_version.version}"
        )
        self.db.add(version)
        
        await self.db.commit()
        await self.db.refresh(clone)
        
        return clone, None
    
    async def list_floor_plans(
        self,
        building_id: Optional[UUID] = None,
        page: int = 1,
        page_size: int = 20,
        is_active: Optional[bool] = None
    ) -> Tuple[List[FloorPlan], int]:
        """List floor plans with filtering."""
        query = select(FloorPlan)
        count_query = select(func.count(FloorPlan.id))
        
        if building_id:
            query = query.where(FloorPlan.building_id == building_id)
            count_query = count_query.where(FloorPlan.building_id == building_id)
        
        if is_active is not None:
            query = query.where(FloorPlan.is_active == is_active)
            count_query = count_query.where(FloorPlan.is_active == is_active)
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        query = query.offset((page - 1) * page_size).limit(page_size)
        query = query.order_by(FloorPlan.floor_number)
        
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