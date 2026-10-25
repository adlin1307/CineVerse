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
        service = get_service()
        data = await service.get_person_details(person_id)
        return data
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        import traceback
        print(f"[ERROR] Person details failed for ID {person_id}: {type(e).__name__}: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed to retrieve person details. Please try again later.")
