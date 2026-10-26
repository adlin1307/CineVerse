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
        print(f"[ERROR] Multi-search failed: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail="Search failed. Please try again later.")


@router.get("/trending")
async def get_trending(
    media_type: str = Query("all", pattern="^(all|movie|tv)$"),
    time_window: str = Query("week", pattern="^(day|week)$")
):
    """Get trending content."""
    try:
        service = get_service()
        data = await service.get_trending(media_type=media_type, time_window=time_window)
        return data
    except Exception as e:
        print(f"[WARN] Trending from TMDB failed: {type(e).__name__}: {str(e)}. Falling back to mock data.")
        try:
            movies_data = await mock_service.get_popular_movies(1)
            series_data = await mock_service.get_popular_series(1)
            results = (movies_data.get("results", [])[:10]) + (series_data.get("results", [])[:10])
            return {
                "page": 1,
                "results": results,
                "total_pages": 1,
                "total_results": len(results)
            }
        except Exception:
            raise HTTPException(status_code=500, detail="Failed to retrieve trending content. Please try again later.")

