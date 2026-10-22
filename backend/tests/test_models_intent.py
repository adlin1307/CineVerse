"""
Unit tests for intent models.

Tests validation, edge cases, and model behavior.
"""

import pytest
from pydantic import ValidationError

from models.intent import (
    ParsedIntent,
    RequestType,
    MediaType,
    IntentConfidence,
)


class TestParsedIntent:
    """Test ParsedIntent model validation."""
    
    def test_valid_fresh_search_intent(self):
        """Test creating a valid fresh search intent."""
        intent = ParsedIntent(
            request_type=RequestType.FRESH_SEARCH,
            confidence=IntentConfidence.HIGH,
            media_type=MediaType.TV,
            include_genres=[10765, 18],
            exclude_genres=[27],
            mood="curious",
            response_message="Finding some great sci-fi shows for you!",
            watch_region="IN",
            raw_user_message="Suggest sci-fi TV shows",
            parser_used="llm"
        )
        
        assert intent.request_type == RequestType.FRESH_SEARCH
        assert intent.media_type == MediaType.TV
        assert 10765 in intent.include_genres
        assert 27 in intent.exclude_genres
        assert intent.mood == "curious"
        assert intent.watch_region == "IN"
    
    def test_refinement_intent(self):
        """Test refinement request intent."""
        intent = ParsedIntent(
            request_type=RequestType.REFINEMENT,
            tone_modifiers=["darker"],
            include_genres=[18],  # Adding drama
            response_message="Got it - refining your picks!",
            watch_region="IN"
        )
        
        assert intent.request_type == RequestType.REFINEMENT
        assert "darker" in intent.tone_modifiers
        assert 18 in intent.include_genres
    
    def test_constraint_only_intent(self):
        """Test constraint-only intent (e.g., 'no horror')."""
        intent = ParsedIntent(
            request_type=RequestType.CONSTRAINT_ONLY,
            exclude_genres=[27],
            response_message="No horror, got it!",
            watch_region="IN"
        )
        
        assert intent.request_type == RequestType.CONSTRAINT_ONLY
        assert 27 in intent.exclude_genres
        assert not intent.include_genres
    
    def test_clarification_request_valid(self):
        """Test clarification request with required field."""
        intent = ParsedIntent(
            request_type=RequestType.CLARIFICATION,
            response_message="Do you want movies or TV shows?",
            clarification_needed="media_type",
            watch_region="IN"
        )
        
        assert intent.request_type == RequestType.CLARIFICATION
        assert intent.clarification_needed == "media_type"
    
    def test_clarification_request_missing_field(self):
        """Test clarification request without clarification_needed fails."""
        with pytest.raises(ValidationError) as exc_info:
            ParsedIntent(
                request_type=RequestType.CLARIFICATION,
                response_message="What did you want?",
                watch_region="IN"
            )
        
        assert "Clarification requests must specify what information is needed" in str(exc_info.value)
    
    def test_invalid_genre_ids(self):
        """Test that invalid genre IDs are rejected."""
        with pytest.raises(ValidationError):
            ParsedIntent(
                request_type=RequestType.FRESH_SEARCH,
                include_genres=[0, -1, 878],  # 0 and -1 are invalid
                response_message="Test",
                watch_region="IN"
            )
    
    def test_genre_id_deduplication(self):
        """Test that duplicate genre IDs are removed."""
        intent = ParsedIntent(
            request_type=RequestType.FRESH_SEARCH,
            include_genres=[878, 878, 10765, 878],
            response_message="Test",
            watch_region="IN"
        )
        
        # Should have only unique genres
        assert len(intent.include_genres) == 2
        assert 878 in intent.include_genres
        assert 10765 in intent.include_genres
    
    def test_invalid_mood(self):
        """Test that invalid mood is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ParsedIntent(
                request_type=RequestType.FRESH_SEARCH,
                mood="super_happy",  # Not in valid moods
                response_message="Test",
                watch_region="IN"
            )
        
        assert "mood" in str(exc_info.value).lower()
    
    def test_valid_moods(self):
        """Test all valid moods."""
        valid_moods = ["relaxed", "excited", "emotional", "curious"]
        
        for mood in valid_moods:
            intent = ParsedIntent(
                request_type=RequestType.FRESH_SEARCH,
                mood=mood,
                response_message="Test",
                watch_region="IN"
            )
            assert intent.mood == mood
    
    def test_mood_case_normalization(self):
        """Test mood is normalized to lowercase."""
        intent = ParsedIntent(
            request_type=RequestType.FRESH_SEARCH,
            mood="EXCITED",
            response_message="Test",
            watch_region="IN"
        )
        
        assert intent.mood == "excited"
    
    def test_invalid_runtime_preference(self):
        """Test invalid runtime preference is rejected."""
        with pytest.raises(ValidationError):
            ParsedIntent(
                request_type=RequestType.FRESH_SEARCH,
                runtime_preference="super_short",
                response_message="Test",
                watch_region="IN"
            )
    
    def test_valid_runtime_preferences(self):
        """Test all valid runtime preferences."""
        valid_runtimes = ["under_90", "90_to_130", "flexible"]
        
        for runtime in valid_runtimes:
            intent = ParsedIntent(
                request_type=RequestType.FRESH_SEARCH,
                runtime_preference=runtime,
                response_message="Test",
                watch_region="IN"
            )
            assert intent.runtime_preference == runtime
    
    def test_invalid_popularity(self):
        """Test invalid popularity is rejected."""
        with pytest.raises(ValidationError):
            ParsedIntent(
                request_type=RequestType.FRESH_SEARCH,
                popularity="super_popular",
                response_message="Test",
                watch_region="IN"
            )
    
    def test_invalid_watch_region(self):
        """Test invalid watch region format."""
        with pytest.raises(ValidationError):
            ParsedIntent(
                request_type=RequestType.FRESH_SEARCH,
                response_message="Test",
                watch_region="USA"  # Must be 2-letter code
            )
    
    def test_watch_region_normalization(self):
        """Test watch region is normalized to uppercase."""
        intent = ParsedIntent(
            request_type=RequestType.FRESH_SEARCH,
            response_message="Test",
            watch_region="us"
        )
        
        assert intent.watch_region == "US"
    
    def test_invalid_year_range(self):
        """Test that invalid year range is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ParsedIntent(
                request_type=RequestType.FRESH_SEARCH,
                min_year=2020,
                max_year=2010,  # max < min
                response_message="Test",
                watch_region="IN"
            )
        
        assert "min_year" in str(exc_info.value) or "max_year" in str(exc_info.value)
    
    def test_valid_year_range(self):
        """Test valid year range."""
        intent = ParsedIntent(
            request_type=RequestType.FRESH_SEARCH,
            min_year=2010,
            max_year=2020,
            response_message="Test",
            watch_region="IN"
        )
        
        assert intent.min_year == 2010
        assert intent.max_year == 2020
    
    def test_year_boundary_validation(self):
        """Test year boundary validation."""
        # Too old
        with pytest.raises(ValidationError):
            ParsedIntent(
                request_type=RequestType.FRESH_SEARCH,
                min_year=1800,
                response_message="Test",
                watch_region="IN"
            )
        
        # Too far future
        with pytest.raises(ValidationError):
            ParsedIntent(
                request_type=RequestType.FRESH_SEARCH,
                max_year=2150,
                response_message="Test",
                watch_region="IN"
            )
    
    def test_has_genre_constraints(self):
        """Test has_genre_constraints() method."""
        intent_with = ParsedIntent(
            request_type=RequestType.FRESH_SEARCH,
            include_genres=[878],
            response_message="Test",
            watch_region="IN"
        )
        
        intent_without = ParsedIntent(
            request_type=RequestType.FRESH_SEARCH,
            response_message="Test",
            watch_region="IN"
        )
        
        assert intent_with.has_genre_constraints()
        assert not intent_without.has_genre_constraints()
    
    def test_has_provider_filter(self):
        """Test has_provider_filter() method."""
        intent_with = ParsedIntent(
            request_type=RequestType.FRESH_SEARCH,
            provider_id=2336,
            provider_name="Disney+ Hotstar",
            response_message="Test",
            watch_region="IN"
        )
        
        intent_without = ParsedIntent(
            request_type=RequestType.FRESH_SEARCH,
            response_message="Test",
            watch_region="IN"
        )
        
        assert intent_with.has_provider_filter()
        assert not intent_without.has_provider_filter()
    
    def test_is_recommendation_request(self):
        """Test is_recommendation_request() method."""
        # Should trigger recommendations
        fresh = ParsedIntent(
            request_type=RequestType.FRESH_SEARCH,
            response_message="Test",
            watch_region="IN"
        )
        assert fresh.is_recommendation_request()
        
        refinement = ParsedIntent(
            request_type=RequestType.REFINEMENT,
            response_message="Test",
            watch_region="IN"
        )
        assert refinement.is_recommendation_request()
        
        # Should NOT trigger recommendations
        chat = ParsedIntent(
            request_type=RequestType.CHAT,
            response_message="Hello!",
            watch_region="IN"
        )
        assert not chat.is_recommendation_request()
        
        clarify = ParsedIntent(
            request_type=RequestType.CLARIFICATION,
            clarification_needed="media_type",
            response_message="What type?",
            watch_region="IN"
        )
        assert not clarify.is_recommendation_request()
    
    def test_provider_without_region(self):
        """Test provider ID with default region."""
        intent = ParsedIntent(
            request_type=RequestType.FRESH_SEARCH,
            provider_id=2336,
            provider_name="Disney+ Hotstar",
            response_message="Test",
            watch_region="IN"
        )
        
        assert intent.provider_id == 2336
        assert intent.watch_region == "IN"
    
    def test_empty_response_message_rejected(self):
        """Test that empty response message is rejected."""
        with pytest.raises(ValidationError):
            ParsedIntent(
                request_type=RequestType.FRESH_SEARCH,
                response_message="",  # Empty
                watch_region="IN"
            )
    
    def test_minimal_valid_intent(self):
        """Test minimal valid intent with only required fields."""
        intent = ParsedIntent(
            request_type=RequestType.CHAT,
            response_message="Hello!",
            watch_region="IN"
        )
        
        assert intent.request_type == RequestType.CHAT
        assert intent.response_message == "Hello!"
        assert intent.confidence == IntentConfidence.MEDIUM  # default
        assert not intent.include_genres
        assert not intent.exclude_genres
    
    def test_full_intent_with_all_fields(self):
        """Test intent with all optional fields populated."""
        intent = ParsedIntent(
            request_type=RequestType.FRESH_SEARCH,
            confidence=IntentConfidence.HIGH,
            media_type=MediaType.MOVIE,
            include_genres=[878, 18],
            exclude_genres=[27, 35],
            mood="emotional",
            tone_modifiers=["darker", "intense"],
            provider_id=8,
            provider_name="Netflix",
            watch_region="US",
            min_year=2010,
            max_year=2023,
            runtime_preference="90_to_130",
            language="en",
            popularity="high",
            response_message="Finding emotional sci-fi movies on Netflix!",
            clarification_needed=None,
            raw_user_message="Emotional sci-fi movies on Netflix",
            parser_used="llm"
        )
        
        assert intent.request_type == RequestType.FRESH_SEARCH
        assert intent.media_type == MediaType.MOVIE
        assert len(intent.include_genres) == 2
        assert len(intent.exclude_genres) == 2
        assert len(intent.tone_modifiers) == 2
        assert intent.provider_id == 8
        assert intent.min_year == 2010
        assert intent.max_year == 2023
