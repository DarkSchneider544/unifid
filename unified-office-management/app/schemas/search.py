from pydantic import BaseModel, Field
from typing import Optional, List, Any
from enum import Enum


class SearchDomain(str, Enum):
    FOOD = "food"
    IT_ASSETS = "it_assets"


class SemanticSearchRequest(BaseModel):
    """Semantic search request schema."""
    query: str = Field(..., min_length=1, max_length=500)
    domain: SearchDomain
    limit: int = Field(default=10, ge=1, le=100)
    filters: Optional[dict] = None  # Additional filters like category, tags, etc.


class SearchResultItem(BaseModel):
    """Individual search result."""
    id: str
    name: str
    description: Optional[str] = None
    score: float
    metadata: dict = {}


class SemanticSearchResponse(BaseModel):
    """Semantic search response schema."""
    query: str
    domain: SearchDomain
    results: List[SearchResultItem]
    total: int
    search_type: str  # "semantic", "keyword", "hybrid"