from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from services.tmdb_service import tmdb_service
from services.mock_service import mock_service

router = APIRouter(prefix="/api/series", tags=["series"])


def get_service():
    """Return the appropriate service (TMDB or mock)."""
    return tmdb_service if tmdb_service.is_configured else mock_service


@router.get("/popular")
async def get_popular_series(page: int = Query(1, ge=1, le=500)):
    """Get popular TV series."""
    try:
        service = get_service()
        data = await service.get_popular_series(page=page)
        return data
    except Exception as e:
        print(f"[WARN] Popular series from TMDB failed: {type(e).__name__}: {str(e)}. Falling back to mock data.")
        try:
            return await mock_service.get_popular_series(page=page)
        except Exception:
            raise HTTPException(status_code=500, detail="Failed to retrieve popular series. Please try again later.")



@router.get("/discover")
async def discover_series(
    page: int = Query(1, ge=1, le=500),
    sort_by: str = Query("popularity.desc", pattern="^(popularity|vote_average|first_air_date)\\.(asc|desc)$"),
    with_genres: Optional[str] = None,
    with_original_language: Optional[str] = None,
    first_air_date_year: Optional[int] = Query(None, ge=1900, le=2100)
):
    """Discover TV series with filters."""
    try:
        if not tmdb_service.is_configured:
            # For mock service, just return popular series
            data = await mock_service.get_popular_series(page=page)
            return data
        
        data = await tmdb_service.discover_series(
            page=page,
            sort_by=sort_by,
            with_genres=with_genres,
            with_original_language=with_original_language,
            first_air_date_year=first_air_date_year
        )
        return data
    except Exception as e:
        print(f"[ERROR] Discover series failed: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to discover TV series. Please try again later.")


@router.get("/{series_id}")
async def get_series_details(series_id: int):
    """Get detailed information about a specific TV series."""
    try:
        service = get_service()
        data = await service.get_series_details(series_id)
        return data
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(f"[ERROR] Series details failed for ID {series_id}: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve TV series details. Please try again later.")


@router.get("/genres/list")
async def get_series_genres():
    """Get list of TV series genres."""
    try:
        service = get_service()
        data = await service.get_genres_series()
        return data
    except Exception as e:
        print(f"[ERROR] Series genres failed: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve series genres. Please try again later.")


@router.get("/{series_id}/videos")
async def get_series_videos(series_id: int):
    """Get videos (trailers, teasers) for a specific TV series."""
    try:
        if not tmdb_service.is_configured:
            # Return empty results for mock service
            return {"id": series_id, "results": []}
        
        data = await tmdb_service.get_series_videos(series_id)
        return data
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        import traceback
        print(f"[ERROR] Series videos failed for ID {series_id}: {type(e).__name__}: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed to retrieve series videos. Please try again later.")

