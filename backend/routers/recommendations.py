"""
Recommendations router for situation-aware movie discovery.

This router provides an endpoint for getting personalized movie recommendations
based on viewing situation (mood, occasion, runtime preference).
"""

from fastapi import APIRouter, HTTPException, Query, Body
from typing import Optional, List
from pydantic import BaseModel, Field
from services.recommendation_service import recommendation_service
from services.tmdb_service import tmdb_service

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


class RecommendationRequest(BaseModel):
    """Request model for situation-aware recommendations."""
    
    mood: str = Field(
        ...,
        description="Viewing mood: relaxed, excited, emotional, or curious"
    )
    occasion: str = Field(
        ...,
        description="Viewing occasion: alone, friends, family, or date"
    )
    runtime_preference: str = Field(
        ...,
        description="Runtime preference: under_90, 90_to_130, or flexible"
    )
    excluded_genres: Optional[List[int]] = Field(
        default=None,
        description="Optional list of genre IDs to exclude"
    )
    count: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Number of recommendations to return (1-100)"
    )


@router.post("/situation-aware")
async def get_situation_aware_recommendations(
    request: RecommendationRequest
):
    """
    Get movie recommendations tailored to your current viewing situation.
    
    This endpoint provides transparent, metadata-based recommendations without
    using AI/ML models. Recommendations are ranked using:
    - Situation fit: How well genres match your mood and occasion
    - Quality: Movie rating weighted by vote confidence
    - Popularity: TMDB popularity score
    
    **Moods:**
    - `relaxed`: Comedy, Documentary, Romance
    - `excited`: Action, Thriller, Adventure
    - `emotional`: Drama, Romance
    - `curious`: Mystery, Science Fiction, Documentary
    
    **Occasions:**
    - `alone`: Any genre (no specific preference)
    - `friends`: Comedy, Action, Thriller
    - `family`: Animation, Family, Adventure
    - `date`: Romance, Comedy, Drama
    
    **Runtime Preferences:**
    - `under_90`: Movies under 90 minutes
    - `90_to_130`: Movies between 90-130 minutes
    - `flexible`: Any runtime
    
    **Example Request:**
    ```json
    {
        "mood": "relaxed",
        "occasion": "date",
        "runtime_preference": "90_to_130",
        "excluded_genres": [27, 53],
        "count": 10
    }
    ```
    
    **Response includes:**
    - Ranked list of recommended movies
    - Score breakdown for each movie
    - Match reason based on metadata
    - Scoring explanation
    
    **Note:** Requires TMDB API key to be configured on the backend.
    """
    try:
        # Check if TMDB is configured
        if not tmdb_service.is_configured:
            raise HTTPException(
                status_code=503,
                detail=(
                    "TMDB API is not configured. Recommendation service requires "
                    "a valid TMDB API key. Please configure TMDB_API_KEY in the "
                    "backend .env file."
                )
            )
        
        # Get recommendations
        result = await recommendation_service.get_situation_aware_recommendations(
            mood=request.mood,
            occasion=request.occasion,
            runtime_preference=request.runtime_preference,
            excluded_genres=request.excluded_genres,
            count=request.count
        )
        
        return result
        
    except ValueError as e:
        # Input validation errors
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        # Log the full error for debugging
        import traceback
        error_detail = f"{type(e).__name__}: {str(e)}"
        print(f"[ERROR] Recommendation request failed: {error_detail}")
        traceback.print_exc()
        
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate recommendations: {error_detail}"
        )


@router.get("/genres")
async def get_available_genres():
    """
    Get list of available genres for use in exclusion filters.
    
    Returns the complete genre mapping used by the recommendation system.
    """
    from services.recommendation_service import GENRE_MAP
    
    genres = [
        {"id": genre_id, "name": name}
        for genre_id, name in GENRE_MAP.items()
    ]
    
    # Sort by name for easier reading
    genres.sort(key=lambda x: x["name"])
    
    return {
        "genres": genres,
        "total": len(genres)
    }


@router.get("/options")
async def get_recommendation_options():
    """
    Get all available options for situation-aware recommendations.
    
    Returns valid values for mood, occasion, and runtime_preference.
    Useful for building frontend UI controls.
    """
    from services.recommendation_service import (
        VALID_MOODS,
        VALID_OCCASIONS,
        VALID_RUNTIME_PREFS
    )
    
    return {
        "moods": sorted(list(VALID_MOODS)),
        "occasions": sorted(list(VALID_OCCASIONS)),
        "runtime_preferences": sorted(list(VALID_RUNTIME_PREFS)),
        "runtime_descriptions": {
            "under_90": "Under 90 minutes",
            "90_to_130": "90 to 130 minutes",
            "flexible": "Any runtime"
        }
    }
