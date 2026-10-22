"""
Recommendation request and response schemas.

These models represent the deterministic recommendation pipeline:
- Validated requests to the recommendation engine
- Candidates with normalized metadata
- Structured evidence for explanations
- Final validated results
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict

from models.intent import MediaType


class RecommendationRequest(BaseModel):
    """
    Validated request to recommendation engine.
    
    This is the input to the deterministic recommendation pipeline.
    All validation has been completed; the engine applies constraints mechanically.
    """
    
    # Media type (required)
    media_type: MediaType = Field(
        ...,
        description="Media type to search (movie, tv, or both)"
    )
    
    # Genre constraints (hard filters)
    include_genres: List[int] = Field(
        default_factory=list,
        description="Genre IDs that must be present (at least one)"
    )
    
    exclude_genres: List[int] = Field(
        default_factory=list,
        description="Genre IDs that must not be present (hard exclusion)"
    )
    
    # Provider filter (hard filter)
    provider_id: Optional[int] = Field(
        default=None,
        description="TMDB provider ID (region-specific)"
    )
    
    watch_region: str = Field(
        default="IN",
        description="Watch region for provider filtering"
    )
    
    # Year constraints (hard filters)
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
    
    # Runtime preference (soft ranking signal for movies)
    runtime_preference: Optional[str] = Field(
        default=None,
        description="Runtime preference (under_90, 90_to_130, flexible)"
    )
    
    # Mood for situation-aware ranking (soft signal)
    mood: Optional[str] = Field(
        default=None,
        description="Viewing mood for ranking (relaxed, excited, emotional, curious)"
    )
    
    emotional_sub_intent: Optional[str] = Field(
        default=None,
        description="Emotional sub-intent (tearjerker, feelgood, bittersweet, dark, etc.)"
    )
    
    # Additional soft signals
    language: Optional[str] = Field(
        default=None,
        description="Preferred language (ISO 639-1)"
    )
    
    popularity: Optional[str] = Field(
        default=None,
        description="Popularity preference (low, medium, high)"
    )
    
    # Result count
    count: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of recommendations to return"
    )
    
    # Context for evidence building
    tone_modifiers: List[str] = Field(
        default_factory=list,
        description="Tone modifiers for explanation context (darker, lighter, etc.)"
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
    
    @field_validator("watch_region")
    @classmethod
    def validate_region(cls, v: str) -> str:
        """Validate region code."""
        if not v or len(v) != 2:
            raise ValueError(f"Invalid region: {v}")
        return v.upper()
    
    @model_validator(mode="after")
    def validate_constraints(self) -> "RecommendationRequest":
        """Validate constraint logic."""
        # Can't have overlapping include/exclude
        if self.include_genres and self.exclude_genres:
            overlap = set(self.include_genres) & set(self.exclude_genres)
            if overlap:
                raise ValueError(f"Genres cannot be both included and excluded: {overlap}")
        
        # Year range validation
        if self.min_year and self.max_year:
            if self.min_year > self.max_year:
                raise ValueError(f"min_year ({self.min_year}) > max_year ({self.max_year})")
        
        return self
    
    def has_hard_filters(self) -> bool:
        """Check if request has any hard filtering constraints."""
        return bool(
            self.include_genres
            or self.exclude_genres
            or self.provider_id
            or self.min_year
            or self.max_year
        )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "media_type": "tv",
                "include_genres": [10765, 18],
                "exclude_genres": [27],
                "provider_id": None,
                "watch_region": "IN",
                "mood": "curious",
                "count": 5,
                "tone_modifiers": ["darker"]
            }
        })


class GenreMatch(BaseModel):
    """Genre match evidence."""
    genre_id: int = Field(..., description="Genre ID from TMDB")
    genre_name: str = Field(..., description="Human-readable genre name")
    was_requested: bool = Field(
        ...,
        description="True if this genre was explicitly requested"
    )


class RecommendationEvidence(BaseModel):
    """
    Structured evidence for a recommendation.
    
    This contains only verified metadata that can be used to generate
    explanations. Never invented, always from TMDB or verified sources.
    """
    
    # Verified metadata
    title: str = Field(..., description="Title from TMDB")
    media_type: MediaType = Field(..., description="Movie or TV")
    tmdb_id: int = Field(..., description="TMDB ID")
    
    # Genre matching evidence
    matched_genres: List[GenreMatch] = Field(
        default_factory=list,
        description="Genres that match the request"
    )
    
    all_genres: List[GenreMatch] = Field(
        default_factory=list,
        description="All genres for this title"
    )
    
    # Quality signals
    vote_average: Optional[float] = Field(
        default=None,
        ge=0,
        le=10,
        description="TMDB rating (0-10)"
    )
    
    vote_count: Optional[int] = Field(
        default=None,
        ge=0,
        description="Number of votes"
    )
    
    popularity: Optional[float] = Field(
        default=None,
        ge=0,
        description="TMDB popularity score"
    )
    
    # Release information
    release_year: Optional[int] = Field(
        default=None,
        ge=1900,
        description="Release year"
    )
    
    release_date: Optional[str] = Field(
        default=None,
        description="Full release date (YYYY-MM-DD)"
    )
    
    # Runtime (movies only)
    runtime: Optional[int] = Field(
        default=None,
        ge=0,
        description="Runtime in minutes (movies only)"
    )
    
    # Language
    original_language: Optional[str] = Field(
        default=None,
        description="Original language code"
    )
    
    # Overview (short excerpt only)
    overview_excerpt: Optional[str] = Field(
        default=None,
        max_length=150,
        description="First 150 chars of overview"
    )
    
    # Provider availability (if verified)
    available_on_requested_provider: Optional[bool] = Field(
        default=None,
        description="True if verified available on requested provider"
    )
    
    provider_verification_attempted: bool = Field(
        default=False,
        description="Whether provider availability was checked"
    )
    
    # Poster
    poster_path: Optional[str] = Field(
        default=None,
        description="TMDB poster path"
    )
    
    def has_rating_evidence(self) -> bool:
        """Check if we have rating data."""
        return self.vote_average is not None and self.vote_count is not None
    
    def has_genre_match(self) -> bool:
        """Check if any genres were matched."""
        return bool(self.matched_genres)
    
    def get_rating_description(self) -> Optional[str]:
        """Get human-readable rating description."""
        if not self.has_rating_evidence():
            return None
        
        if self.vote_average >= 8.0:
            return f"{self.vote_average:.1f}/10 rating"
        elif self.vote_average >= 7.0:
            return f"rated {self.vote_average:.1f}/10"
        else:
            return None  # Don't highlight low ratings
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "The Expanse",
                "media_type": "tv",
                "tmdb_id": 63639,
                "matched_genres": [
                    {"genre_id": 10765, "genre_name": "Sci-Fi & Fantasy", "was_requested": True},
                    {"genre_id": 18, "genre_name": "Drama", "was_requested": True}
                ],
                "vote_average": 8.2,
                "vote_count": 1250,
                "release_year": 2015,
                "release_date": "2015-12-14",
                "overview_excerpt": "A thriller set two hundred years in the future...",
                "poster_path": "/path.jpg"
            }
        })


class RecommendationCandidate(BaseModel):
    """
    Candidate recommendation with evidence and scoring.
    
    Internal representation during ranking. Final results contain
    only evidence and generated explanation.
    """
    
    # Evidence (verified metadata)
    evidence: RecommendationEvidence = Field(
        ...,
        description="Structured evidence for this recommendation"
    )
    
    # Ranking scores (internal, not exposed to frontend)
    relevance_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="How well it matches request (0-1)"
    )
    
    quality_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Quality based on ratings (0-1)"
    )
    
    popularity_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Normalized popularity (0-1)"
    )
    
    final_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Combined final score (0-1)"
    )
    
    # Ranking metadata
    rank: Optional[int] = Field(
        default=None,
        ge=1,
        description="Rank in final results (1 = best)"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "evidence": {
                    "title": "The Expanse",
                    "media_type": "tv",
                    "tmdb_id": 63639,
                    "matched_genres": [],
                    "vote_average": 8.2,
                    "release_year": 2015
                },
                "relevance_score": 0.95,
                "quality_score": 0.85,
                "popularity_score": 0.70,
                "final_score": 0.87,
                "rank": 1
            }
        })


class RecommendationResult(BaseModel):
    """
    Final validated recommendation result.
    
    This is what gets returned to the frontend. It contains only
    evidence and a generated explanation based on that evidence.
    """
    
    # TMDB identification
    id: int = Field(..., description="TMDB ID")
    title: str = Field(..., description="Title")
    media_type: str = Field(..., description="'movie' or 'tv'")
    
    # Display metadata
    poster_path: Optional[str] = Field(
        default=None,
        description="Poster path for display"
    )
    
    vote_average: Optional[float] = Field(
        default=None,
        description="Rating for display"
    )
    
    release_date: Optional[str] = Field(
        default=None,
        description="Release date for display"
    )
    
    # Genre information
    genre_ids: List[int] = Field(
        default_factory=list,
        description="Genre IDs for this title"
    )
    
    # Evidence-based explanation
    explanation: str = Field(
        ...,
        min_length=1,
        description="Natural language explanation based on evidence"
    )
    
    # Optional: structured evidence for debugging
    evidence: Optional[RecommendationEvidence] = Field(
        default=None,
        description="Full structured evidence (optional, for debugging)"
    )
    
    @classmethod
    def from_candidate(
        cls,
        candidate: RecommendationCandidate,
        explanation: str,
        include_evidence: bool = False
    ) -> "RecommendationResult":
        """Create result from candidate with generated explanation."""
        evidence = candidate.evidence
        
        return cls(
            id=evidence.tmdb_id,
            title=evidence.title,
            media_type=evidence.media_type.value,
            poster_path=evidence.poster_path,
            vote_average=evidence.vote_average,
            release_date=evidence.release_date,
            genre_ids=[g.genre_id for g in evidence.all_genres],
            explanation=explanation,
            evidence=evidence if include_evidence else None
        )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 63639,
                "title": "The Expanse",
                "media_type": "tv",
                "poster_path": "/path.jpg",
                "vote_average": 8.2,
                "release_date": "2015-12-14",
                "genre_ids": [10765, 18],
                "explanation": "Sci-fi & fantasy — 8.2/10 rating — (2015)"
            }
        })
