from pydantic import BaseModel, Field, ConfigDict
from typing import TypeVar, Generic, Optional, List, Any
from datetime import datetime, timezone
import math

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """
    Standard API response format.
    
    All API responses follow this consistent structure:
    - success: Boolean indicating if the request was successful
    - data: The actual response data (can be any type)
    - message: Human-readable message about the operation
    - timestamp: ISO8601 timestamp of the response
    """
    success: bool = True
    data: Optional[T] = None
    message: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None
        }
    )


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Paginated response format for list endpoints.
    
    Extends the standard response with pagination metadata:
    - total: Total number of items across all pages
    - page: Current page number (1-indexed)
    - page_size: Number of items per page
    - total_pages: Total number of pages
    """
    success: bool = True
    data: List[T] = Field(default_factory=list)
    message: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    total: int = 0
    page: int = 1
    page_size: int = 20
    total_pages: int = 0
    
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None
        }
    )
    
    @classmethod
    def create(
        cls,
        data: List[T],
        total: int,
        page: int,
        page_size: int,
        message: str = ""
    ) -> "PaginatedResponse[T]":
        """
        Factory method to create a paginated response with calculated total_pages.
        
        Args:
            data: List of items for the current page
            total: Total count of all items
            page: Current page number
            page_size: Number of items per page
            message: Optional message
            
        Returns:
            PaginatedResponse instance with all fields populated
        """
        total_pages = math.ceil(total / page_size) if page_size > 0 else 0
        
        return cls(
            success=True,
            data=data,
            message=message,
            timestamp=datetime.now(timezone.utc),
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )


class ErrorDetail(BaseModel):
    """
    Detailed error information for validation errors.
    """
    loc: List[str] = Field(default_factory=list, description="Location of the error")
    msg: str = Field(default="", description="Error message")
    type: str = Field(default="", description="Error type")


class ErrorResponse(BaseModel):
    """
    Standard error response format.
    
    Used for returning error details in a consistent format:
    - success: Always False for errors
    - data: Always None for errors
    - message: Human-readable error message
    - errors: List of detailed error information (for validation errors)
    - timestamp: ISO8601 timestamp
    """
    success: bool = False
    data: None = None
    message: str = "An error occurred"
    errors: Optional[List[ErrorDetail]] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None
        }
    )
    
    @classmethod
    def from_exception(
        cls,
        message: str,
        errors: Optional[List[dict]] = None
    ) -> "ErrorResponse":
        """
        Factory method to create an error response from an exception.
        
        Args:
            message: Error message
            errors: Optional list of error details
            
        Returns:
            ErrorResponse instance
        """
        error_details = None
        if errors:
            error_details = [
                ErrorDetail(
                    loc=e.get("loc", []),
                    msg=e.get("msg", ""),
                    type=e.get("type", "")
                )
                for e in errors
            ]
        
        return cls(
            success=False,
            data=None,
            message=message,
            errors=error_details,
            timestamp=datetime.now(timezone.utc)
        )


class HealthCheckResponse(BaseModel):
    """
    Health check response for monitoring endpoints.
    """
    status: str = "healthy"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version: str = "1.0.0"
    database: str = "connected"
    
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None
        }
    )


class MessageResponse(BaseModel):
    """
    Simple message response for operations that don't return data.
    """
    success: bool = True
    message: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None
        }
    )


class BulkOperationResponse(BaseModel):
    """
    Response for bulk operations showing success/failure counts.
    """
    success: bool = True
    message: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    total_processed: int = 0
    successful: int = 0
    failed: int = 0
    errors: Optional[List[dict]] = None
    
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None
        }
    )


class SortOrder(BaseModel):
    """
    Sort order specification for list queries.
    """
    field: str
    direction: str = Field(default="asc", pattern="^(asc|desc)$")


class PaginationParams(BaseModel):
    """
    Common pagination parameters.
    """
    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")
    sort_by: Optional[str] = Field(default=None, description="Field to sort by")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$", description="Sort direction")
    
    @property
    def offset(self) -> int:
        """Calculate the offset for database queries."""
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        """Return the limit (same as page_size)."""
        return self.page_size


class DateRangeFilter(BaseModel):
    """
    Date range filter for queries.
    """
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    def validate_range(self) -> bool:
        """Validate that start_date is before end_date if both are provided."""
        if self.start_date and self.end_date:
            return self.start_date <= self.end_date
        return True


class IDList(BaseModel):
    """
    List of IDs for bulk operations.
    """
    ids: List[str] = Field(..., min_length=1, description="List of IDs")


class StatusUpdate(BaseModel):
    """
    Generic status update schema.
    """
    status: str
    notes: Optional[str] = None
    
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None
        })