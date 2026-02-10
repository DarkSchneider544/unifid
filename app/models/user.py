from sqlalchemy import (
    Column, String, Boolean, Enum, Index, event, ForeignKey
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
import random
import string

from .base import Base, TimestampMixin
from .enums import UserRole, ManagerType


def generate_user_code():
    """
    Generate a unique 6-character alphanumeric user code.
    Format: 2 letters + 4 digits (e.g., AB1234)
    """
    letters = ''.join(random.choices(string.ascii_uppercase, k=2))
    digits = ''.join(random.choices(string.digits, k=4))
    return f"{letters}{digits}"


class User(Base, TimestampMixin):
    """
    User model with role-based access control and hierarchical approval system.
    
    Hierarchy (from whiteboard):
    ┌─────────────────────────────────────────────────────────────────┐
    │  SUPER_ADMIN                                                     │
    │       │ creates                                                  │
    │       ▼                                                          │
    │    ADMIN                                                         │
    │       │ creates                                                  │
    │       ▼                                                          │
    │  MANAGER (5 types):                                              │
    │    - Parking Manager                                             │
    │    - Attendance Manager (creates dept Team Leads)                │
    │    - Desk & Conference Manager                                   │
    │    - Cafeteria Manager (has Food Inventory TL, Desk Cafe TL)     │
    │    - IT Support Manager                                          │
    │       │ creates                                                  │
    │       ▼                                                          │
    │  TEAM_LEAD (Department-wise: Dev, Sales, AI, etc.)               │
    │       │ manages                                                  │
    │       ▼                                                          │
    │  EMPLOYEE (emp1, emp2, emp3...)                                  │
    └─────────────────────────────────────────────────────────────────┘
    
    Approval Hierarchy (Attendance & Leave):
    - EMPLOYEE submits -> TEAM_LEAD approves
    - TEAM_LEAD submits -> MANAGER approves
    - MANAGER submits -> ADMIN approves
    - ADMIN submits -> SUPER_ADMIN approves
    
    User Identification:
    - user_code: Unique 6-character alphanumeric code (e.g., AB1234)
    - This is the PRIMARY identifier used throughout the system for all operations
    """
    __tablename__ = "users"
    
    # Primary key - auto-generated UUID (internal use only)
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # User Code - unique 6-character alphanumeric identifier (PUBLIC identifier)
    # Format: 2 letters + 4 digits (e.g., AB1234)
    user_code = Column(String(10), unique=True, nullable=False, index=True)
    
    # Basic info
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=True)
    
    # Role-based access
    role = Column(Enum(UserRole), nullable=False, default=UserRole.EMPLOYEE)
    
    # Manager type - only applicable for MANAGER role
    manager_type = Column(Enum(ManagerType), nullable=True)
    
    # Department/Team info (e.g., Dev, Sales, AI, HR, etc.)
    department = Column(String(100), nullable=True)
    
    # Hierarchical reporting structure for approval flow
    # created_by_code: User code of who created this user
    # team_lead_code: User code of the Team Lead (for employees)
    # manager_code: User code of the Manager (for team leads)
    # admin_code: User code of the Admin (for managers)
    created_by_code = Column(String(10), ForeignKey("users.user_code"), nullable=True)
    team_lead_code = Column(String(10), ForeignKey("users.user_code"), nullable=True)
    manager_code = Column(String(10), ForeignKey("users.user_code"), nullable=True)
    admin_code = Column(String(10), ForeignKey("users.user_code"), nullable=True)
    
    # Vehicle info (for parking)
    vehicle_number = Column(String(50), nullable=True)
    vehicle_type = Column(String(20), nullable=True)  # car, bike, two_wheeler
    
    # Status flags
    is_active = Column(Boolean, default=True)
    is_deleted = Column(Boolean, default=False)
    
    # Self-referential relationships for hierarchy
    creator = relationship(
        "User",
        foreign_keys=[created_by_code],
        remote_side="User.user_code",
        backref="created_users"
    )
    team_lead = relationship(
        "User", 
        foreign_keys=[team_lead_code],
        remote_side="User.user_code",
        backref="team_members"
    )
    manager = relationship(
        "User",
        foreign_keys=[manager_code], 
        remote_side="User.user_code",
        backref="managed_team_leads"
    )
    admin = relationship(
        "User",
        foreign_keys=[admin_code],
        remote_side="User.user_code",
        backref="managed_managers"
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_users_role", "role"),
        Index("ix_users_manager_type", "manager_type"),
        Index("ix_users_active_deleted", "is_active", "is_deleted"),
        Index("ix_users_team_lead", "team_lead_code"),
        Index("ix_users_manager", "manager_code"),
        Index("ix_users_admin", "admin_code"),
        Index("ix_users_department", "department"),
        Index("ix_users_created_by", "created_by_code"),
    )
    
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
    
    @property
    def is_super_admin(self) -> bool:
        """Check if user is super admin."""
        return self.role == UserRole.SUPER_ADMIN
    
    @property
    def is_admin(self) -> bool:
        """Check if user is admin."""
        return self.role == UserRole.ADMIN
    
    @property
    def is_manager(self) -> bool:
        """Check if user is a manager."""
        return self.role == UserRole.MANAGER
    
    @property
    def is_team_lead(self) -> bool:
        """Check if user is a team lead."""
        return self.role == UserRole.TEAM_LEAD
    
    @property
    def is_employee(self) -> bool:
        """Check if user is an employee."""
        return self.role == UserRole.EMPLOYEE
    
    @property
    def can_create_users(self) -> bool:
        """Check if user can create other users."""
        return self.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.MANAGER]
    
    @property
    def can_approve_attendance(self) -> bool:
        """Check if user can approve attendance."""
        return self.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.MANAGER, UserRole.TEAM_LEAD]
    
    @property
    def can_approve_leave(self) -> bool:
        """Check if user can approve leave."""
        return self.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.MANAGER, UserRole.TEAM_LEAD]
    
    @property
    def can_use_employee_services(self) -> bool:
        """
        Check if user can use employee services (parking, desk booking, cafeteria).
        Manager and Team Lead are promoted employees, so they can use these services.
        """
        return self.role in [UserRole.EMPLOYEE, UserRole.TEAM_LEAD, UserRole.MANAGER]
    
    def get_approver_code(self) -> str:
        """
        Get the user_code of who should approve this user's attendance/leave.
        
        Returns:
        - For EMPLOYEE: team_lead_code
        - For TEAM_LEAD: manager_code
        - For MANAGER: admin_code
        - For ADMIN: Super Admin handles this (returns None, find SA dynamically)
        """
        if self.role == UserRole.EMPLOYEE:
            return self.team_lead_code
        elif self.role == UserRole.TEAM_LEAD:
            return self.manager_code
        elif self.role == UserRole.MANAGER:
            return self.admin_code
        elif self.role == UserRole.ADMIN:
            return None  # Super Admin approves - find dynamically
        return None
    
    def get_creatable_roles(self) -> list:
        """
        Get roles that this user can create.
        
        - SUPER_ADMIN can create ADMIN
        - ADMIN can create MANAGER
        - MANAGER (Attendance type) can create TEAM_LEAD
        - TEAM_LEAD cannot create users (they manage existing employees)
        """
        if self.role == UserRole.SUPER_ADMIN:
            return [UserRole.ADMIN]
        elif self.role == UserRole.ADMIN:
            return [UserRole.MANAGER]
        elif self.role == UserRole.MANAGER:
            # Only Attendance Manager creates Team Leads
            if self.manager_type == ManagerType.ATTENDANCE:
                return [UserRole.TEAM_LEAD, UserRole.EMPLOYEE]
            return []
        return []


# Event listener to auto-generate user_code if not set
@event.listens_for(User, 'before_insert')
def generate_user_code_before_insert(mapper, connection, target):
    """Auto-generate a unique 6-character alphanumeric user code before inserting a new user."""
    if not target.user_code:
        target.user_code = generate_user_code()