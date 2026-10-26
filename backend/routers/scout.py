"""
Scout conversational movie discovery router.

Provides the /api/scout/chat endpoint for natural language movie recommendations.
"""

import uuid
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from services.scout_service import scout_service
from routers.auth import get_current_user
from database import (
    list_conversations,
    get_conversation,
    create_conversation as db_create_conversation,
    delete_conversation as db_delete_conversation,
    add_message_to_conversation
)


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
    conversation_id: Optional[str] = Field(
        default=None,
        description="Optional persistent conversation ID"
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
    conversation_id: Optional[str] = Field(
        default=None,
        description="Associated conversation ID"
    )


class CreateConversationRequest(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = "New Chat"


@router.post("/chat", response_model=ChatResponse)
async def scout_chat(request: ChatRequest, user: Optional[Dict[str, Any]] = Depends(get_current_user)):
    """
    Chat with Scout for conversational movie discovery.
    
    Scout uses Gemini API to interpret natural language requests and returns
    recommendations from the actual TMDB catalog using the existing recommendation engine.
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
        
        user_id = user["id"] if user else None
        conv_id = request.conversation_id
        if conv_id:
            try:
                add_message_to_conversation(
                    conv_id=conv_id,
                    user_id=user_id,
                    role="user",
                    content=request.message,
                    recommendations=None
                )
            except Exception as e:
                print(f"[SCOUT HISTORY] Failed to save user message: {e}")
        
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
        
        recs = result.get("recommendations", [])
        if conv_id:
            try:
                add_message_to_conversation(
                    conv_id=conv_id,
                    user_id=user_id,
                    role="assistant",
                    content=result["message"],
                    recommendations=recs
                )
            except Exception as e:
                print(f"[SCOUT HISTORY] Failed to save assistant message: {e}")
        
        return ChatResponse(
            message=result["message"],
            recommendations=[
                MovieRecommendation(**movie)
                for movie in recs
            ],
            conversation_id=conv_id
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


@router.get("/conversations")
async def get_conversations(user: Optional[Dict[str, Any]] = Depends(get_current_user)):
    """List all saved conversations for current user."""
    user_id = user["id"] if user else None
    return list_conversations(user_id)


@router.post("/conversations")
async def create_new_conversation(req: CreateConversationRequest, user: Optional[Dict[str, Any]] = Depends(get_current_user)):
    """Create a new conversation record."""
    user_id = user["id"] if user else None
    conv_id = req.id or str(uuid.uuid4())
    return db_create_conversation(conv_id, user_id, req.title or "New Chat")


@router.get("/conversations/{conv_id}")
async def get_single_conversation(conv_id: str, user: Optional[Dict[str, Any]] = Depends(get_current_user)):
    """Retrieve an individual conversation and its messages."""
    user_id = user["id"] if user else None
    conv = get_conversation(conv_id, user_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@router.delete("/conversations/{conv_id}")
async def delete_single_conversation(conv_id: str, user: Optional[Dict[str, Any]] = Depends(get_current_user)):
    """Delete a single conversation."""
    user_id = user["id"] if user else None
    deleted = db_delete_conversation(conv_id, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found or access denied")
    return {"success": True, "message": "Conversation deleted"}
