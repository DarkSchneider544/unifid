import enum


class UserRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MANAGER = "manager"
    TEAM_LEAD = "team_lead"
    EMPLOYEE = "employee"


class ManagerDomain(str, enum.Enum):
    PARKING = "parking"
    DESK = "desk"
    CAFETERIA = "cafeteria"
    ATTENDANCE = "attendance"
    IT_SUPPORT = "it_support"
    FLOOR_PLANNING = "floor_planning"
    GENERAL = "general"


class CellType(str, enum.Enum):
    DESK = "desk"
    PARKING_SLOT = "parking_slot"
    CAFETERIA_TABLE = "cafeteria_table"
    PATH = "path"
    WALL = "wall"
    WINDOW = "window"
    ENTRY = "entry"
    EXIT = "exit"
    EMPTY = "empty"


class CellDirection(str, enum.Enum):
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"
    MULTI = "multi"


class ParkingType(str, enum.Enum):
    EMPLOYEE = "employee"
    VISITOR = "visitor"


class BookingStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    PREPARING = "preparing"
    READY = "ready"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class AttendanceStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_MANAGER = "pending_manager"
    APPROVED = "approved"
    REJECTED = "rejected"


class LeaveType(str, enum.Enum):
    SICK = "sick"
    CASUAL = "casual"
    ANNUAL = "annual"
    UNPAID = "unpaid"


class LeaveStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED_LEVEL1 = "approved_level1"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class AssetStatus(str, enum.Enum):
    AVAILABLE = "available"
    ASSIGNED = "assigned"
    MAINTENANCE = "maintenance"
    RETIRED = "retired"


class AssetType(str, enum.Enum):
    LAPTOP = "laptop"
    DESKTOP = "desktop"
    MONITOR = "monitor"
    KEYBOARD = "keyboard"
    MOUSE = "mouse"
    HEADSET = "headset"
    SERVER = "server"
    NETWORK_EQUIPMENT = "network_equipment"
    MOBILE_DEVICE = "mobile_device"
    OTHER = "other"


class ITRequestType(str, enum.Enum):
    REPAIR = "repair"
    REPLACEMENT = "replacement"
    NEW = "new"


class ITRequestStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"


class ProjectStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"