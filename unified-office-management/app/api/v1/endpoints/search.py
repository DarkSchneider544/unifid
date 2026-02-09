from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....core.dependencies import get_current_active_user
from ....models.user import User
from ....schemas.search import SemanticSearchRequest, SemanticSearchResponse
from ....schemas.base import APIResponse
from ....services.search_service import SearchService
from ....utils.response import create_response

router = APIRouter()


@router.post("", response_model=APIResponse[SemanticSearchResponse])
async def semantic_search(
    search_request: SemanticSearchRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Perform semantic search across food items or IT assets."""
    search_service = SearchService(db)
    results = await search_service.search(
        query=search_request.query,
        domain=search_request.domain,
        limit=search_request.limit,
        filters=search_request.filters
    )
    
    return create_response(
        data=results,
        message=f"Search completed with {results.total} results"
    )