from datetime import datetime, timezone
from typing import TypeVar, Optional, List, Any
import math

from ..schemas.base import APIResponse, PaginatedResponse

T = TypeVar("T")


def create_response(
    data: Optional[T] = None,
    message: str = "",
    success: bool = True
) -> APIResponse[T]:
    """Create a standard API response."""
    return APIResponse(
        success=success,
        data=data,
        message=message,
        timestamp=datetime.now(timezone.utc)
    )


def create_paginated_response(
    data: List[T],
    total: int,
    page: int,
    page_size: int,
    message: str = ""
) -> PaginatedResponse[T]:
    """Create a paginated API response."""
    total_pages = math.ceil(total / page_size) if page_size > 0 else 0
    
    return PaginatedResponse(
        success=True,
        data=data,
        message=message,
        timestamp=datetime.now(timezone.utc),
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )