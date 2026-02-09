from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from typing import Optional, List, Tuple
from uuid import UUID

from ..models.user import User
from ..models.enums import UserRole, ManagerDomain
from ..schemas.user import UserCreate, UserUpdate
from ..core.security import get_password_hash
from ..core.config import settings


class UserService:
    """User management service."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID."""
        result = await self.db.execute(
            select(User).where(
                User.id == user_id,
                User.is_deleted == False
            )
        )
        return result.scalar_one_or_none()
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        result = await self.db.execute(
            select(User).where(
                User.email == email,
                User.is_deleted == False
            )
        )
        return result.scalar_one_or_none()
    
    async def get_user_by_employee_id(self, employee_id: str) -> Optional[User]:
        """Get user by employee ID."""
        result = await self.db.execute(
            select(User).where(
                User.employee_id == employee_id,
                User.is_deleted == False
            )
        )
        return result.scalar_one_or_none()
    
    async def create_user(
        self,
        user_data: UserCreate,
        created_by: User
    ) -> Tuple[Optional[User], Optional[str]]:
        """Create a new user with role-based validation."""
        
        # Validate permissions based on creator's role
        if created_by.role == UserRole.SUPER_ADMIN:
            # Super Admin can create Admins
            if user_data.role not in [UserRole.ADMIN, UserRole.MANAGER, 
                                       UserRole.TEAM_LEAD, UserRole.EMPLOYEE]:
                return None, "Super Admin cannot create Super Admin users"
        elif created_by.role == UserRole.ADMIN:
            # Admin can create Managers and Employees
            if user_data.role not in [UserRole.MANAGER, UserRole.TEAM_LEAD, 
                                       UserRole.EMPLOYEE]:
                return None, "Admin can only create Managers and Employees"
        else:
            return None, "Insufficient permissions to create users"
        
        # Generate email if not provided
        if not user_data.email:
            email = f"{user_data.first_name.lower()}.{user_data.last_name.lower()}@{settings.COMPANY_DOMAIN}"
        else:
            email = user_data.email
        
        # Check for duplicates
        existing_email = await self.get_user_by_email(email)
        if existing_email:
            return None, "Email already exists"
        
        existing_employee = await self.get_user_by_employee_id(user_data.employee_id)
        if existing_employee:
            return None, "Employee ID already exists"
        
        # Create user
        new_user = User(
            employee_id=user_data.employee_id,
            email=email,
            hashed_password=get_password_hash(user_data.password),
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            role=user_data.role,
            manager_domain=user_data.manager_domain if user_data.role == UserRole.MANAGER else None,
            is_team_lead=user_data.is_team_lead,
            department=user_data.department,
            phone=user_data.phone,
            team_lead_id=user_data.team_lead_id,
            manager_id=user_data.manager_id
        )
        
        self.db.add(new_user)
        await self.db.commit()
        await self.db.refresh(new_user)
        
        return new_user, None
    
    async def update_user(
        self,
        user_id: UUID,
        user_data: UserUpdate,
        updated_by: User
    ) -> Tuple[Optional[User], Optional[str]]:
        """Update user details."""
        user = await self.get_user_by_id(user_id)
        if not user:
            return None, "User not found"
        
        # Validate permissions
        if updated_by.role == UserRole.SUPER_ADMIN:
            pass  # Can update any user
        elif updated_by.role == UserRole.ADMIN:
            if user.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
                return None, "Cannot update Admin or Super Admin users"
        else:
            if str(user.id) != str(updated_by.id):
                return None, "Can only update your own profile"
        
        # Update fields
        update_data = user_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(user, field):
                setattr(user, field, value)
        
        await self.db.commit()
        await self.db.refresh(user)
        
        return user, None
    
    async def soft_delete_user(
        self,
        user_id: UUID,
        deleted_by: User
    ) -> Tuple[bool, Optional[str]]:
        """Soft delete a user."""
        user = await self.get_user_by_id(user_id)
        if not user:
            return False, "User not found"
        
        # Validate permissions
        if deleted_by.role == UserRole.SUPER_ADMIN:
            if user.role == UserRole.SUPER_ADMIN:
                return False, "Cannot delete Super Admin"
        elif deleted_by.role == UserRole.ADMIN:
            if user.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
                return False, "Cannot delete Admin or Super Admin"
        else:
            return False, "Insufficient permissions"
        
        user.is_deleted = True
        user.is_active = False
        await self.db.commit()
        
        return True, None
    
    async def list_users(
        self,
        page: int = 1,
        page_size: int = 20,
        role: Optional[UserRole] = None,
        department: Optional[str] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None
    ) -> Tuple[List[User], int]:
        """List users with filtering and pagination."""
        query = select(User).where(User.is_deleted == False)
        count_query = select(func.count(User.id)).where(User.is_deleted == False)
        
        # Apply filters
        if role:
            query = query.where(User.role == role)
            count_query = count_query.where(User.role == role)
        
        if department:
            query = query.where(User.department == department)
            count_query = count_query.where(User.department == department)
        
        if is_active is not None:
            query = query.where(User.is_active == is_active)
            count_query = count_query.where(User.is_active == is_active)
        
        if search:
            search_filter = or_(
                User.first_name.ilike(f"%{search}%"),
                User.last_name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
                User.employee_id.ilike(f"%{search}%")
            )
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)
        
        # Get total count
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination
        query = query.offset((page - 1) * page_size).limit(page_size)
        query = query.order_by(User.created_at.desc())
        
        result = await self.db.execute(query)
        users = result.scalars().all()
        
        return list(users), total
    
    async def get_team_members(
        self,
        team_lead_id: UUID
    ) -> List[User]:
        """Get team members for a team lead."""
        result = await self.db.execute(
            select(User).where(
                User.team_lead_id == team_lead_id,
                User.is_deleted == False,
                User.is_active == True
            )
        )
        return list(result.scalars().all())
    
    async def promote_to_team_lead(
        self,
        user_id: UUID,
        promoted_by: User
    ) -> Tuple[Optional[User], Optional[str]]:
        """Promote an employee to team lead."""
        user = await self.get_user_by_id(user_id)
        if not user:
            return None, "User not found"
        
        if user.role != UserRole.EMPLOYEE:
            return None, "Only employees can be promoted to team lead"
        
        user.is_team_lead = True
        user.role = UserRole.TEAM_LEAD
        
        await self.db.commit()
        await self.db.refresh(user)
        
        return user, None