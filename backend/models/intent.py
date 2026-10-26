"""
Intent schemas for natural language request parsing.

These models represent the structured output from intent parsing,
whether from LLM (Gemini) or fallback rule-based parser.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict, model_validator


class RequestType(str, Enum):
    """Type of user request."""
    FRESH_SEARCH = "fresh_search"  # New search, clear unrelated constraints
    NEW_SEARCH = "new_search"  # Alias for fresh search
    REFINEMENT = "refinement"  # Modify existing search (e.g., "make them darker")
    CONSTRAINT_ONLY = "constraint_only"  # Add constraint to current (e.g., "no horror")
    CONSTRAINT_UPDATE = "constraint_update"  # Alias for constraint update
    CORRECTION = "correction"  # Fix/override previous value (e.g., "actually, I want movies")
    TITLE_QUESTION = "title_question"  # Ask about a title or recommendation already shown
    CLARIFICATION = "clarification"  # Need more info from user
    CHAT = "chat"  # Conversational, no recommendation needed


class MediaType(str, Enum):
    """Media type for recommendations."""
    MOVIE = "movie"
    TV = "tv"
    BOTH = "both"  # Explicitly requested mixed media


class IntentConfidence(str, Enum):
    """Confidence level in parsed intent."""
    HIGH = "high"  # Clear, unambiguous request
    MEDIUM = "medium"  # Reasonable interpretation
    LOW = "low"  # Uncertain, may need clarification


class ParsedIntent(BaseModel):
    """
    Structured intent parsed from natural language.
    
    This is the output of intent parsing and input to state management.
    All fields are validated and normalized.
    """
    
    # Request classification
    request_type: RequestType = Field(
        ...,
        description="Type of request (fresh search, refinement, etc.)"
    )
    
    confidence: IntentConfidence = Field(
        default=IntentConfidence.MEDIUM,
        description="Parser's confidence in this interpretation"
    )
    
    # Media preferences
    media_type: Optional[MediaType] = Field(
        default=None,
        description="Requested media type (movie, tv, or both)"
    )
    
    # Genre constraints
    include_genres: List[int] = Field(
        default_factory=list,
        description="Genre IDs to include (TMDB genre IDs)"
    )
    
    exclude_genres: List[int] = Field(
        default_factory=list,
        description="Genre IDs to exclude (TMDB genre IDs)"
    )
    
    # Mood and tone
    mood: Optional[str] = Field(
        default=None,
        description="Viewing mood (relaxed, excited, emotional, curious)"
    )
    
    emotional_sub_intent: Optional[str] = Field(
        default=None,
        description="Nuanced emotional intent (tearjerker, feelgood, bittersweet, hopeful, dark, thought_provoking, general)"
    )
    
    tone_modifiers: List[str] = Field(
        default_factory=list,
        description="Tone requests like 'darker', 'lighter', 'more intense'"
    )
    
    # Referenced title for title questions
    referenced_title_index: Optional[int] = Field(
        default=None,
        description="1-based index of referenced title in previous recommendation set"
    )
    
    referenced_title_name: Optional[str] = Field(
        default=None,
        description="Name of title referenced by user"
    )
    
    # Streaming provider
    provider_id: Optional[int] = Field(
        default=None,
        description="TMDB provider ID (region-specific)"
    )
    
    provider_name: Optional[str] = Field(
        default=None,
        description="Provider name for display (e.g., 'Netflix', 'Disney+ Hotstar')"
    )
    
    watch_region: str = Field(
        default="IN",
        description="Watch region (ISO 3166-1 alpha-2, e.g., 'IN', 'US')"
    )
    
    # Additional filters
    min_year: Optional[int] = Field(
        default=None,
        ge=1900,
        le=2100,
        description="Minimum release year"
    )
    
    max_year: Optional[int] = Field(
        default=None,
        ge=1900,
        le=2100,
        description="Maximum release year"
    )
    
    runtime_preference: Optional[str] = Field(
        default=None,
        description="Runtime preference (under_90, 90_to_130, flexible)"
    )
    
    language: Optional[str] = Field(
        default=None,
        description="Preferred language (ISO 639-1 code, e.g., 'en', 'hi')"
    )
    
    popularity: Optional[str] = Field(
        default=None,
        description="Popularity preference (low, medium, high)"
    )
    
    count: Optional[int] = Field(
        default=None,
        ge=1,
        le=20,
        description="Number of recommendations requested by user"
    )
    
    # Response generation
    response_message: str = Field(
        ...,
        min_length=1,
        description="Natural language response to user"
    )
    
    clarification_needed: Optional[str] = Field(
        default=None,
        description="What info is needed for clarification requests"
    )
    
    # Metadata
    raw_user_message: Optional[str] = Field(
        default=None,
        description="Original user message for debugging"
    )
    
    parser_used: Optional[str] = Field(
        default=None,
        description="Which parser was used (llm, fallback)"
    )
    
    @field_validator("include_genres", "exclude_genres")
    @classmethod
    def validate_genre_ids(cls, v: List[int]) -> List[int]:
        """Validate genre IDs are positive integers."""
        if not v:
            return []
        
        for genre_id in v:
            if not isinstance(genre_id, int) or genre_id <= 0:
                raise ValueError(f"Invalid genre ID: {genre_id}. Must be positive integer.")
        
        return list(set(v))  # Remove duplicates
    
    @field_validator("mood")
    @classmethod
    def validate_mood(cls, v: Optional[str]) -> Optional[str]:
        """Validate mood is in allowed list."""
        if v is None:
            return None
        
        valid_moods = {"relaxed", "excited", "emotional", "curious"}
        if v.lower() not in valid_moods:
            raise ValueError(f"Invalid mood: {v}. Must be one of {valid_moods}")
        
        return v.lower()
    
    @field_validator("runtime_preference")
    @classmethod
    def validate_runtime(cls, v: Optional[str]) -> Optional[str]:
        """Validate runtime preference."""
        if v is None:
            return None
        
        valid_runtimes = {"under_90", "90_to_130", "flexible"}
        if v not in valid_runtimes:
            raise ValueError(f"Invalid runtime: {v}. Must be one of {valid_runtimes}")
        
        return v
    
    @field_validator("popularity")
    @classmethod
    def validate_popularity(cls, v: Optional[str]) -> Optional[str]:
        """Validate popularity preference."""
        if v is None:
            return None
        
        valid_popularity = {"low", "medium", "high"}
        if v not in valid_popularity:
            raise ValueError(f"Invalid popularity: {v}. Must be one of {valid_popularity}")
        
        return v
    
    @field_validator("watch_region")
    @classmethod
    def validate_region(cls, v: str) -> str:
        """Validate watch region is 2-letter code."""
        if not v or len(v) != 2:
            raise ValueError(f"Invalid region code: {v}. Must be 2-letter ISO 3166-1 alpha-2 code.")
        
        return v.upper()
    
    @model_validator(mode="after")
    def validate_year_range(self) -> "ParsedIntent":
        """Validate year range is logical."""
        if self.min_year and self.max_year:
            if self.min_year > self.max_year:
                raise ValueError(f"min_year ({self.min_year}) cannot be greater than max_year ({self.max_year})")
        
        return self
    
    @model_validator(mode="after")
    def validate_clarification_request(self) -> "ParsedIntent":
        """Validate clarification requests have clarification_needed."""
        if self.request_type == RequestType.CLARIFICATION and not self.clarification_needed:
            raise ValueError("Clarification requests must specify what information is needed")
        
        return self
    
    def has_genre_constraints(self) -> bool:
        """Check if intent has any genre constraints."""
        return bool(self.include_genres or self.exclude_genres)
    
    def has_provider_filter(self) -> bool:
        """Check if intent specifies a streaming provider."""
        return self.provider_id is not None
    
    def is_recommendation_request(self) -> bool:
        """Check if this intent should generate recommendations."""
        return self.request_type in {
            RequestType.FRESH_SEARCH,
            RequestType.NEW_SEARCH,
            RequestType.REFINEMENT,
            RequestType.CONSTRAINT_ONLY,
            RequestType.CONSTRAINT_UPDATE,
            RequestType.CORRECTION,
        }
    
    model_config = ConfigDict(
        use_enum_values=False,
        json_schema_extra={
            "example": {
                "request_type": "fresh_search",
                "confidence": "high",
                "media_type": "tv",
                "include_genres": [10765, 18],
                "exclude_genres": [27],
                "mood": "curious",
                "tone_modifiers": [],
                "provider_id": None,
                "provider_name": None,
                "watch_region": "IN",
                "response_message": "Finding some great sci-fi shows for you!",
                "clarification_needed": None,
                "raw_user_message": "Suggest some sci-fi TV shows",
                "parser_used": "llm"
            }
        }
    )
