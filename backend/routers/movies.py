from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from services.tmdb_service import tmdb_service
from services.mock_service import mock_service
from config import settings

router = APIRouter(prefix="/api/movies", tags=["movies"])


def get_service():
    """Return the appropriate service (TMDB or mock)."""
    return tmdb_service if tmdb_service.is_configured else mock_service


@router.get("/popular")
async def get_popular_movies(page: int = Query(1, ge=1, le=500)):
    """Get popular movies."""
    try:
        service = get_service()
        data = await service.get_popular_movies(page=page)
        return data
    except Exception as e:
        print(f"[WARN] Popular movies from TMDB failed: {type(e).__name__}: {str(e)}. Falling back to mock data.")
        try:
            return await mock_service.get_popular_movies(page=page)
        except Exception:
            raise HTTPException(status_code=500, detail="Failed to retrieve popular movies. Please try again later.")



@router.get("/discover")
async def discover_movies(
    page: int = Query(1, ge=1, le=500),
    sort_by: str = Query("popularity.desc", pattern="^(popularity|vote_average|release_date)\\.(asc|desc)$"),
    with_genres: Optional[str] = None,
    with_original_language: Optional[str] = None,
    year: Optional[int] = Query(None, ge=1900, le=2100)
):
    """Discover movies with filters."""
    try:
        if not tmdb_service.is_configured:
            # For mock service, just return popular movies
            data = await mock_service.get_popular_movies(page=page)
            return data
        
        data = await tmdb_service.discover_movies(
            page=page,
            sort_by=sort_by,
            with_genres=with_genres,
            with_original_language=with_original_language,
            year=year
        )
        return data
    except Exception as e:
        print(f"[ERROR] Discover movies failed: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to discover movies. Please try again later.")


@router.get("/{movie_id}")
async def get_movie_details(movie_id: int):
    """Get detailed information about a specific movie."""
    try:
        service = get_service()
        data = await service.get_movie_details(movie_id)
        return data
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        import traceback
        print(f"[ERROR] Movie details failed for ID {movie_id}: {type(e).__name__}: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed to retrieve movie details. Please try again later.")


@router.get("/genres/list")
async def get_movie_genres():
    """Get list of movie genres."""
    try:
        service = get_service()
        data = await service.get_genres_movies()
        return data
    except Exception as e:
        print(f"[ERROR] Movie genres failed: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve movie genres. Please try again later.")


@router.get("/{movie_id}/videos")
async def get_movie_videos(movie_id: int):
    """Get videos (trailers, teasers) for a specific movie."""
    try:
        if not tmdb_service.is_configured:
            # Return empty results for mock service
            return {"id": movie_id, "results": []}
        
        data = await tmdb_service.get_movie_videos(movie_id)
        return data
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        import traceback
        print(f"[ERROR] Movie videos failed for ID {movie_id}: {type(e).__name__}: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed to retrieve movie videos. Please try again later.")

