"""
Seed data script for initial setup.
Run with: python -m scripts.seed_data
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
from app.models.floor_plan import FloorPlan, FloorPlanVersion
from app.models.food import FoodItem
from app.models.it_asset import ITAsset
from app.models.enums import (
    UserRole, AdminType, FloorPlanType, CellType, AssetType, AssetStatus
)
from decimal import Decimal
import uuid


async def seed_users(db: AsyncSession):
    """Seed initial users with auto-generated 4-digit user codes."""
    users = [
        # Super Admin
        {
            "user_code": "1001",
            "email": "super.admin@company.com",
            "password": "Admin@123",
            "first_name": "Super",
            "last_name": "Admin",
            "role": UserRole.SUPER_ADMIN,
            "admin_type": None,
            "department": "Administration"
        },
        # IT Admin
        {
            "user_code": "2001",
            "email": "it.admin@company.com",
            "password": "Admin@123",
            "first_name": "IT",
            "last_name": "Admin",
            "role": UserRole.ADMIN,
            "admin_type": AdminType.IT,
            "department": "IT"
        },
        # Security Admin
        {
            "user_code": "2002",
            "email": "security.admin@company.com",
            "password": "Admin@123",
            "first_name": "Security",
            "last_name": "Admin",
            "role": UserRole.ADMIN,
            "admin_type": AdminType.SECURITY,
            "department": "Security"
        },
        # Cafeteria Admin
        {
            "user_code": "2003",
            "email": "cafeteria.admin@company.com",
            "password": "Admin@123",
            "first_name": "Cafeteria",
            "last_name": "Admin",
            "role": UserRole.ADMIN,
            "admin_type": AdminType.CAFETERIA,
            "department": "Food Services"
        },
        # Desk Admin
        {
            "user_code": "2004",
            "email": "desk.admin@company.com",
            "password": "Admin@123",
            "first_name": "Desk",
            "last_name": "Admin",
            "role": UserRole.ADMIN,
            "admin_type": AdminType.DESK,
            "department": "Facilities"
        },
        # Manager
        {
            "user_code": "3001",
            "email": "manager@company.com",
            "password": "Manager@123",
            "first_name": "John",
            "last_name": "Manager",
            "role": UserRole.MANAGER,
            "admin_type": None,
            "department": "Engineering"
        },
        # Team Lead
        {
            "user_code": "3002",
            "email": "teamlead@company.com",
            "password": "TeamLead@123",
            "first_name": "Jane",
            "last_name": "TeamLead",
            "role": UserRole.TEAM_LEAD,
            "admin_type": None,
            "department": "Engineering"
        },
        # Employees
        {
            "user_code": "4001",
            "email": "employee1@company.com",
            "password": "Employee@123",
            "first_name": "Alice",
            "last_name": "Employee",
            "role": UserRole.EMPLOYEE,
            "admin_type": None,
            "department": "Engineering"
        },
        {
            "user_code": "4002",
            "email": "employee2@company.com",
            "password": "Employee@123",
            "first_name": "Bob",
            "last_name": "Employee",
            "role": UserRole.EMPLOYEE,
            "admin_type": None,
            "department": "Engineering"
        },
    ]
    
    created_users = []
    for user_data in users:
        # Check if user already exists
        result = await db.execute(
            select(User).where(User.email == user_data["email"])
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            print(f"  User already exists: {user_data['email']}")
            created_users.append(existing)
            continue
        
        user = User(
            user_code=user_data["user_code"],
            email=user_data["email"],
            hashed_password=get_password_hash(user_data["password"]),
            first_name=user_data["first_name"],
            last_name=user_data["last_name"],
            role=user_data["role"],
            admin_type=user_data.get("admin_type"),
            department=user_data.get("department"),
            is_active=True
        )
        db.add(user)
        created_users.append(user)
        print(f"  Created user: {user_data['email']} (Code: {user_data['user_code']})")
    
    await db.commit()
    return created_users


async def seed_floor_plans(db: AsyncSession, users: list):
    """Seed initial floor plans for each type."""
    # Find the admin users
    desk_admin = next((u for u in users if u.admin_type == AdminType.DESK), users[0])
    cafeteria_admin = next((u for u in users if u.admin_type == AdminType.CAFETERIA), users[0])
    security_admin = next((u for u in users if u.admin_type == AdminType.SECURITY), users[0])
    
    floor_plans_data = [
        {
            "name": "Main Office - Desk Area",
            "plan_type": FloorPlanType.DESK_AREA,
            "rows": 10,
            "columns": 15,
            "description": "Main office desk layout",
            "created_by": desk_admin,
            "cell_types": [CellType.DESK, CellType.PATH, CellType.WALL]
        },
        {
            "name": "Cafeteria - Main Floor",
            "plan_type": FloorPlanType.CAFETERIA,
            "rows": 8,
            "columns": 12,
            "description": "Main cafeteria table layout",
            "created_by": cafeteria_admin,
            "cell_types": [CellType.CAFETERIA_TABLE, CellType.PATH]
        },
        {
            "name": "Parking Basement Level 1",
            "plan_type": FloorPlanType.PARKING,
            "rows": 10,
            "columns": 20,
            "description": "Basement parking slots",
            "created_by": security_admin,
            "cell_types": [CellType.PARKING_SLOT, CellType.PATH]
        },
    ]
    
    created_plans = []
    for fp_data in floor_plans_data:
        # Check if floor plan exists
        result = await db.execute(
            select(FloorPlan).where(FloorPlan.name == fp_data["name"])
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            print(f"  Floor plan already exists: {fp_data['name']}")
            created_plans.append(existing)
            continue
        
        floor_plan = FloorPlan(
            name=fp_data["name"],
            plan_type=fp_data["plan_type"],
            rows=fp_data["rows"],
            columns=fp_data["columns"],
            description=fp_data["description"],
            created_by_id=fp_data["created_by"].id,
            is_active=True
        )
        db.add(floor_plan)
        await db.flush()
        
        # Create initial grid
        grid = create_sample_grid(
            fp_data["rows"], 
            fp_data["columns"], 
            fp_data["cell_types"],
            fp_data["plan_type"]
        )
        
        version = FloorPlanVersion(
            floor_plan_id=floor_plan.id,
            version=1,
            grid_data=grid,
            created_by_id=fp_data["created_by"].id
        )
        db.add(version)
        
        created_plans.append(floor_plan)
        print(f"  Created floor plan: {fp_data['name']}")
    
    await db.commit()
    return created_plans


def create_sample_grid(rows: int, columns: int, cell_types: list, plan_type: FloorPlanType) -> list:
    """Create a sample grid with the given cell types."""
    grid = []
    
    for row in range(rows):
        row_data = []
        for col in range(columns):
            # Default to path
            cell = {"cell_type": CellType.PATH.value, "label": None}
            
            # Outer edges are paths
            if row == 0 or row == rows - 1 or col == 0 or col == columns - 1:
                cell = {"cell_type": CellType.PATH.value, "label": None}
            else:
                # Inner cells based on plan type
                if plan_type == FloorPlanType.DESK_AREA:
                    # Create desk clusters
                    if row % 3 != 0 and col % 3 != 0:
                        cell = {
                            "cell_type": CellType.DESK.value,
                            "label": f"D-{row}-{col}",
                            "capacity": 1
                        }
                elif plan_type == FloorPlanType.CAFETERIA:
                    # Create table layout
                    if row % 2 != 0 and col % 3 != 0:
                        cell = {
                            "cell_type": CellType.CAFETERIA_TABLE.value,
                            "label": f"T-{row}-{col}",
                            "seats": 4
                        }
                elif plan_type == FloorPlanType.PARKING:
                    # Create parking slots
                    if col % 2 != 0 and row % 2 != 0:
                        cell = {
                            "cell_type": CellType.PARKING_SLOT.value,
                            "label": f"P-{row}-{col}",
                            "direction": "up"
                        }
            
            row_data.append(cell)
        grid.append(row_data)
    
    return grid


async def seed_food_items(db: AsyncSession, users: list):
    """Seed sample food items."""
    # Find cafeteria admin to be the creator
    cafeteria_admin = next((u for u in users if u.admin_type == AdminType.CAFETERIA), users[0])
    
    food_items = [
        {"name": "Butter Chicken", "description": "Creamy tomato-based curry", "price": Decimal("12.99"), "category": "Main Course", "tags": ["non-veg", "spicy"], "calories": 450},
        {"name": "Paneer Tikka", "description": "Grilled cottage cheese", "price": Decimal("9.99"), "category": "Starters", "tags": ["vegetarian", "high-protein"], "calories": 280},
        {"name": "Masala Dosa", "description": "Crispy rice crepe with potato filling", "price": Decimal("7.99"), "category": "South Indian", "tags": ["vegetarian", "vegan"], "calories": 320},
        {"name": "Chicken Biryani", "description": "Aromatic rice with chicken", "price": Decimal("14.99"), "category": "Main Course", "tags": ["non-veg", "spicy"], "calories": 520},
        {"name": "Mango Lassi", "description": "Sweet mango yogurt drink", "price": Decimal("3.99"), "category": "Beverages", "tags": ["vegetarian", "sweet"], "calories": 180},
        {"name": "Coffee", "description": "Hot brewed coffee", "price": Decimal("2.49"), "category": "Beverages", "tags": ["vegetarian", "vegan"], "calories": 5},
        {"name": "Tea", "description": "Hot brewed tea", "price": Decimal("1.99"), "category": "Beverages", "tags": ["vegetarian", "vegan"], "calories": 2},
        {"name": "Veg Sandwich", "description": "Fresh vegetable sandwich", "price": Decimal("4.99"), "category": "Snacks", "tags": ["vegetarian", "healthy"], "calories": 250},
    ]
    
    for item_data in food_items:
        result = await db.execute(
            select(FoodItem).where(FoodItem.name == item_data["name"])
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            print(f"  Food item already exists: {item_data['name']}")
            continue
        
        item = FoodItem(
            name=item_data["name"],
            description=item_data["description"],
            price=item_data["price"],
            category=item_data["category"],
            tags=item_data["tags"],
            calories=item_data["calories"],
            is_available=True,
            is_active=True,
            created_by_id=cafeteria_admin.id
        )
        db.add(item)
        print(f"  Created food item: {item_data['name']}")
    
    await db.commit()


async def seed_it_assets(db: AsyncSession):
    """Seed sample IT assets."""
    assets = [
        {"asset_id": "IT-LAP-001", "name": "Dell Laptop 15", "asset_type": AssetType.LAPTOP, "serial_number": "DELL-001", "model": "Latitude 5520", "vendor": "Dell"},
        {"asset_id": "IT-LAP-002", "name": "Dell Laptop 15", "asset_type": AssetType.LAPTOP, "serial_number": "DELL-002", "model": "Latitude 5520", "vendor": "Dell"},
        {"asset_id": "IT-MON-001", "name": "HP Monitor 24", "asset_type": AssetType.MONITOR, "serial_number": "HP-MON-001", "model": "HP E24", "vendor": "HP"},
        {"asset_id": "IT-MON-002", "name": "HP Monitor 24", "asset_type": AssetType.MONITOR, "serial_number": "HP-MON-002", "model": "HP E24", "vendor": "HP"},
        {"asset_id": "IT-KB-001", "name": "Logitech Keyboard", "asset_type": AssetType.KEYBOARD, "serial_number": "LOG-KB-001", "model": "K120", "vendor": "Logitech"},
        {"asset_id": "IT-MS-001", "name": "Logitech Mouse", "asset_type": AssetType.MOUSE, "serial_number": "LOG-MS-001", "model": "M100", "vendor": "Logitech"},
    ]
    
    for asset_data in assets:
        result = await db.execute(
            select(ITAsset).where(ITAsset.serial_number == asset_data["serial_number"])
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            print(f"  IT asset already exists: {asset_data['serial_number']}")
            continue
        
        asset = ITAsset(
            asset_id=asset_data["asset_id"],
            name=asset_data["name"],
            asset_type=asset_data["asset_type"],
            serial_number=asset_data["serial_number"],
            model=asset_data["model"],
            vendor=asset_data["vendor"],
            status=AssetStatus.AVAILABLE,
            is_active=True
        )
        db.add(asset)
        print(f"  Created IT asset: {asset_data['serial_number']}")
    
    await db.commit()


async def main():
    """Main seed function."""
    print("\n========================================")
    print("  UNIFIED OFFICE MANAGEMENT - SEED DATA")
    print("========================================\n")
    
    async with AsyncSessionLocal() as db:
        try:
            print("Creating users...")
            users = await seed_users(db)
            
            print("\nCreating floor plans...")
            await seed_floor_plans(db, users)
            
            print("\nCreating food items...")
            await seed_food_items(db, users)
            
            print("\nCreating IT assets...")
            await seed_it_assets(db)
            
            print("\n========================================")
            print("  SEED DATA COMPLETED SUCCESSFULLY!")
            print("========================================")
            print("\nDefault credentials:")
            print("  Super Admin: super.admin@company.com / Admin@123")
            print("  IT Admin: it.admin@company.com / Admin@123")
            print("  Security Admin: security.admin@company.com / Admin@123")
            print("  Cafeteria Admin: cafeteria.admin@company.com / Admin@123")
            print("  Desk Admin: desk.admin@company.com / Admin@123")
            print("  Manager: manager@company.com / Manager@123")
            print("  Employee: employee1@company.com / Employee@123")
            print("")
            
        except Exception as e:
            print(f"\nError during seeding: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(main())
