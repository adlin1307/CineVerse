"""
Scout conversational movie discovery router.

Provides the /api/scout/chat endpoint for natural language movie recommendations.
"""

from fastapi import APIRouter, HTTPException
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from services.scout_service import scout_service


router = APIRouter(prefix="/api/scout", tags=["scout"])


class ConversationMessage(BaseModel):
    """A message in the conversation history."""
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    recommendations: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Optional list of recommendations from previous assistant turn"
    )


class ChatRequest(BaseModel):
    """Request model for Scout chat endpoint."""
    message: str = Field(..., min_length=1, description="User's message")
    conversation_history: List[ConversationMessage] = Field(
        default=[],
        description="Previous conversation messages for context"
    )


class MovieRecommendation(BaseModel):
    """A recommendation from Scout (movie or TV series)."""
    id: int
    title: str
    poster_path: Optional[str] = None
    vote_average: Optional[float] = None
    release_date: Optional[str] = None
    media_type: str = Field(default="movie", description="'movie' or 'tv'")
    explanation: Optional[str] = None
    analysis: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Structured selection analysis with verified evidence"
    )


class ChatResponse(BaseModel):
    """Response model for Scout chat endpoint."""
    message: str = Field(..., description="Scout's response message")
    recommendations: List[MovieRecommendation] = Field(
        default=[],
        description="Movie recommendations (if applicable)"
    )


@router.post("/chat", response_model=ChatResponse)
async def scout_chat(request: ChatRequest):
    """
    Chat with Scout for conversational movie discovery.
    
    Scout uses Gemini API to interpret natural language requests and returns
    recommendations from the actual TMDB catalog using the existing recommendation engine.
    
    **Scout's Personality:**
    - Witty, cheeky, and movie-obsessed
    - Conversational and helpful without being generic
    - Remembers context within the conversation
    
    **Supported Requests:**
    - "Find something fun for tonight"
    - "Recommend an underrated thriller"
    - "Something emotional but not too long"
    - "No horror this time" (refines previous preferences)
    - "Make it shorter" (adjusts runtime)
    - "Try again" (different recommendations with same criteria)
    
    **Context Management:**
    - Maintains preferences across the conversation (genres, runtime, mood)
    - Accumulates exclusions ("no horror", "skip comedies")
    - Asks clarifying questions only when critical info is missing
    
    **Example Request:**
    ```json
    {
        "message": "I want something fun for tonight",
        "conversation_history": []
    }
    ```
    
    **Example Response:**
    ```json
    {
        "message": "Fun vibes, got it! Pulling some crowd-pleasers.",
        "recommendations": [
            {
                "id": 123,
                "title": "Movie Title",
                "poster_path": "/path.jpg",
                "vote_average": 7.5,
                "release_date": "2024-01-15",
                "explanation": "Perfect for a chill watch"
            }
        ]
    }
    ```
    
    **Error Handling:**
    - 503: Gemini API not configured (GEMINI_API_KEY required in backend/.env)
    - 429: Rate limit exceeded (try again in a moment)
    - 500: Processing error (API timeout, invalid response, etc.)
    
    **Note:** Requires GEMINI_API_KEY to be configured in backend/.env
    """
    try:
        # Check if Scout service is configured
        if not scout_service.gemini_configured:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Scout is not configured. The Gemini API key is required. "
                    "Please set GEMINI_API_KEY in the backend/.env file."
                )
            )
        
        # Process message with Scout
        result = await scout_service.process_message(
            user_message=request.message,
            conversation_history=[
                {
                    "role": msg.role,
                    "content": msg.content,
                    "recommendations": msg.recommendations
                }
                for msg in request.conversation_history
            ]
        )
        
        return ChatResponse(
            message=result["message"],
            recommendations=[
                MovieRecommendation(**movie)
                for movie in result.get("recommendations", [])
            ]
        )
    
    except ValueError as e:
        # Configuration or validation errors
        error_msg = str(e)
        if "not configured" in error_msg.lower():
            raise HTTPException(status_code=503, detail=error_msg)
        elif "timeout" in error_msg.lower() or "timed out" in error_msg.lower() or "too long" in error_msg.lower():
            raise HTTPException(status_code=504, detail="Scout is taking a bit too long to fetch recommendations. Please try again.")
        elif "rate limit" in error_msg.lower() or "overwhelmed" in error_msg.lower():
            raise HTTPException(status_code=429, detail=error_msg)
        else:
            raise HTTPException(status_code=400, detail=error_msg)
    
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    
    except Exception as e:
        # User-friendly errors from scout_service
        error_msg = str(e)
        
        # Map error types to status codes
        if "rate limit" in error_msg.lower() or "overwhelmed" in error_msg:
            status_code = 429
        elif "timeout" in error_msg.lower() or "timed out" in error_msg.lower() or "too long" in error_msg.lower():
            status_code = 504
            error_msg = "Scout is taking a bit too long to fetch recommendations. Please try again."
        elif "not configured" in error_msg.lower():
            status_code = 503
        else:
            status_code = 500
        
        raise HTTPException(status_code=status_code, detail=error_msg)


@router.get("/health")
async def scout_health():
    """
    Check Scout service health and configuration status.
    
    Returns:
        - configured: Whether Gemini API key is set
        - model: Configured Gemini model
        - tmdb_configured: Whether TMDB API is available
    """
    from config import settings
    from services.tmdb_service import tmdb_service
    
    return {
        "configured": scout_service.gemini_configured,
        "model": settings.gemini_model,
        "tmdb_configured": tmdb_service.is_configured
    }
