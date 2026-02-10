from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Any
from datetime import datetime
from uuid import UUID

from ..models.enums import CellType, CellDirection, FloorPlanType, ManagerType


class CellConfig(BaseModel):
    """Individual cell configuration in the floor plan grid."""
    row: int = Field(..., ge=0)
    column: int = Field(..., ge=0)
    cell_type: CellType
    label: Optional[str] = None
    direction: Optional[CellDirection] = None
    is_active: bool = True
    capacity: Optional[int] = None  # For tables, conference rooms
    metadata: Optional[dict] = None


class GridData(BaseModel):
    """Grid data structure."""
    cells: List[List[CellConfig]]
    
    @field_validator('cells')
    @classmethod
    def validate_grid(cls, v):
        if not v:
            raise ValueError('Grid cannot be empty')
        row_length = len(v[0]) if v else 0
        for row in v:
            if len(row) != row_length:
                raise ValueError('All rows must have the same number of columns')
        return v


class FloorPlanBase(BaseModel):
    """
    Base floor plan schema.
    
    There are exactly 3 floor plan types:
    - PARKING: Managed by SECURITY admin
    - DESK_AREA: Managed by DESK admin
    - CAFETERIA: Managed by CAFETERIA admin
    
    floor_code is auto-generated based on type (e.g., PKG-1234, DSK-5678, CAF-9012)
    """
    name: str = Field(..., min_length=1, max_length=200)
    plan_type: FloorPlanType  # PARKING, DESK_AREA, or CAFETERIA
    rows: int = Field(..., ge=1, le=100)
    columns: int = Field(..., ge=1, le=100)
    description: Optional[str] = None
    building_name: Optional[str] = None
    floor_number: Optional[str] = None


class FloorPlanCreate(FloorPlanBase):
    """
    Floor plan creation schema.
    
    Only the respective admin can create each type:
    - SECURITY admin: PARKING floor plan
    - DESK admin: DESK_AREA floor plan
    - CAFETERIA admin: CAFETERIA floor plan
    """
    grid_data: List[List[dict]]  # Initial grid configuration
    
    @field_validator('grid_data')
    @classmethod
    def validate_grid_data(cls, v, info):
        rows = info.data.get('rows', 0)
        columns = info.data.get('columns', 0)
        if len(v) != rows:
            raise ValueError(f'Grid must have exactly {rows} rows')
        for row in v:
            if len(row) != columns:
                raise ValueError(f'Each row must have exactly {columns} columns')
        return v


class FloorPlanUpdate(BaseModel):
    """Floor plan update schema."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    is_active: Optional[bool] = None
    description: Optional[str] = None
    building_name: Optional[str] = None
    floor_number: Optional[str] = None


class FloorPlanVersionCreate(BaseModel):
    """Floor plan version creation schema (for updating grid layout)."""
    grid_data: List[List[dict]]
    change_notes: Optional[str] = None


class FloorPlanVersionResponse(BaseModel):
    """Floor plan version response schema."""
    id: UUID
    floor_plan_id: UUID
    version: int
    grid_data: Any
    is_active: bool
    created_by_code: str
    created_by_name: Optional[str] = None
    change_notes: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class FloorPlanResponse(BaseModel):
    """Floor plan response schema with auto-generated floor_code."""
    id: UUID
    floor_code: str  # Auto-generated: PKG-XXXX, DSK-XXXX, or CAF-XXXX
    name: str
    plan_type: FloorPlanType
    rows: int
    columns: int
    is_active: bool
    description: Optional[str] = None
    building_name: Optional[str] = None
    floor_number: Optional[str] = None
    current_version: int
    created_by_code: str
    created_by_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    latest_grid: Optional[Any] = None
    
    class Config:
        from_attributes = True


class FloorPlanDetailResponse(FloorPlanResponse):
    """Detailed floor plan with version history."""
    versions: List[FloorPlanVersionResponse] = []
    
    class Config:
        from_attributes = True


class FloorPlanListResponse(BaseModel):
    """Floor plan list response schema."""
    floor_plans: List[FloorPlanResponse]
    total: int
    page: int
    page_size: int


class FloorPlanTypeInfo(BaseModel):
    """Information about a floor plan type."""
    plan_type: FloorPlanType
    manager_type: ManagerType
    description: str
    current_floor_plan: Optional[FloorPlanResponse] = None