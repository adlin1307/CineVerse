"""
Conversation state schemas.

These models represent the current state of a conversation,
including temporary constraints and context for state transitions.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime, UTC
from pydantic import BaseModel, Field, field_validator, ConfigDict

from models.intent import MediaType


class StateTransition(str, Enum):
    """Type of state transition."""
    INITIALIZE = "initialize"  # Start new conversation
    APPLY_FRESH = "apply_fresh"  # Fresh search, clear unrelated state
    APPLY_REFINEMENT = "apply_refinement"  # Modify current search
    APPLY_CONSTRAINT = "apply_constraint"  # Add constraint to current
    APPLY_CORRECTION = "apply_correction"  # Override previous value
    TITLE_QUESTION = "title_question"  # Ask about previous recommendation
    CLEAR = "clear"  # Reset conversation state


class TemporaryConstraints(BaseModel):
    """
    Temporary constraints active in current conversation.
    
    These are reset when starting a fresh search or clearing conversation.
    They do NOT persist across sessions.
    """
    
    # Genre constraints
    include_genres: List[int] = Field(
        default_factory=list,
        description="Genre IDs to include in current search"
    )
    
    exclude_genres: List[int] = Field(
        default_factory=list,
        description="Genre IDs to exclude in current search"
    )
    
    # Media type
    media_type: Optional[MediaType] = Field(
        default=None,
        description="Current media type filter"
    )
    
    # Mood and tone
    mood: Optional[str] = Field(
        default=None,
        description="Current mood (relaxed, excited, emotional, curious)"
    )
    
    emotional_sub_intent: Optional[str] = Field(
        default=None,
        description="Current emotional sub-intent (tearjerker, feelgood, etc.)"
    )
    
    tone_modifiers: List[str] = Field(
        default_factory=list,
        description="Active tone modifiers (darker, lighter, intense)"
    )
    
    # Streaming provider (temporary - not a long-term preference)
    provider_id: Optional[int] = Field(
        default=None,
        description="Currently active provider filter"
    )
    
    provider_name: Optional[str] = Field(
        default=None,
        description="Provider name for display"
    )
    
    watch_region: str = Field(
        default="IN",
        description="Current watch region"
    )
    
    # Additional filters
    min_year: Optional[int] = Field(
        default=None,
        description="Minimum release year"
    )
    
    max_year: Optional[int] = Field(
        default=None,
        description="Maximum release year"
    )
    
    runtime_preference: Optional[str] = Field(
        default=None,
        description="Runtime preference"
    )
    
    language: Optional[str] = Field(
        default=None,
        description="Language preference"
    )
    
    popularity: Optional[str] = Field(
        default=None,
        description="Popularity preference"
    )
    
    @field_validator("include_genres", "exclude_genres")
    @classmethod
    def validate_genre_ids(cls, v: List[int]) -> List[int]:
        """Validate genre IDs."""
        if not v:
            return []
        
        for genre_id in v:
            if not isinstance(genre_id, int) or genre_id <= 0:
                raise ValueError(f"Invalid genre ID: {genre_id}")
        
        return list(set(v))
    
    def is_empty(self) -> bool:
        """Check if there are any active constraints."""
        return not any([
            self.include_genres,
            self.exclude_genres,
            self.media_type,
            self.mood,
            self.tone_modifiers,
            self.provider_id,
            self.min_year,
            self.max_year,
            self.runtime_preference,
            self.language,
            self.popularity,
        ])
    
    def has_genre_context(self) -> bool:
        """Check if there's active genre context."""
        return bool(self.include_genres)
    
    def has_provider_filter(self) -> bool:
        """Check if there's an active provider filter."""
        return self.provider_id is not None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "include_genres": [10765, 18],
                "exclude_genres": [27],
                "media_type": "tv",
                "mood": "curious",
                "tone_modifiers": ["darker"],
                "provider_id": None,
                "provider_name": None,
                "watch_region": "IN",
                "min_year": None,
                "max_year": None,
                "runtime_preference": None,
                "language": None,
                "popularity": None
            }
        }
    )


class ConversationState(BaseModel):
    """
    Complete conversation state for Scout.
    
    Separates temporary conversation context from persistent user preferences.
    Tracks conversation metadata for debugging and state transitions.
    """
    
    # Conversation identity
    conversation_id: Optional[str] = Field(
        default=None,
        description="Unique conversation identifier"
    )
    
    user_profile_id: Optional[str] = Field(
        default=None,
        description="Anonymous user profile ID (for persistent preferences)"
    )
    
    # Temporary conversation constraints
    temporary_constraints: TemporaryConstraints = Field(
        default_factory=TemporaryConstraints,
        description="Active constraints in current conversation"
    )
    
    # Recommendations shown in previous turn
    previous_recommendations: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Titles and metadata recommended in most recent turn"
    )
    
    # Conversation metadata
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When conversation started"
    )
    
    last_updated: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Last state update timestamp"
    )
    
    turn_count: int = Field(
        default=0,
        ge=0,
        description="Number of turns in conversation"
    )
    
    last_transition: Optional[StateTransition] = Field(
        default=None,
        description="Last state transition type"
    )
    
    # Context for state transitions
    last_request_type: Optional[str] = Field(
        default=None,
        description="Type of last request (for transition logic)"
    )
    
    last_media_type: Optional[MediaType] = Field(
        default=None,
        description="Media type from last request"
    )
    
    last_response_message: Optional[str] = Field(
        default=None,
        description="Last response sent to user"
    )
    
    # Debugging and analytics
    parser_history: List[str] = Field(
        default_factory=list,
        description="History of which parser was used (llm/fallback)"
    )
    
    error_count: int = Field(
        default=0,
        ge=0,
        description="Number of errors in this conversation"
    )
    
    def increment_turn(self) -> None:
        """Increment turn count and update timestamp."""
        self.turn_count += 1
        self.last_updated = datetime.now(UTC)
    
    def record_transition(self, transition: StateTransition, parser_used: Optional[str] = None) -> None:
        """Record a state transition."""
        self.last_transition = transition
        self.last_updated = datetime.now(UTC)
        
        if parser_used:
            self.parser_history.append(parser_used)
    
    def record_error(self) -> None:
        """Record an error occurrence."""
        self.error_count += 1
        self.last_updated = datetime.now(UTC)
    
    def should_reset(self) -> bool:
        """
        Determine if conversation should be reset.
        
        Reset criteria:
        - Too many errors (>3)
        - Very long conversation (>20 turns)
        """
        return self.error_count > 3 or self.turn_count > 20
    
    def get_active_constraints_summary(self) -> Dict[str, Any]:
        """Get human-readable summary of active constraints."""
        constraints = self.temporary_constraints
        
        summary = {}
        
        if constraints.media_type:
            summary["media_type"] = constraints.media_type.value
        
        if constraints.include_genres:
            summary["include_genres"] = constraints.include_genres
        
        if constraints.exclude_genres:
            summary["exclude_genres"] = constraints.exclude_genres
        
        if constraints.mood:
            summary["mood"] = constraints.mood
        
        if constraints.provider_name:
            summary["provider"] = constraints.provider_name
        
        if constraints.min_year or constraints.max_year:
            summary["year_range"] = {
                "min": constraints.min_year,
                "max": constraints.max_year
            }
        
        return summary
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "conversation_id": "conv_123",
                "user_profile_id": "user_456",
                "temporary_constraints": {
                    "include_genres": [10765],
                    "exclude_genres": [27],
                    "media_type": "tv",
                    "mood": "curious",
                    "tone_modifiers": [],
                    "provider_id": None,
                    "watch_region": "IN"
                },
                "turn_count": 3,
                "last_transition": "apply_constraint",
                "last_request_type": "constraint_only"
            }
        })
