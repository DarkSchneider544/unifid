from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List, Tuple
from uuid import UUID

from ..models.building import Building
from ..schemas.building import BuildingCreate, BuildingUpdate


class BuildingService:
    """Building management service."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_building_by_id(self, building_id: UUID) -> Optional[Building]:
        """Get building by ID."""
        result = await self.db.execute(
            select(Building).where(Building.id == building_id)
        )
        return result.scalar_one_or_none()
    
    async def get_building_by_code(self, code: str) -> Optional[Building]:
        """Get building by code."""
        result = await self.db.execute(
            select(Building).where(Building.code == code)
        )
        return result.scalar_one_or_none()
    
    async def create_building(
        self,
        building_data: BuildingCreate
    ) -> Tuple[Optional[Building], Optional[str]]:
        """Create a new building."""
        # Check for duplicate code
        existing = await self.get_building_by_code(building_data.code)
        if existing:
            return None, "Building code already exists"
        
        building = Building(**building_data.model_dump())
        self.db.add(building)
        await self.db.commit()
        await self.db.refresh(building)
        
        return building, None
    
    async def update_building(
        self,
        building_id: UUID,
        building_data: BuildingUpdate
    ) -> Tuple[Optional[Building], Optional[str]]:
        """Update building details."""
        building = await self.get_building_by_id(building_id)
        if not building:
            return None, "Building not found"
        
        update_data = building_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(building, field, value)
        
        await self.db.commit()
        await self.db.refresh(building)
        
        return building, None
    
    async def list_buildings(
        self,
        page: int = 1,
        page_size: int = 20,
        is_active: Optional[bool] = None
    ) -> Tuple[List[Building], int]:
        """List buildings with pagination."""
        query = select(Building)
        count_query = select(func.count(Building.id))
        
        if is_active is not None:
            query = query.where(Building.is_active == is_active)
            count_query = count_query.where(Building.is_active == is_active)
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        query = query.offset((page - 1) * page_size).limit(page_size)
        query = query.order_by(Building.name)
        
        result = await self.db.execute(query)
        buildings = result.scalars().all()
        
        return list(buildings), total
    
    async def delete_building(
        self,
        building_id: UUID
    ) -> Tuple[bool, Optional[str]]:
        """Deactivate a building."""
        building = await self.get_building_by_id(building_id)
        if not building:
            return False, "Building not found"
        
        building.is_active = False
        await self.db.commit()
        
        return True, None