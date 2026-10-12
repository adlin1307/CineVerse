from fastapi import APIRouter, HTTPException, Query
from services.tmdb_service import tmdb_service
from services.mock_service import mock_service

router = APIRouter(prefix="/api/search", tags=["search"])


def get_service():
    """Return the appropriate service (TMDB or mock)."""
    return tmdb_service if tmdb_service.is_configured else mock_service


@router.get("/multi")
async def search_multi(
    query: str = Query(..., min_length=1),
    page: int = Query(1, ge=1, le=500)
):
    """Search for movies, TV series, and people."""
    try:
        service = get_service()
        data = await service.search_multi(query=query, page=page)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trending")
async def get_trending(
    media_type: str = Query("all", regex="^(all|movie|tv)$"),
    time_window: str = Query("week", regex="^(day|week)$")
):
    """Get trending content."""
    try:
        service = get_service()
        data = await service.get_trending(media_type=media_type, time_window=time_window)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
