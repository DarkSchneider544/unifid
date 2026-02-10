from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from typing import Optional, List, Tuple
from uuid import UUID

from ..models.user import User
from ..models.enums import UserRole, ManagerType
from ..schemas.user import UserCreate, UserUpdate
from ..core.security import get_password_hash
from ..core.config import settings


class UserService:
    """
    User management service with hierarchical role-based access control.
    
    Hierarchy (who creates whom):
    ┌─────────────────────────────────────────────────────────────────┐
    │  SUPER_ADMIN                                                     │
    │       │ creates                                                  │
    │       ▼                                                          │
    │    ADMIN                                                         │
    │       │ creates                                                  │
    │       ▼                                                          │
    │  MANAGER (5 types):                                              │
    │    - Parking Manager                                             │
    │    - Attendance Manager -> creates Team Leads & Employees        │
    │    - Desk & Conference Manager                                   │
    │    - Cafeteria Manager                                           │
    │    - IT Support Manager                                          │
    │       │                                                          │
    │       ▼                                                          │
    │  TEAM_LEAD (Department-wise: Dev, Sales, AI, etc.)               │
    │       │ manages                                                  │
    │       ▼                                                          │
    │  EMPLOYEE (emp1, emp2, emp3...)                                  │
    └─────────────────────────────────────────────────────────────────┘
    
    Approval Flow:
    - EMPLOYEE -> TEAM_LEAD approves
    - TEAM_LEAD -> MANAGER approves
    - MANAGER -> ADMIN approves
    - ADMIN -> SUPER_ADMIN approves
    
    User Code Format: 6 characters (2 letters + 4 digits), e.g., AB1234
    """
    
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
    
    async def get_user_by_code(self, user_code: str) -> Optional[User]:
        """Get user by 6-character user code (e.g., AB1234)."""
        result = await self.db.execute(
            select(User).where(
                User.user_code == user_code.upper(),
                User.is_deleted == False
            )
        )
        return result.scalar_one_or_none()
    
    async def validate_hierarchy(
        self,
        role: UserRole,
        team_lead_code: Optional[str] = None,
        manager_code: Optional[str] = None,
        admin_code: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate hierarchy assignments based on role.
        
        Rules:
        - EMPLOYEE must have a team_lead_code and manager_code
        - TEAM_LEAD must have a manager_code
        - MANAGER must have an admin_code
        """
        if role == UserRole.EMPLOYEE:
            if not team_lead_code:
                return False, "Employees must be assigned to a team lead"
            team_lead = await self.get_user_by_code(team_lead_code)
            if not team_lead:
                return False, f"Team lead with code '{team_lead_code}' not found"
            if team_lead.role != UserRole.TEAM_LEAD:
                return False, f"User '{team_lead_code}' is not a team lead"
            if not manager_code:
                return False, "Employees must be assigned to a manager"
            manager = await self.get_user_by_code(manager_code)
            if not manager:
                return False, f"Manager with code '{manager_code}' not found"
            if manager.role != UserRole.MANAGER:
                return False, f"User '{manager_code}' is not a manager"
                
        elif role == UserRole.TEAM_LEAD:
            if not manager_code:
                return False, "Team leads must be assigned to a manager"
            manager = await self.get_user_by_code(manager_code)
            if not manager:
                return False, f"Manager with code '{manager_code}' not found"
            if manager.role != UserRole.MANAGER:
                return False, f"User '{manager_code}' is not a manager"
        
        elif role == UserRole.MANAGER:
            if not admin_code:
                return False, "Managers must be assigned to an admin"
            admin = await self.get_user_by_code(admin_code)
            if not admin:
                return False, f"Admin with code '{admin_code}' not found"
            if admin.role != UserRole.ADMIN:
                return False, f"User '{admin_code}' is not an admin"
        
        return True, None
    
    async def create_user(
        self,
        user_data: UserCreate,
        created_by: User
    ) -> Tuple[Optional[User], Optional[str]]:
        """
        Create a new user - Only SUPER_ADMIN and ADMIN can create users.
        
        Permission Rules:
        - SUPER_ADMIN can create: ADMIN, MANAGER, TEAM_LEAD, EMPLOYEE
        - ADMIN can create: MANAGER, TEAM_LEAD, EMPLOYEE (not ADMIN or SUPER_ADMIN)
        
        Auto-filled fields:
        - id: UUID (auto-generated by DB)
        - user_code: 6-character unique code (auto-generated by model)
        - created_by_code: Creator's user_code
        - hierarchy codes: Auto-assigned based on creator if not provided
        """
        
        # Only SUPER_ADMIN and ADMIN can create users
        if created_by.role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
            return None, "Only Super Admin and Admin can create users"
        
        # Validate role creation permissions
        role = user_data.role
        
        if role == UserRole.SUPER_ADMIN:
            return None, "Cannot create Super Admin users"
        
        if role == UserRole.ADMIN and created_by.role != UserRole.SUPER_ADMIN:
            return None, "Only Super Admin can create Admin users"
        
        # Initialize hierarchy codes (convert empty strings to None for FK constraints)
        team_lead_code = user_data.team_lead_code or None
        manager_code = user_data.manager_code or None
        admin_code = user_data.admin_code or None
        
        # Auto-fill admin_code based on creator
        # If Admin creates user → admin_code = Admin's user_code (for all roles)
        # If Super Admin creates user → admin_code can be provided or left None
        if created_by.role == UserRole.ADMIN:
            # Admin creating user - always set admin_code to the Admin's code
            admin_code = created_by.user_code
        elif created_by.role == UserRole.SUPER_ADMIN and admin_code:
            # Super Admin can optionally specify an admin_code - validate it
            admin_user = await self.get_user_by_code(admin_code)
            if not admin_user:
                return None, f"Admin with code '{admin_code}' not found"
            if admin_user.role != UserRole.ADMIN:
                return None, f"User '{admin_code}' is not an Admin"
        
        # Validate role-specific hierarchy codes
        if role == UserRole.MANAGER:
            # Manager can optionally have admin_code (already handled above)
            if user_data.manager_type is None:
                return None, "manager_type is required when creating a Manager"
        
        elif role == UserRole.TEAM_LEAD:
            # Team lead needs manager_code - validate if provided
            if manager_code:
                manager_user = await self.get_user_by_code(manager_code)
                if not manager_user:
                    return None, f"Manager with code '{manager_code}' not found"
                if manager_user.role != UserRole.MANAGER:
                    return None, f"User '{manager_code}' is not a Manager"
        
        elif role == UserRole.EMPLOYEE:
            # Employee can have team_lead_code and manager_code
            if team_lead_code:
                team_lead = await self.get_user_by_code(team_lead_code)
                if not team_lead:
                    return None, f"Team lead with code '{team_lead_code}' not found"
                if team_lead.role != UserRole.TEAM_LEAD:
                    return None, f"User '{team_lead_code}' is not a Team Lead"
            
            if manager_code:
                manager_user = await self.get_user_by_code(manager_code)
                if not manager_user:
                    return None, f"Manager with code '{manager_code}' not found"
                if manager_user.role != UserRole.MANAGER:
                    return None, f"User '{manager_code}' is not a Manager"
        
        # Generate email if not provided
        if user_data.email:
            email = user_data.email
        else:
            first_name = user_data.first_name.lower().replace(' ', '')
            last_name = user_data.last_name.lower().replace(' ', '')
            email = f"{first_name}.{last_name}@{settings.COMPANY_DOMAIN}"
        
        # Check for duplicate email
        existing_email = await self.get_user_by_email(email)
        if existing_email:
            return None, f"Email '{email}' already exists"
        
        # Create user - user_code will be auto-generated by the model
        new_user = User(
            email=email,
            hashed_password=get_password_hash(user_data.password),
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            role=role,
            phone=user_data.phone or None,
            # Manager-specific fields
            manager_type=user_data.manager_type if role == UserRole.MANAGER else None,
            # Department
            department=user_data.department or None,
            # Hierarchy fields
            created_by_code=created_by.user_code,
            team_lead_code=team_lead_code if role == UserRole.EMPLOYEE else None,
            manager_code=manager_code if role in [UserRole.EMPLOYEE, UserRole.TEAM_LEAD] else None,
            admin_code=admin_code,  # Store admin_code for all roles (auto-filled if created by Admin)
            # Vehicle info for employee services
            vehicle_number=user_data.vehicle_number or None,
            vehicle_type=user_data.vehicle_type,
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
        """Update user details with role-based validation."""
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
            # Regular users can only update themselves
            if str(user.id) != str(updated_by.id):
                return None, "Can only update your own profile"
            # And can only update limited fields
            allowed_fields = {'first_name', 'last_name', 'phone'}
            update_data = user_data.model_dump(exclude_unset=True)
            if set(update_data.keys()) - allowed_fields:
                return None, "You can only update name and phone"
        
        # Update fields
        update_data = user_data.model_dump(exclude_unset=True)
        
        # Only allow manager_type and department for MANAGER role
        if user.role != UserRole.MANAGER:
            update_data.pop('manager_type', None)
        if user.role not in [UserRole.MANAGER, UserRole.TEAM_LEAD]:
            update_data.pop('department', None)
        
        for field, value in update_data.items():
            if hasattr(user, field):
                setattr(user, field, value)
        
        await self.db.commit()
        await self.db.refresh(user)
        
        return user, None
    
    async def update_password(
        self,
        user_id: UUID,
        new_password: str,
        updated_by: User
    ) -> Tuple[bool, Optional[str]]:
        """Update user password (admin action)."""
        user = await self.get_user_by_id(user_id)
        if not user:
            return False, "User not found"
        
        # Only super admin and admin can reset passwords
        if updated_by.role == UserRole.SUPER_ADMIN:
            pass  # Can reset any password
        elif updated_by.role == UserRole.ADMIN:
            if user.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
                return False, "Cannot reset Admin or Super Admin password"
        else:
            return False, "Insufficient permissions"
        
        user.hashed_password = get_password_hash(new_password)
        await self.db.commit()
        
        return True, None
    
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
        manager_type: Optional[ManagerType] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
        requesting_user: Optional[User] = None
    ) -> Tuple[List[User], int]:
        """
        List users with filtering and pagination.
        
        Access Control:
        - SUPER_ADMIN: See all users
        - ADMIN: See all non-admin users
        - Others: Only see active users (limited view)
        """
        query = select(User).where(User.is_deleted == False)
        count_query = select(func.count(User.id)).where(User.is_deleted == False)
        
        # Role-based visibility
        if requesting_user:
            if requesting_user.role == UserRole.ADMIN:
                # Admins can't see Super Admin or other Admins
                query = query.where(User.role.notin_([UserRole.SUPER_ADMIN, UserRole.ADMIN]))
                count_query = count_query.where(User.role.notin_([UserRole.SUPER_ADMIN, UserRole.ADMIN]))
            elif requesting_user.role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
                # Regular users only see active users
                query = query.where(User.is_active == True)
                count_query = count_query.where(User.is_active == True)
        
        # Apply filters
        if role:
            query = query.where(User.role == role)
            count_query = count_query.where(User.role == role)
        
        if manager_type:
            query = query.where(User.manager_type == manager_type)
            count_query = count_query.where(User.manager_type == manager_type)
        
        if is_active is not None:
            query = query.where(User.is_active == is_active)
            count_query = count_query.where(User.is_active == is_active)
        
        if search:
            search_filter = or_(
                User.first_name.ilike(f"%{search}%"),
                User.last_name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
                User.user_code.ilike(f"%{search}%")
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
    
    async def get_managers_by_type(
        self,
        manager_type: ManagerType
    ) -> List[User]:
        """Get all managers of a specific type."""
        result = await self.db.execute(
            select(User).where(
                User.role == UserRole.MANAGER,
                User.manager_type == manager_type,
                User.is_deleted == False,
                User.is_active == True
            )
        )
        return list(result.scalars().all())
    
    async def change_user_role(
        self,
        user_id: UUID,
        new_role: UserRole,
        changed_by: User,
        manager_type: Optional[ManagerType] = None,
        department: Optional[str] = None
    ) -> Tuple[Optional[User], Optional[str]]:
        """
        Change user's role.
        
        Only SUPER_ADMIN can change roles.
        """
        if changed_by.role != UserRole.SUPER_ADMIN:
            return None, "Only Super Admin can change user roles"
        
        user = await self.get_user_by_id(user_id)
        if not user:
            return None, "User not found"
        
        if user.role == UserRole.SUPER_ADMIN:
            return None, "Cannot change Super Admin role"
        
        if new_role == UserRole.SUPER_ADMIN:
            return None, "Cannot promote to Super Admin"
        
        # Validate manager fields for MANAGER role
        if new_role == UserRole.MANAGER:
            if not manager_type:
                return None, "manager_type is required when changing to MANAGER role"
            user.manager_type = manager_type
            user.department = department
        else:
            user.manager_type = None
            user.department = department  # Department can be set for team leads too
        
        user.role = new_role
        
        await self.db.commit()
        await self.db.refresh(user)
        
        return user, None
    
    async def toggle_user_active(
        self,
        user_id: UUID,
        toggled_by: User
    ) -> Tuple[Optional[User], Optional[str]]:
        """Toggle user's active status."""
        user = await self.get_user_by_id(user_id)
        if not user:
            return None, "User not found"
        
        # Validate permissions
        if toggled_by.role == UserRole.SUPER_ADMIN:
            if user.role == UserRole.SUPER_ADMIN:
                return None, "Cannot deactivate Super Admin"
        elif toggled_by.role == UserRole.ADMIN:
            if user.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
                return None, "Cannot modify Admin or Super Admin status"
        else:
            return None, "Insufficient permissions"
        
        user.is_active = not user.is_active
        await self.db.commit()
        await self.db.refresh(user)
        
        return user, None
    
    async def get_team_members(
        self,
        supervisor: User
    ) -> List[User]:
        """
        Get team members reporting to a supervisor.
        
        - TEAM_LEAD: Gets all employees with team_lead_code matching
        - MANAGER: Gets all team leads with manager_code matching + their employees
        """
        if supervisor.role == UserRole.TEAM_LEAD:
            # Get employees reporting to this team lead
            result = await self.db.execute(
                select(User).where(
                    User.team_lead_code == supervisor.user_code,
                    User.is_deleted == False,
                    User.is_active == True
                )
            )
            return list(result.scalars().all())
        
        elif supervisor.role == UserRole.MANAGER:
            # Get team leads reporting to this manager
            team_leads_result = await self.db.execute(
                select(User).where(
                    User.manager_code == supervisor.user_code,
                    User.is_deleted == False,
                    User.is_active == True
                )
            )
            team_leads = list(team_leads_result.scalars().all())
            
            # Also get employees of those team leads
            team_lead_codes = [tl.user_code for tl in team_leads]
            if team_lead_codes:
                employees_result = await self.db.execute(
                    select(User).where(
                        User.team_lead_code.in_(team_lead_codes),
                        User.is_deleted == False,
                        User.is_active == True
                    )
                )
                employees = list(employees_result.scalars().all())
                return team_leads + employees
            
            return team_leads
        
        return []
    
    async def get_direct_reports(
        self,
        supervisor: User
    ) -> List[User]:
        """
        Get direct reports only (not entire team hierarchy).
        
        - SUPER_ADMIN: Gets admins
        - ADMIN: Gets managers with admin_code matching
        - MANAGER: Gets team leads with manager_code matching
        - TEAM_LEAD: Gets employees with team_lead_code matching
        """
        if supervisor.role == UserRole.SUPER_ADMIN:
            result = await self.db.execute(
                select(User).where(
                    User.role == UserRole.ADMIN,
                    User.is_deleted == False,
                    User.is_active == True
                )
            )
        elif supervisor.role == UserRole.ADMIN:
            result = await self.db.execute(
                select(User).where(
                    User.admin_code == supervisor.user_code,
                    User.is_deleted == False,
                    User.is_active == True
                )
            )
        elif supervisor.role == UserRole.MANAGER:
            result = await self.db.execute(
                select(User).where(
                    User.manager_code == supervisor.user_code,
                    User.is_deleted == False,
                    User.is_active == True
                )
            )
        elif supervisor.role == UserRole.TEAM_LEAD:
            result = await self.db.execute(
                select(User).where(
                    User.team_lead_code == supervisor.user_code,
                    User.is_deleted == False,
                    User.is_active == True
                )
            )
        else:
            return []
        
        return list(result.scalars().all())
    
    async def get_approver(
        self,
        user: User
    ) -> Optional[User]:
        """
        Get the approver for a user based on hierarchy.
        
        Approval Flow:
        - EMPLOYEE -> TEAM_LEAD
        - TEAM_LEAD -> MANAGER
        - MANAGER -> ADMIN
        - ADMIN -> SUPER_ADMIN
        """
        if user.role == UserRole.EMPLOYEE and user.team_lead_code:
            return await self.get_user_by_code(user.team_lead_code)
        elif user.role == UserRole.TEAM_LEAD and user.manager_code:
            return await self.get_user_by_code(user.manager_code)
        elif user.role == UserRole.MANAGER and user.admin_code:
            return await self.get_user_by_code(user.admin_code)
        elif user.role == UserRole.ADMIN:
            # Find super admin
            result = await self.db.execute(
                select(User).where(
                    User.role == UserRole.SUPER_ADMIN,
                    User.is_deleted == False,
                    User.is_active == True
                ).limit(1)
            )
            return result.scalar_one_or_none()
        return None
    
    async def is_approver_for(
        self,
        approver: User,
        subordinate: User
    ) -> bool:
        """Check if a user is the approver for another user."""
        if subordinate.role == UserRole.EMPLOYEE:
            return subordinate.team_lead_code == approver.user_code
        elif subordinate.role == UserRole.TEAM_LEAD:
            return subordinate.manager_code == approver.user_code
        elif subordinate.role == UserRole.MANAGER:
            return subordinate.admin_code == approver.user_code
        elif subordinate.role == UserRole.ADMIN:
            return approver.role == UserRole.SUPER_ADMIN
        return False
    
    async def can_use_employee_services(self, user: User) -> bool:
        """
        Check if user can use employee services (parking, desk booking, cafeteria).
        
        Available to: EMPLOYEE, TEAM_LEAD, MANAGER
        """
        return user.role in [UserRole.EMPLOYEE, UserRole.TEAM_LEAD, UserRole.MANAGER]
    
    async def update_hierarchy(
        self,
        user_id: UUID,
        team_lead_code: Optional[str] = None,
        manager_code: Optional[str] = None,
        admin_code: Optional[str] = None,
        updated_by: User = None
    ) -> Tuple[Optional[User], Optional[str]]:
        """
        Update user's reporting hierarchy.
        
        Only SUPER_ADMIN, ADMIN, and MANAGER can update hierarchy.
        """
        if updated_by:
            if updated_by.role == UserRole.SUPER_ADMIN:
                pass  # Can update any hierarchy
            elif updated_by.role == UserRole.ADMIN:
                # Admin can only update managers' admin_code to themselves
                pass
            elif updated_by.role == UserRole.MANAGER:
                # Manager can only update team leads and employees
                pass
            else:
                return None, "Insufficient permissions to update hierarchy"
        
        user = await self.get_user_by_id(user_id)
        if not user:
            return None, "User not found"
        
        # Validate new hierarchy
        is_valid, error = await self.validate_hierarchy(
            user.role,
            team_lead_code or user.team_lead_code,
            manager_code or user.manager_code,
            admin_code or user.admin_code
        )
        if not is_valid:
            return None, error
        
        if team_lead_code is not None:
            user.team_lead_code = team_lead_code
        if manager_code is not None:
            user.manager_code = manager_code
        if admin_code is not None:
            user.admin_code = admin_code
        
        await self.db.commit()
        await self.db.refresh(user)
        
        return user, None
    
    async def get_managers_by_admin(
        self,
        admin: User
    ) -> List[User]:
        """Get all managers created by/assigned to an admin."""
        if admin.role != UserRole.ADMIN:
            return []
        
        result = await self.db.execute(
            select(User).where(
                User.role == UserRole.MANAGER,
                User.admin_code == admin.user_code,
                User.is_deleted == False,
                User.is_active == True
            )
        )
        return list(result.scalars().all())
    
    async def get_managers_by_type(
        self,
        manager_type: ManagerType
    ) -> List[User]:
        """Get all managers of a specific type."""
        result = await self.db.execute(
            select(User).where(
                User.role == UserRole.MANAGER,
                User.manager_type == manager_type,
                User.is_deleted == False,
                User.is_active == True
            )
        )
        return list(result.scalars().all())
    
    async def get_team_leads_by_manager(
        self,
        manager: User
    ) -> List[User]:
        """Get all team leads under a manager."""
        if manager.role != UserRole.MANAGER:
            return []
        
        result = await self.db.execute(
            select(User).where(
                User.role == UserRole.TEAM_LEAD,
                User.manager_code == manager.user_code,
                User.is_deleted == False,
                User.is_active == True
            )
        )
        return list(result.scalars().all())
    
    async def get_team_leads_by_department(
        self,
        department: str
    ) -> List[User]:
        """Get all team leads of a specific department."""
        result = await self.db.execute(
            select(User).where(
                User.role == UserRole.TEAM_LEAD,
                User.department == department,
                User.is_deleted == False,
                User.is_active == True
            )
        )
        return list(result.scalars().all())
    
    async def get_employees_by_team_lead(
        self,
        team_lead: User
    ) -> List[User]:
        """Get all employees under a team lead."""
        if team_lead.role != UserRole.TEAM_LEAD:
            return []
        
        result = await self.db.execute(
            select(User).where(
                User.role == UserRole.EMPLOYEE,
                User.team_lead_code == team_lead.user_code,
                User.is_deleted == False,
                User.is_active == True
            )
        )
        return list(result.scalars().all())
    
    async def get_all_subordinates(
        self,
        user: User
    ) -> List[User]:
        """
        Get all subordinates under a user (recursively).
        
        - SUPER_ADMIN: All users
        - ADMIN: All managers under them + their team leads + their employees
        - MANAGER: All team leads under them + their employees
        - TEAM_LEAD: All employees under them
        """
        subordinates = []
        
        if user.role == UserRole.SUPER_ADMIN:
            # Get all non-super-admin users
            result = await self.db.execute(
                select(User).where(
                    User.role != UserRole.SUPER_ADMIN,
                    User.is_deleted == False
                )
            )
            return list(result.scalars().all())
        
        elif user.role == UserRole.ADMIN:
            # Get managers under this admin
            managers = await self.get_managers_by_admin(user)
            subordinates.extend(managers)
            
            # Get team leads under those managers
            for manager in managers:
                team_leads = await self.get_team_leads_by_manager(manager)
                subordinates.extend(team_leads)
                
                # Get employees under those team leads
                for team_lead in team_leads:
                    employees = await self.get_employees_by_team_lead(team_lead)
                    subordinates.extend(employees)
        
        elif user.role == UserRole.MANAGER:
            # Get team leads under this manager
            team_leads = await self.get_team_leads_by_manager(user)
            subordinates.extend(team_leads)
            
            # Get employees under those team leads
            for team_lead in team_leads:
                employees = await self.get_employees_by_team_lead(team_lead)
                subordinates.extend(employees)
        
        elif user.role == UserRole.TEAM_LEAD:
            # Get employees under this team lead
            employees = await self.get_employees_by_team_lead(user)
            subordinates.extend(employees)
        
        return subordinates