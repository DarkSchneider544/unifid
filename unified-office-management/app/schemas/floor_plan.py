from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Any
from datetime import datetime
from uuid import UUID

from ..models.enums import CellType, CellDirection


class CellConfig(BaseModel):
    """Individual cell configuration."""
    row: int = Field(..., ge=0)
    column: int = Field(..., ge=0)
    cell_type: CellType
    label: Optional[str] = None
    direction: Optional[CellDirection] = None
    is_active: bool = True
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
    """Base floor plan schema."""
    name: str = Field(..., min_length=1, max_length=200)
    floor_number: int
    rows: int = Field(..., ge=1, le=100)
    columns: int = Field(..., ge=1, le=100)
    is_basement: bool = False
    description: Optional[str] = None


class FloorPlanCreate(FloorPlanBase):
    """Floor plan creation schema."""
    building_id: UUID
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


class FloorPlanVersionCreate(BaseModel):
    """Floor plan version creation schema."""
    grid_data: List[List[dict]]
    change_notes: Optional[str] = None


class FloorPlanVersionResponse(BaseModel):
    """Floor plan version response schema."""
    id: UUID
    floor_plan_id: UUID
    version: int
    grid_data: Any
    is_active: bool
    created_by_id: UUID
    change_notes: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class FloorPlanResponse(BaseModel):
    """Floor plan response schema."""
    id: UUID
    building_id: UUID
    name: str
    floor_number: int
    rows: int
    columns: int
    is_active: bool
    is_basement: bool
    description: Optional[str] = None
    current_version: int
    created_at: datetime
    updated_at: datetime
    latest_grid: Optional[Any] = None
    
    class Config:
        from_attributes = True