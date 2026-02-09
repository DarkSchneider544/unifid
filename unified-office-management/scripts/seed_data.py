"""
Seed data script for initial setup.
Run with: python -m scripts.seed_data
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash
from app.models.user import User
from app.models.building import Building
from app.models.floor_plan import FloorPlan, FloorPlanVersion
from app.models.food import FoodItem
from app.models.it_asset import ITAsset
from app.models.leave import LeaveType as LeaveTypeModel
from app.models.enums import (
    UserRole, ManagerDomain, CellType, LeaveType, AssetType, AssetStatus
)
from decimal import Decimal
import uuid


async def seed_users(db: AsyncSession):
    """Seed initial users."""
    users = [
        {
            "employee_id": "SADMIN-001",
            "email": "super.admin@company.com",
            "password": "Admin@123",
            "first_name": "Super",
            "last_name": "Admin",
            "role": UserRole.SUPER_ADMIN,
            "department": "Administration"
        },
        {
            "employee_id": "ADMIN-001",
            "email": "admin.user@company.com",
            "password": "Admin@123",
            "first_name": "Admin",
            "last_name": "User",
            "role": UserRole.ADMIN,
            "department": "Administration"
        },
        {
            "employee_id": "MGR-PKG-001",
            "email": "parking.manager@company.com",
            "password": "Manager@123",
            "first_name": "Parking",
            "last_name": "Manager",
            "role": UserRole.MANAGER,
            "manager_domain": ManagerDomain.PARKING,
            "department": "Facilities"
        },
        {
            "employee_id": "MGR-CAF-001",
            "email": "cafeteria.manager@company.com",
            "password": "Manager@123",
            "first_name": "Cafeteria",
            "last_name": "Manager",
            "role": UserRole.MANAGER,
            "manager_domain": ManagerDomain.CAFETERIA,
            "department": "Food Services"
        },
        {
            "employee_id": "MGR-IT-001",
            "email": "it.manager@company.com",
            "password": "Manager@123",
            "first_name": "IT",
            "last_name": "Manager",
            "role": UserRole.MANAGER,
            "manager_domain": ManagerDomain.IT_SUPPORT,
            "department": "IT"
        },
        {
            "employee_id": "TL-001",
            "email": "team.lead@company.com",
            "password": "TeamLead@123",
            "first_name": "Team",
            "last_name": "Lead",
            "role": UserRole.TEAM_LEAD,
            "is_team_lead": True,
            "department": "Engineering"
        },
        {
            "employee_id": "EMP-001",
            "email": "john.doe@company.com",
            "password": "Employee@123",
            "first_name": "John",
            "last_name": "Doe",
            "role": UserRole.EMPLOYEE,
            "department": "Engineering"
        },
        {
            "employee_id": "EMP-002",
            "email": "jane.smith@company.com",
            "password": "Employee@123",
            "first_name": "Jane",
            "last_name": "Smith",
            "role": UserRole.EMPLOYEE,
            "department": "Engineering"
        },
    ]
    
    created_users = {}
    for user_data in users:
        password = user_data.pop("password")
        user = User(
            **user_data,
            hashed_password=get_password_hash(password),
            is_active=True
        )
        db.add(user)
        await db.flush()
        created_users[user_data["employee_id"]] = user
        print(f"Created user: {user_data['email']}")
    
    # Set team lead for employees
    team_lead = created_users.get("TL-001")
    if team_lead:
        for emp_id in ["EMP-001", "EMP-002"]:
            if emp_id in created_users:
                created_users[emp_id].team_lead_id = team_lead.id
    
    await db.commit()
    return created_users


async def seed_buildings(db: AsyncSession, admin_user: User):
    """Seed buildings and floor plans."""
    # Create main building
    building = Building(
        name="Main Office Building",
        code="MAIN-01",
        address="123 Business Park, Tech City",
        total_floors=5,
        has_basement=True,
        basement_floors=2,
        description="Main corporate headquarters"
    )
    db.add(building)
    await db.flush()
    print(f"Created building: {building.name}")
    
    # Create floor plans
    floors = [
        {"floor_number": -2, "name": "Basement 2 - Parking", "is_basement": True},
        {"floor_number": -1, "name": "Basement 1 - Parking", "is_basement": True},
        {"floor_number": 0, "name": "Ground Floor - Reception"},
        {"floor_number": 1, "name": "First Floor - Office"},
        {"floor_number": 2, "name": "Second Floor - Cafeteria"},
    ]
    
    for floor_data in floors:
        # Create 10x10 grid
        rows, cols = 10, 10
        grid_data = []
        
        for r in range(rows):
            row = []
            for c in range(cols):
                if floor_data["floor_number"] < 0:
                    # Parking floor
                    if r == 0 or r == rows - 1 or c == 0 or c == cols - 1:
                        cell = {"cell_type": "wall"}
                    elif r == rows // 2:
                        cell = {"cell_type": "path"}
                    elif c == 0:
                        cell = {"cell_type": "entry", "label": "Entry"}
                    elif c == cols - 1:
                        cell = {"cell_type": "exit", "label": "Exit"}
                    else:
                        cell = {
                            "cell_type": "parking_slot",
                            "label": f"P{abs(floor_data['floor_number'])}-{r}{c}"
                        }
                elif floor_data["floor_number"] == 2:
                    # Cafeteria floor
                    if r == 0 or r == rows - 1 or c == 0 or c == cols - 1:
                        cell = {"cell_type": "wall"}
                    elif r < 2 or c < 2:
                        cell = {"cell_type": "path"}
                    elif r % 2 == 0 and c % 2 == 0:
                        cell = {
                            "cell_type": "cafeteria_table",
                            "label": f"T-{r}{c}"
                        }
                    else:
                        cell = {"cell_type": "empty"}
                else:
                    # Office floor
                    if r == 0 or r == rows - 1 or c == 0 or c == cols - 1:
                        cell = {"cell_type": "wall"}
                    elif c == 1:
                        cell = {"cell_type": "path"}
                    elif r % 2 == 0 and c > 1:
                        cell = {
                            "cell_type": "desk",
                            "label": f"D{floor_data['floor_number']}-{r}{c}",
                            "is_active": True
                        }
                    else:
                        cell = {"cell_type": "empty"}
                
                row.append(cell)
            grid_data.append(row)
        
        floor_plan = FloorPlan(
            building_id=building.id,
            name=floor_data["name"],
            floor_number=floor_data["floor_number"],
            rows=rows,
            columns=cols,
            is_basement=floor_data.get("is_basement", False),
            current_version=1
        )
        db.add(floor_plan)
        await db.flush()
        
        version = FloorPlanVersion(
            floor_plan_id=floor_plan.id,
            version=1,
            grid_data=grid_data,
            created_by_id=admin_user.id,
            change_notes="Initial version"
        )
        db.add(version)
        print(f"Created floor plan: {floor_data['name']}")
    
    await db.commit()
    return building


async def seed_leave_types(db: AsyncSession):
    """Seed leave types."""
    leave_types = [
        {
            "name": "Sick Leave",
            "code": LeaveType.SICK,
            "default_days": 12,
            "is_paid": True,
            "description": "Leave for illness or medical appointments"
        },
        {
            "name": "Casual Leave",
            "code": LeaveType.CASUAL,
            "default_days": 12,
            "is_paid": True,
            "description": "Leave for personal matters"
        },
        {
            "name": "Annual Leave",
            "code": LeaveType.ANNUAL,
            "default_days": 20,
            "is_paid": True,
            "description": "Annual vacation leave"
        },
        {
            "name": "Unpaid Leave",
            "code": LeaveType.UNPAID,
            "default_days": 0,
            "is_paid": False,
            "description": "Leave without pay"
        },
    ]
    
    for lt_data in leave_types:
        leave_type = LeaveTypeModel(**lt_data, is_active=True)
        db.add(leave_type)
        print(f"Created leave type: {lt_data['name']}")
    
    await db.commit()


async def seed_food_items(db: AsyncSession, admin_user: User):
    """Seed food menu items."""
    food_items = [
        {
            "name": "Grilled Chicken Salad",
            "description": "Fresh garden salad with grilled chicken breast, cherry tomatoes, and balsamic dressing",
            "category": "Salads",
            "price": Decimal("12.99"),
            "ingredients": ["chicken", "lettuce", "tomatoes", "cucumber", "balsamic"],
            "tags": ["high-protein", "healthy", "gluten-free"],
            "calories": 350,
            "preparation_time_minutes": 10
        },
        {
            "name": "Veggie Wrap",
            "description": "Whole wheat wrap with hummus, grilled vegetables, and feta cheese",
            "category": "Wraps",
            "price": Decimal("9.99"),
            "ingredients": ["tortilla", "hummus", "peppers", "zucchini", "feta"],
            "tags": ["vegetarian", "healthy"],
            "calories": 420,
            "preparation_time_minutes": 8
        },
        {
            "name": "Spicy Thai Noodles",
            "description": "Rice noodles with vegetables in spicy peanut sauce",
            "category": "Main Course",
            "price": Decimal("11.99"),
            "ingredients": ["rice noodles", "vegetables", "peanuts", "thai sauce"],
            "tags": ["spicy", "vegan", "asian"],
            "calories": 550,
            "preparation_time_minutes": 15
        },
        {
            "name": "Protein Power Bowl",
            "description": "Quinoa bowl with grilled chicken, eggs, avocado, and mixed greens",
            "category": "Bowls",
            "price": Decimal("14.99"),
            "ingredients": ["quinoa", "chicken", "eggs", "avocado", "greens"],
            "tags": ["high-protein", "healthy", "keto-friendly"],
            "calories": 650,
            "preparation_time_minutes": 12
        },
        {
            "name": "Fresh Fruit Smoothie",
            "description": "Blend of seasonal fruits with yogurt and honey",
            "category": "Beverages",
            "price": Decimal("5.99"),
            "ingredients": ["banana", "strawberry", "yogurt", "honey"],
            "tags": ["healthy", "low-sugar", "vegetarian"],
            "calories": 180,
            "preparation_time_minutes": 5
        },
        {
            "name": "Classic Burger",
            "description": "Angus beef patty with lettuce, tomato, and special sauce",
            "category": "Main Course",
            "price": Decimal("13.99"),
            "ingredients": ["beef patty", "bun", "lettuce", "tomato", "cheese"],
            "tags": ["comfort-food"],
            "calories": 750,
            "preparation_time_minutes": 15
        },
    ]
    
    for item_data in food_items:
        food_item = FoodItem(
            **item_data,
            created_by_id=admin_user.id,
            is_available=True,
            is_active=True
        )
        db.add(food_item)
        print(f"Created food item: {item_data['name']}")
    
    await db.commit()


async def seed_it_assets(db: AsyncSession):
    """Seed IT assets."""
    assets = [
        {
            "asset_id": "LAP-001",
            "name": "MacBook Pro 16",
            "asset_type": AssetType.LAPTOP,
            "description": "16-inch MacBook Pro with M3 Pro chip",
            "vendor": "Apple",
            "model": "MacBook Pro 16 2023",
            "serial_number": "C02ZX1234567",
            "specifications": {
                "processor": "Apple M3 Pro",
                "memory": "32GB",
                "storage": "1TB SSD",
                "display": "16.2-inch Liquid Retina XDR"
            },
            "tags": ["development", "high-performance", "portable"],
            "purchase_price": Decimal("3499.00")
        },
        {
            "asset_id": "LAP-002",
            "name": "Dell XPS 15",
            "asset_type": AssetType.LAPTOP,
            "description": "Dell XPS 15 with Intel Core i9",
            "vendor": "Dell",
            "model": "XPS 15 9530",
            "serial_number": "DELL1234567890",
            "specifications": {
                "processor": "Intel Core i9-13900H",
                "memory": "64GB DDR5",
                "storage": "2TB NVMe SSD",
                "display": "15.6-inch OLED 3.5K"
            },
            "tags": ["development", "high-memory", "ML-workloads"],
            "purchase_price": Decimal("2899.00")
        },
        {
            "asset_id": "MON-001",
            "name": "Dell UltraSharp 32",
            "asset_type": AssetType.MONITOR,
            "description": "32-inch 4K USB-C Hub Monitor",
            "vendor": "Dell",
            "model": "U3223QE",
            "serial_number": "MON1234567890",
            "specifications": {
                "resolution": "3840x2160",
                "size": "32 inches",
                "panel": "IPS Black",
                "ports": "USB-C, HDMI, DisplayPort"
            },
            "tags": ["4k", "usb-c", "color-accurate"],
            "purchase_price": Decimal("899.00")
        },
        {
            "asset_id": "SRV-001",
            "name": "Dell PowerEdge R750",
            "asset_type": AssetType.SERVER,
            "description": "Enterprise rack server for ML workloads",
            "vendor": "Dell",
            "model": "PowerEdge R750",
            "serial_number": "SRV1234567890",
            "specifications": {
                "processor": "2x Intel Xeon Gold 6348",
                "memory": "512GB DDR4",
                "storage": "8x 3.84TB NVMe SSD",
                "gpu": "2x NVIDIA A100"
            },
            "tags": ["server", "ML-workloads", "high-memory", "gpu"],
            "purchase_price": Decimal("45000.00")
        },
        {
            "asset_id": "MSE-001",
            "name": "Logitech MX Master 3",
            "asset_type": AssetType.MOUSE,
            "description": "Wireless ergonomic mouse",
            "vendor": "Logitech",
            "model": "MX Master 3",
            "serial_number": "MSE1234567890",
            "specifications": {
                "connectivity": "Bluetooth, USB receiver",
                "battery": "Rechargeable, 70 days",
                "dpi": "4000"
            },
            "tags": ["wireless", "ergonomic"],
            "purchase_price": Decimal("99.00")
        },
    ]
    
    for asset_data in assets:
        asset = ITAsset(
            **asset_data,
            status=AssetStatus.AVAILABLE,
            is_active=True
        )
        db.add(asset)
        print(f"Created IT asset: {asset_data['name']}")
    
    await db.commit()


async def main():
    """Main seed function."""
    print("Starting database seeding...")
    
    async with AsyncSessionLocal() as db:
        try:
            # Seed users first
            print("\n--- Seeding Users ---")
            users = await seed_users(db)
            admin_user = users.get("ADMIN-001")
            
            # Seed buildings and floor plans
            print("\n--- Seeding Buildings & Floor Plans ---")
            await seed_buildings(db, admin_user)
            
            # Seed leave types
            print("\n--- Seeding Leave Types ---")
            await seed_leave_types(db)
            
            # Seed food items
            print("\n--- Seeding Food Items ---")
            await seed_food_items(db, admin_user)
            
            # Seed IT assets
            print("\n--- Seeding IT Assets ---")
            await seed_it_assets(db)
            
            print("\n✅ Database seeding completed successfully!")
            print("\nDefault credentials:")
            print("  Super Admin: super.admin@company.com / Admin@123")
            print("  Admin: admin.user@company.com / Admin@123")
            print("  Manager: parking.manager@company.com / Manager@123")
            print("  Team Lead: team.lead@company.com / TeamLead@123")
            print("  Employee: john.doe@company.com / Employee@123")
            
        except Exception as e:
            print(f"❌ Error during seeding: {e}")
            await db.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(main())