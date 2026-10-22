from fastapi import APIRouter, HTTPException
from services.tmdb_service import tmdb_service
from services.mock_service import mock_service

router = APIRouter(prefix="/api/people", tags=["people"])


def get_service():
    """Return the appropriate service (TMDB or mock)."""
    return tmdb_service if tmdb_service.is_configured else mock_service


@router.get("/{person_id}")
async def get_person_details(person_id: int):
    """Get detailed information about a person (actor/crew member)."""
    try:
        if not tmdb_service.is_configured:
            raise HTTPException(
                status_code=503, 
                detail="TMDB service not configured. Person details require TMDB API."
            )
        
        data = await tmdb_service.get_person_details(person_id)
        return data
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        import traceback
        error_detail = f"{type(e).__name__}: {str(e)}"
        print(f"[ERROR] Person details failed for ID {person_id}: {error_detail}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=error_detail)
