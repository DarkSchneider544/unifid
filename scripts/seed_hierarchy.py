"""
Seed data script for hierarchical user structure.
Run with: python -m scripts.seed_hierarchy

Hierarchy:
┌─────────────────────────────────────────────────────────────────┐
│  SUPER_ADMIN (SA0001)                                           │
│       │ creates                                                 │
│       ▼                                                         │
│    ADMIN (AD0001)                                               │
│       │ creates                                                 │
│       ▼                                                         │
│  MANAGER (5 types):                                             │
│    - Parking Manager (PM0001)                                   │
│    - Attendance Manager (AM0001) -> creates Team Leads          │
│    - Desk & Conference Manager (DM0001)                         │
│    - Cafeteria Manager (CM0001)                                 │
│    - IT Support Manager (IM0001)                                │
│       │ creates                                                 │
│       ▼                                                         │
│  TEAM_LEAD (TL0001 - Dev, TL0002 - Sales, etc.)                 │
│       │ manages                                                 │
│       ▼                                                         │
│  EMPLOYEE (EM0001, EM0002, EM0003...)                           │
└─────────────────────────────────────────────────────────────────┘
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash
from app.models.user import User
from app.models.enums import UserRole, ManagerType


async def seed_hierarchy(db: AsyncSession):
    """Seed the complete user hierarchy."""
    
    # Check if super admin exists
    result = await db.execute(
        select(User).where(User.role == UserRole.SUPER_ADMIN)
    )
    if result.scalar_one_or_none():
        print("Users already seeded. Skipping...")
        return
    
    print("Seeding hierarchical user structure...")
    
    # 1. Create Super Admin
    super_admin = User(
        user_code="SA0001",
        email="super.admin@cygnet.com",
        hashed_password=get_password_hash("Admin@123"),
        first_name="Super",
        last_name="Admin",
        role=UserRole.SUPER_ADMIN,
    )
    db.add(super_admin)
    await db.flush()  # Get the user_code
    print(f"✓ Created Super Admin: {super_admin.user_code}")
    
    # 2. Create Admin (created by Super Admin)
    admin = User(
        user_code="AD0001",
        email="admin@cygnet.com",
        hashed_password=get_password_hash("Admin@123"),
        first_name="Main",
        last_name="Admin",
        role=UserRole.ADMIN,
        created_by_code=super_admin.user_code,
    )
    db.add(admin)
    await db.flush()
    print(f"✓ Created Admin: {admin.user_code} (created by {super_admin.user_code})")
    
    # 3. Create Managers (created by Admin)
    managers = [
        {
            "user_code": "PM0001",
            "email": "parking.manager@cygnet.com",
            "first_name": "Parking",
            "last_name": "Manager",
            "manager_type": ManagerType.PARKING,
        },
        {
            "user_code": "AM0001",
            "email": "attendance.manager@cygnet.com",
            "first_name": "Attendance",
            "last_name": "Manager",
            "manager_type": ManagerType.ATTENDANCE,
        },
        {
            "user_code": "DM0001",
            "email": "desk.manager@cygnet.com",
            "first_name": "Desk",
            "last_name": "Manager",
            "manager_type": ManagerType.DESK_CONFERENCE,
        },
        {
            "user_code": "CM0001",
            "email": "cafeteria.manager@cygnet.com",
            "first_name": "Cafeteria",
            "last_name": "Manager",
            "manager_type": ManagerType.CAFETERIA,
        },
        {
            "user_code": "IM0001",
            "email": "it.manager@cygnet.com",
            "first_name": "IT Support",
            "last_name": "Manager",
            "manager_type": ManagerType.IT_SUPPORT,
        },
    ]
    
    manager_objects = {}
    for m in managers:
        manager = User(
            user_code=m["user_code"],
            email=m["email"],
            hashed_password=get_password_hash("Manager@123"),
            first_name=m["first_name"],
            last_name=m["last_name"],
            role=UserRole.MANAGER,
            manager_type=m["manager_type"],
            admin_code=admin.user_code,
            created_by_code=admin.user_code,
        )
        db.add(manager)
        manager_objects[m["manager_type"]] = manager
        print(f"✓ Created Manager: {manager.user_code} ({m['manager_type'].value}) (admin: {admin.user_code})")
    
    await db.flush()
    
    # 4. Create Team Leads (created by Attendance Manager - only Attendance Manager can create TLs)
    attendance_manager = manager_objects[ManagerType.ATTENDANCE]
    team_leads = [
        {"user_code": "TL0001", "department": "Development", "first_name": "Dev", "last_name": "Lead"},
        {"user_code": "TL0002", "department": "Sales", "first_name": "Sales", "last_name": "Lead"},
        {"user_code": "TL0003", "department": "AI", "first_name": "AI", "last_name": "Lead"},
        {"user_code": "TL0004", "department": "HR", "first_name": "HR", "last_name": "Lead"},
    ]
    
    team_lead_objects = {}
    for tl in team_leads:
        team_lead = User(
            user_code=tl["user_code"],
            email=f"{tl['department'].lower()}.lead@cygnet.com",
            hashed_password=get_password_hash("TeamLead@123"),
            first_name=tl["first_name"],
            last_name=tl["last_name"],
            role=UserRole.TEAM_LEAD,
            department=tl["department"],
            manager_code=attendance_manager.user_code,
            created_by_code=attendance_manager.user_code,
        )
        db.add(team_lead)
        team_lead_objects[tl["department"]] = team_lead
        print(f"✓ Created Team Lead: {team_lead.user_code} ({tl['department']}) (manager: {attendance_manager.user_code})")
    
    await db.flush()
    
    # 5. Create Employees (under their respective Team Leads)
    employees = [
        # Dev Team
        {"user_code": "EM0001", "department": "Development", "first_name": "John", "last_name": "Developer"},
        {"user_code": "EM0002", "department": "Development", "first_name": "Jane", "last_name": "Coder"},
        {"user_code": "EM0003", "department": "Development", "first_name": "Bob", "last_name": "Programmer"},
        # Sales Team
        {"user_code": "EM0004", "department": "Sales", "first_name": "Alice", "last_name": "Seller"},
        {"user_code": "EM0005", "department": "Sales", "first_name": "Charlie", "last_name": "Deal"},
        # AI Team
        {"user_code": "EM0006", "department": "AI", "first_name": "Data", "last_name": "Scientist"},
        {"user_code": "EM0007", "department": "AI", "first_name": "ML", "last_name": "Engineer"},
        # HR Team
        {"user_code": "EM0008", "department": "HR", "first_name": "Human", "last_name": "Resource"},
    ]
    
    for emp in employees:
        team_lead = team_lead_objects.get(emp["department"])
        if not team_lead:
            continue
            
        employee = User(
            user_code=emp["user_code"],
            email=f"{emp['first_name'].lower()}.{emp['last_name'].lower()}@cygnet.com",
            hashed_password=get_password_hash("Employee@123"),
            first_name=emp["first_name"],
            last_name=emp["last_name"],
            role=UserRole.EMPLOYEE,
            department=emp["department"],
            team_lead_code=team_lead.user_code,
            manager_code=attendance_manager.user_code,  # All employees report to attendance manager for attendance
            created_by_code=attendance_manager.user_code,
        )
        db.add(employee)
        print(f"✓ Created Employee: {employee.user_code} ({emp['department']}) (TL: {team_lead.user_code})")
    
    await db.commit()
    print("\n" + "="*60)
    print("User hierarchy seeding completed!")
    print("="*60)
    print("\nLogin credentials:")
    print("-"*40)
    print("Super Admin: super.admin@cygnet.com / Admin@123")
    print("Admin: admin@cygnet.com / Admin@123")
    print("Managers: [type].manager@cygnet.com / Manager@123")
    print("Team Leads: [dept].lead@cygnet.com / TeamLead@123")
    print("Employees: [name]@cygnet.com / Employee@123")
    print("-"*40)


async def main():
    async with AsyncSessionLocal() as db:
        await seed_hierarchy(db)


if __name__ == "__main__":
    asyncio.run(main())
