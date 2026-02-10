from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from typing import Optional, List, Tuple
from uuid import UUID
from datetime import date, datetime, timezone, timedelta

from ..models.holiday import Holiday
from ..models.user import User
from ..models.enums import UserRole
from ..schemas.holiday import HolidayCreate, HolidayUpdate


class HolidayService:
    """Holiday management service - Super Admin only."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    def is_super_admin(self, user: User) -> bool:
        """Check if user is Super Admin."""
        return user.role == UserRole.SUPER_ADMIN
    
    async def get_holiday_by_id(
        self,
        holiday_id: UUID
    ) -> Optional[Holiday]:
        """Get holiday by ID with relationships."""
        result = await self.db.execute(
            select(Holiday)
            .where(Holiday.id == holiday_id)
            .options(selectinload(Holiday.created_by))
        )
        return result.scalar_one_or_none()
    
    async def get_holiday_by_date(
        self,
        holiday_date: date
    ) -> Optional[Holiday]:
        """Get holiday by date."""
        result = await self.db.execute(
            select(Holiday).where(Holiday.date == holiday_date)
        )
        return result.scalar_one_or_none()
    
    async def create_holiday(
        self,
        holiday_data: HolidayCreate,
        created_by: User
    ) -> Tuple[Optional[Holiday], Optional[str]]:
        """Create a new holiday. Super Admin only."""
        if not self.is_super_admin(created_by):
            return None, "Only Super Admin can create holidays"
        
        # Check if holiday already exists for this date
        existing = await self.get_holiday_by_date(holiday_data.date)
        if existing:
            return None, f"A holiday already exists on {holiday_data.date}"
        
        holiday = Holiday(
            name=holiday_data.name,
            description=holiday_data.description,
            date=holiday_data.date,
            holiday_type=holiday_data.holiday_type,
            is_optional=holiday_data.is_optional,
            is_active=True,
            created_by_code=created_by.user_code
        )
        
        self.db.add(holiday)
        await self.db.commit()
        
        # Reload with relationships
        holiday = await self.get_holiday_by_id(holiday.id)
        
        return holiday, None
    
    async def update_holiday(
        self,
        holiday_id: UUID,
        holiday_data: HolidayUpdate,
        user: User
    ) -> Tuple[Optional[Holiday], Optional[str]]:
        """Update a holiday. Super Admin only."""
        if not self.is_super_admin(user):
            return None, "Only Super Admin can update holidays"
        
        holiday = await self.get_holiday_by_id(holiday_id)
        if not holiday:
            return None, "Holiday not found"
        
        # Check if new date conflicts with existing holiday
        if holiday_data.date and holiday_data.date != holiday.date:
            existing = await self.get_holiday_by_date(holiday_data.date)
            if existing:
                return None, f"A holiday already exists on {holiday_data.date}"
        
        update_data = holiday_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(holiday, field, value)
        
        await self.db.commit()
        
        # Reload with relationships
        holiday = await self.get_holiday_by_id(holiday_id)
        
        return holiday, None
    
    async def delete_holiday(
        self,
        holiday_id: UUID,
        user: User
    ) -> Tuple[bool, Optional[str]]:
        """Delete a holiday. Super Admin only."""
        if not self.is_super_admin(user):
            return False, "Only Super Admin can delete holidays"
        
        holiday = await self.get_holiday_by_id(holiday_id)
        if not holiday:
            return False, "Holiday not found"
        
        # Soft delete by setting is_active to False
        holiday.is_active = False
        await self.db.commit()
        
        return True, None
    
    async def list_holidays(
        self,
        upcoming_only: bool = True,
        include_inactive: bool = False,
        year: Optional[int] = None,
        page: int = 1,
        page_size: int = 50
    ) -> Tuple[List[Holiday], int]:
        """List holidays with filtering."""
        query = select(Holiday).options(selectinload(Holiday.created_by))
        count_query = select(func.count(Holiday.id))
        
        # Filter by active status
        if not include_inactive:
            query = query.where(Holiday.is_active == True)
            count_query = count_query.where(Holiday.is_active == True)
        
        # Filter upcoming holidays
        if upcoming_only:
            today = date.today()
            query = query.where(Holiday.date >= today)
            count_query = count_query.where(Holiday.date >= today)
        
        # Filter by year
        if year:
            query = query.where(func.extract('year', Holiday.date) == year)
            count_query = count_query.where(func.extract('year', Holiday.date) == year)
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        query = query.offset((page - 1) * page_size).limit(page_size)
        query = query.order_by(Holiday.date.asc())
        
        result = await self.db.execute(query)
        holidays = result.scalars().all()
        
        return list(holidays), total
    
    async def get_upcoming_holidays(
        self,
        days_ahead: int = 30
    ) -> List[Holiday]:
        """Get holidays in the next N days."""
        today = date.today()
        end_date = today + timedelta(days=days_ahead)
        
        result = await self.db.execute(
            select(Holiday)
            .where(
                and_(
                    Holiday.is_active == True,
                    Holiday.date >= today,
                    Holiday.date <= end_date
                )
            )
            .options(selectinload(Holiday.created_by))
            .order_by(Holiday.date.asc())
        )
        
        return list(result.scalars().all())
