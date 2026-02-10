import enum


class UserRole(str, enum.Enum):
    """
    User roles in the system - determines dashboard and access level.
    
    Hierarchy (Top to Bottom):
    ┌─────────────────────────────────────────────────────────────────┐
    │  SUPER_ADMIN                                                     │
    │       │ creates                                                  │
    │       ▼                                                          │
    │    ADMIN                                                         │
    │       │ creates                                                  │
    │       ▼                                                          │
    │  MANAGER (Parking, Attendance, Desk & Conference, Cafeteria, IT) │
    │       │ creates (Attendance Manager creates department TLs)      │
    │       ▼                                                          │
    │  TEAM_LEAD (Department-wise: Dev, Sales, AI, etc.)               │
    │       │ manages                                                  │
    │       ▼                                                          │
    │  EMPLOYEE (emp1, emp2, emp3...)                                  │
    └─────────────────────────────────────────────────────────────────┘
    
    Approval Flow:
    - EMPLOYEE submits attendance/leave -> TEAM_LEAD approves
    - TEAM_LEAD submits attendance/leave -> MANAGER approves  
    - MANAGER submits attendance/leave -> ADMIN approves
    - ADMIN submits attendance/leave -> SUPER_ADMIN approves
    
    Note: TEAM_LEAD and MANAGER are promoted EMPLOYEEs who can use all 
    employee services plus have approval/management responsibilities.
    """
    SUPER_ADMIN = "super_admin"  # Full system access, creates Admin, approves Admin's attendance/leave
    ADMIN = "admin"              # Creates Managers, approves Manager's attendance/leave
    MANAGER = "manager"          # Department Managers, creates Team Leads, approves TL attendance/leave
    TEAM_LEAD = "team_lead"      # Department Team Leads, manages Employees, approves Employee attendance/leave
    EMPLOYEE = "employee"        # Regular employee


class ManagerType(str, enum.Enum):
    """
    Manager types - determines which department a Manager oversees.
    Each manager type has specific responsibilities.
    
    - PARKING: Manages parking allocation and floor plan
    - ATTENDANCE: Manages attendance tracking, creates department-wise Team Leads
    - DESK_CONFERENCE: Manages desk and conference room allocation
    - CAFETERIA: Manages cafeteria operations (Food Inventory TL, Desk Cafeteria TL)
    - IT_SUPPORT: Manages IT assets and support requests
    """
    PARKING = "parking"                 # Parking Manager - parking floor plan
    ATTENDANCE = "attendance"           # Attendance Manager - creates department TLs
    DESK_CONFERENCE = "desk_conference" # Desk & Conference Manager - desk area floor plan
    CAFETERIA = "cafeteria"             # Cafeteria Manager - cafeteria floor plan, food
    IT_SUPPORT = "it_support"           # IT Support Manager - IT assets, requests


class FloorPlanType(str, enum.Enum):
    """
    Types of floor plans - exactly 3 types, each managed by a specific admin.
    Floor plan IDs are auto-generated.
    
    - PARKING: Managed by SECURITY admin
    - DESK_AREA: Managed by DESK admin (includes conference rooms)
    - CAFETERIA: Managed by CAFETERIA admin (dining area)
    """
    PARKING = "parking"           # Managed by SECURITY admin - parking slot layout
    DESK_AREA = "desk_area"       # Managed by DESK admin - desk & conference room layout
    CAFETERIA = "cafeteria"       # Managed by CAFETERIA admin - dining area layout


class CellType(str, enum.Enum):
    """Cell types for floor plan grid design."""
    DESK = "desk"
    CONFERENCE_ROOM = "conference_room"
    PARKING_SLOT = "parking_slot"
    CAFETERIA_TABLE = "cafeteria_table"
    PATH = "path"
    WALL = "wall"
    WINDOW = "window"
    ENTRY = "entry"
    EXIT = "exit"
    EMPTY = "empty"
    RECEPTION = "reception"
    RESTROOM = "restroom"


class CellDirection(str, enum.Enum):
    """Direction for cells that have orientation."""
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"
    MULTI = "multi"


class ParkingType(str, enum.Enum):
    """Types of parking allocations."""
    EMPLOYEE = "employee"
    VISITOR = "visitor"


class ParkingSlotStatus(str, enum.Enum):
    """Status of parking slots."""
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    DISABLED = "disabled"
    MAINTENANCE = "maintenance"


class VehicleType(str, enum.Enum):
    """Types of vehicles for parking."""
    CAR = "car"
    BIKE = "bike"
    TWO_WHEELER = "two_wheeler"


class BookingStatus(str, enum.Enum):
    """Status for various bookings (desk, cafeteria table, conference room)."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    NO_SHOW = "no_show"


class DeskStatus(str, enum.Enum):
    """Status of desks in the floor plan."""
    AVAILABLE = "available"
    BOOKED = "booked"
    MAINTENANCE = "maintenance"
    DISABLED = "disabled"


class OrderStatus(str, enum.Enum):
    """Status for food orders."""
    PENDING = "pending"
    PREPARING = "preparing"
    READY = "ready"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class AttendanceStatus(str, enum.Enum):
    """
    Attendance approval workflow status.
    
    Flow:
    - DRAFT: Employee marks attendance (check-in/check-out)
    - PENDING_APPROVAL: Employee submits for approval
    - APPROVED: Approved by appropriate authority
    - REJECTED: Rejected by appropriate authority
    
    Approval hierarchy:
    - Employee attendance -> Team Lead approves
    - Team Lead attendance -> Manager approves
    - Manager attendance -> Super Admin approves
    """
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"


class LeaveType(str, enum.Enum):
    """Types of leave available."""
    SICK = "sick"
    CASUAL = "casual"
    ANNUAL = "annual"
    UNPAID = "unpaid"
    MATERNITY = "maternity"
    PATERNITY = "paternity"
    BEREAVEMENT = "bereavement"


class LeaveStatus(str, enum.Enum):
    """
    Leave approval workflow status.
    
    Flow for Employee:
    - PENDING: Applied, waiting for Team Lead approval
    - APPROVED_BY_TEAM_LEAD: Team Lead approved, waiting for Manager
    - APPROVED: Fully approved by Manager
    - REJECTED: Rejected at any level
    
    Flow for Team Lead:
    - PENDING: Applied, waiting for Manager approval
    - APPROVED: Approved by Manager
    - REJECTED: Rejected by Manager
    
    Flow for Manager:
    - PENDING: Applied, waiting for Super Admin approval
    - APPROVED: Approved by Super Admin
    - REJECTED: Rejected by Super Admin
    """
    PENDING = "pending"
    APPROVED_BY_TEAM_LEAD = "approved_by_team_lead"  # For employee leaves
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class AssetStatus(str, enum.Enum):
    """Status of IT assets."""
    AVAILABLE = "available"
    ASSIGNED = "assigned"
    MAINTENANCE = "maintenance"
    RETIRED = "retired"


class AssetType(str, enum.Enum):
    """Types of IT assets."""
    LAPTOP = "laptop"
    DESKTOP = "desktop"
    MONITOR = "monitor"
    KEYBOARD = "keyboard"
    MOUSE = "mouse"
    HEADSET = "headset"
    WEBCAM = "webcam"
    DOCKING_STATION = "docking_station"
    MOBILE_PHONE = "mobile_phone"
    TABLET = "tablet"
    PRINTER = "printer"
    SCANNER = "scanner"
    OTHER = "other"


class ITRequestType(str, enum.Enum):
    """Types of IT requests.
    
    Note: Values must match the database enum exactly (case-sensitive).
    The database enum 'itrequesttype' contains: REPAIR, REPLACEMENT, NEW,
    NEW_ASSET, SOFTWARE_INSTALL, ACCESS_REQUEST, NETWORK_ISSUE, OTHER
    """
    NEW = "NEW"  # Original DB value
    NEW_ASSET = "NEW_ASSET"
    REPAIR = "REPAIR"
    REPLACEMENT = "REPLACEMENT"
    SOFTWARE_INSTALL = "SOFTWARE_INSTALL"
    ACCESS_REQUEST = "ACCESS_REQUEST"
    NETWORK_ISSUE = "NETWORK_ISSUE"
    OTHER = "OTHER"


class ITRequestStatus(str, enum.Enum):
    """Status of IT requests."""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class ITRequestPriority(str, enum.Enum):
    """Priority levels for IT requests."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ProjectStatus(str, enum.Enum):
    """Status of projects."""
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"
    CANCELLED = "cancelled"
    REJECTED = "rejected"