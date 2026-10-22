"""
User preference schemas for persistent storage.

These models represent long-term user preferences that persist across sessions.
They are separate from temporary conversation state.
"""

from enum import Enum
from typing import Optional, List
from datetime import datetime, UTC
from pydantic import BaseModel, Field, field_validator, ConfigDict


class PreferenceType(str, Enum):
    """Type of user preference."""
    GENRE_LIKE = "genre_like"  # User likes this genre
    GENRE_DISLIKE = "genre_dislike"  # User dislikes this genre
    LANGUAGE = "language"  # Preferred language
    MEDIA_TYPE = "media_type"  # Preferred media type
    RUNTIME = "runtime"  # Runtime preference
    EXCLUDE = "exclude"  # Permanent exclusion (e.g., no horror ever)


class SavedGenrePreference(BaseModel):
    """
    Saved genre preference (like or dislike).
    
    This is a long-term preference that applies unless overridden
    by an explicit request in the current conversation.
    """
    
    genre_id: int = Field(
        ...,
        gt=0,
        description="TMDB genre ID"
    )
    
    genre_name: str = Field(
        ...,
        min_length=1,
        description="Human-readable genre name"
    )
    
    preference_type: PreferenceType = Field(
        ...,
        description="Like or dislike"
    )
    
    media_type: Optional[str] = Field(
        default=None,
        description="Specific to movie or tv (None = both)"
    )
    
    strength: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Preference strength (0-1, default 1.0)"
    )
    
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When preference was saved"
    )
    
    confirmed: bool = Field(
        default=False,
        description="User explicitly confirmed this preference"
    )
    
    @field_validator("preference_type")
    @classmethod
    def validate_preference_type(cls, v: PreferenceType) -> PreferenceType:
        """Validate preference type is for genres."""
        if v not in {PreferenceType.GENRE_LIKE, PreferenceType.GENRE_DISLIKE}:
            raise ValueError(f"Invalid preference type for genre: {v}")
        return v
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "genre_id": 878,
                "genre_name": "Science Fiction",
                "preference_type": "genre_like",
                "media_type": "movie",
                "strength": 1.0,
                "confirmed": True
            }
        })


class SavedExclusion(BaseModel):
    """
    Permanent exclusion preference.
    
    Example: "I never want to see horror"
    This applies to all future recommendations unless explicitly overridden.
    """
    
    exclusion_type: str = Field(
        ...,
        description="What to exclude (genre, rating, etc.)"
    )
    
    exclusion_value: str = Field(
        ...,
        description="Value to exclude (e.g., genre ID, rating threshold)"
    )
    
    reason: Optional[str] = Field(
        default=None,
        description="Why this is excluded (user's words)"
    )
    
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When exclusion was saved"
    )
    
    confirmed: bool = Field(
        default=False,
        description="User explicitly confirmed this exclusion"
    )
    
    applies_to_media: Optional[str] = Field(
        default=None,
        description="Specific to movie or tv (None = both)"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "exclusion_type": "genre",
                "exclusion_value": "27",
                "reason": "Don't like scary movies",
                "confirmed": True,
                "applies_to_media": None
            }
        })


class UserPreference(BaseModel):
    """
    Complete user preference profile.
    
    This is NOT stored in conversation state. It's loaded from persistent
    storage and merged with current request context, with explicit current
    requests taking precedence.
    """
    
    # User identity
    profile_id: str = Field(
        ...,
        min_length=1,
        description="Anonymous profile identifier"
    )
    
    # Genre preferences
    liked_genres: List[SavedGenrePreference] = Field(
        default_factory=list,
        description="Genres user likes"
    )
    
    disliked_genres: List[SavedGenrePreference] = Field(
        default_factory=list,
        description="Genres user dislikes"
    )
    
    # Permanent exclusions
    permanent_exclusions: List[SavedExclusion] = Field(
        default_factory=list,
        description="Things user never wants to see"
    )
    
    # Preferred language
    preferred_language: Optional[str] = Field(
        default=None,
        description="Preferred content language (ISO 639-1)"
    )
    
    # Preferred media type (if user consistently chooses one)
    preferred_media_type: Optional[str] = Field(
        default=None,
        description="Preferred media type (movie/tv) if user has strong preference"
    )
    
    # Preferred runtime (for movies)
    preferred_runtime: Optional[str] = Field(
        default=None,
        description="Preferred runtime range (under_90, 90_to_130, flexible)"
    )
    
    # Metadata
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When profile was created"
    )
    
    last_updated: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Last preference update"
    )
    
    interaction_count: int = Field(
        default=0,
        ge=0,
        description="Number of interactions with this profile"
    )
    
    @field_validator("profile_id")
    @classmethod
    def validate_profile_id(cls, v: str) -> str:
        """Validate profile ID format."""
        if not v or len(v) < 1:
            raise ValueError("Profile ID cannot be empty")
        
        # Basic sanitization
        if not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError("Profile ID must be alphanumeric (hyphens/underscores allowed)")
        
        return v
    
    def has_genre_preference(self, genre_id: int) -> Optional[PreferenceType]:
        """Check if user has a preference for this genre."""
        # Check likes
        for pref in self.liked_genres:
            if pref.genre_id == genre_id:
                return PreferenceType.GENRE_LIKE
        
        # Check dislikes
        for pref in self.disliked_genres:
            if pref.genre_id == genre_id:
                return PreferenceType.GENRE_DISLIKE
        
        return None
    
    def has_permanent_exclusion(self, exclusion_type: str, value: str) -> bool:
        """Check if user has a permanent exclusion."""
        for exclusion in self.permanent_exclusions:
            if exclusion.exclusion_type == exclusion_type and exclusion.exclusion_value == value:
                return True
        return False
    
    def get_preferred_genres(self, media_type: Optional[str] = None) -> List[int]:
        """Get list of preferred genre IDs for given media type."""
        return [
            pref.genre_id
            for pref in self.liked_genres
            if media_type is None or pref.media_type is None or pref.media_type == media_type
        ]
    
    def get_excluded_genres(self, media_type: Optional[str] = None) -> List[int]:
        """Get list of excluded genre IDs for given media type."""
        # From disliked genres
        disliked = [
            pref.genre_id
            for pref in self.disliked_genres
            if media_type is None or pref.media_type is None or pref.media_type == media_type
        ]
        
        # From permanent exclusions
        permanent = [
            int(exc.exclusion_value)
            for exc in self.permanent_exclusions
            if exc.exclusion_type == "genre"
            and (exc.applies_to_media is None or exc.applies_to_media == media_type)
        ]
        
        return list(set(disliked + permanent))
    
    def is_empty(self) -> bool:
        """Check if profile has any preferences."""
        return not any([
            self.liked_genres,
            self.disliked_genres,
            self.permanent_exclusions,
            self.preferred_language,
            self.preferred_media_type,
            self.preferred_runtime,
        ])
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "profile_id": "user_abc123",
                "liked_genres": [
                    {
                        "genre_id": 878,
                        "genre_name": "Science Fiction",
                        "preference_type": "genre_like",
                        "confirmed": True
                    }
                ],
                "disliked_genres": [],
                "permanent_exclusions": [
                    {
                        "exclusion_type": "genre",
                        "exclusion_value": "27",
                        "reason": "No horror movies",
                        "confirmed": True
                    }
                ],
                "preferred_language": "en",
                "preferred_media_type": None,
                "interaction_count": 15
            }
        })
