"""
Models package for CineVerse Scout architecture.

This package contains Pydantic schemas for:
- Parsed intents from natural language
- Conversation state management
- Recommendation requests and responses
- Structured evidence for explanations
- User preferences (persistent)
"""

from models.intent import (
    RequestType,
    ParsedIntent,
    MediaType,
    IntentConfidence,
)

from models.state import (
    ConversationState,
    TemporaryConstraints,
    StateTransition,
)

from models.recommendation import (
    RecommendationRequest,
    RecommendationCandidate,
    RecommendationEvidence,
    RecommendationResult,
    GenreMatch,
)

from models.user_preferences import (
    UserPreference,
    PreferenceType,
    SavedGenrePreference,
    SavedExclusion,
)

__all__ = [
    # Intent
    "RequestType",
    "ParsedIntent",
    "MediaType",
    "IntentConfidence",
    # State
    "ConversationState",
    "TemporaryConstraints",
    "StateTransition",
    # Recommendation
    "RecommendationRequest",
    "RecommendationCandidate",
    "RecommendationEvidence",
    "RecommendationResult",
    "GenreMatch",
    # User Preferences
    "UserPreference",
    "PreferenceType",
    "SavedGenrePreference",
    "SavedExclusion",
]
