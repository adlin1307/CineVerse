"""
Tests for Intent Parser Service (Phase 2)

Validates both LLM and deterministic fallback parsing modes.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, UTC

from services.intent_parser import IntentParser, GENRE_MAP
from models.intent import ParsedIntent, RequestType, MediaType, IntentConfidence
from models.state import ConversationState, TemporaryConstraints


@pytest.fixture
def parser():
    """Create IntentParser instance."""
    return IntentParser()


@pytest.fixture
def empty_state():
    """Empty conversation state."""
    return ConversationState(
        conversation_id="test-session",
        user_profile_id="user-123",
        temporary_constraints=TemporaryConstraints()
    )


@pytest.fixture
def state_with_scifi():
    """Conversation state with sci-fi movies context."""
    return ConversationState(
        conversation_id="test-session",
        user_profile_id="user-123",
        temporary_constraints=TemporaryConstraints(
            media_type=MediaType.MOVIE,
            include_genres=[878],  # Sci-fi movies
            watch_region="IN"
        )
    )


class TestDeterministicFallback:
    """Test deterministic parser (no LLM)."""
    
    @pytest.mark.asyncio
    async def test_fresh_search_scifi_tv(self, parser, empty_state):
        """Test: 'Suggest some sci-fi TV shows'"""
        result = await parser.parse_intent(
            "Suggest some sci-fi TV shows",
            empty_state
        )
        
        assert result.request_type == RequestType.FRESH_SEARCH
        assert result.media_type == MediaType.TV
        assert 10765 in result.include_genres  # TV sci-fi
        assert result.exclude_genres == []
        assert result.parser_used == "fallback"
        assert "TV" in result.response_message or "series" in result.response_message
    
    @pytest.mark.asyncio
    async def test_fresh_search_action_movies(self, parser, empty_state):
        """Test: 'Find action movies'"""
        result = await parser.parse_intent(
            "Find action movies",
            empty_state
        )
        
        assert result.request_type == RequestType.FRESH_SEARCH
        assert result.media_type == MediaType.MOVIE
        assert 28 in result.include_genres  # Action movies
        assert result.parser_used == "fallback"
    
    @pytest.mark.asyncio
    async def test_refinement_darker(self, parser, state_with_scifi):
        """Test: 'Make them darker' (requires context)"""
        result = await parser.parse_intent(
            "Make them darker",
            state_with_scifi
        )
        
        assert result.request_type == RequestType.REFINEMENT
        assert "darker" in result.tone_modifiers
        assert 18 in result.include_genres  # Drama
        assert result.mood == "emotional"
        assert result.parser_used == "fallback"
    
    @pytest.mark.asyncio
    async def test_refinement_without_context_becomes_fresh(self, parser, empty_state):
        """Test: 'Make them darker' without context -> fresh search"""
        result = await parser.parse_intent(
            "Make them darker",
            empty_state
        )
        
        # Without context, "more/less" patterns should not trigger refinement
        # Should be fresh search
        assert result.request_type == RequestType.FRESH_SEARCH
        assert "darker" in result.tone_modifiers
    
    @pytest.mark.asyncio
    async def test_constraint_no_horror(self, parser, state_with_scifi):
        """Test: 'no horror please' (exclusion)"""
        result = await parser.parse_intent(
            "no horror please",
            state_with_scifi
        )
        
        assert result.request_type == RequestType.CONSTRAINT_ONLY
        assert 27 in result.exclude_genres  # Horror
        assert result.include_genres == []
        assert result.parser_used == "fallback"
    
    @pytest.mark.asyncio
    async def test_constraint_without_thriller(self, parser, state_with_scifi):
        """Test: 'without thriller' (exclusion)"""
        result = await parser.parse_intent(
            "without thriller",
            state_with_scifi
        )
        
        assert result.request_type == RequestType.CONSTRAINT_ONLY
        assert 53 in result.exclude_genres  # Thriller
    
    @pytest.mark.asyncio
    async def test_correction_actually_tv(self, parser, state_with_scifi):
        """Test: 'actually I want TV shows' (correction)"""
        result = await parser.parse_intent(
            "actually I want TV shows",
            state_with_scifi
        )
        
        assert result.request_type == RequestType.CORRECTION
        assert result.media_type == MediaType.TV
        assert result.parser_used == "fallback"
    
    @pytest.mark.asyncio
    async def test_chat_greeting(self, parser, empty_state):
        """Test: 'hi' (chat)"""
        result = await parser.parse_intent("hi", empty_state)
        
        assert result.request_type == RequestType.CHAT
        assert result.confidence == IntentConfidence.HIGH
        assert "Hey" in result.response_message or "Hello" in result.response_message
        assert result.parser_used == "fallback"
    
    @pytest.mark.asyncio
    async def test_chat_thanks(self, parser, empty_state):
        """Test: 'thanks' (chat)"""
        result = await parser.parse_intent("thanks", empty_state)
        
        assert result.request_type == RequestType.CHAT
        assert result.parser_used == "fallback"
    
    @pytest.mark.asyncio
    async def test_now_suggest_disney_is_fresh_search(self, parser, state_with_scifi):
        """Test: 'Now suggest Disney TV shows' -> FRESH_SEARCH (not negative)"""
        result = await parser.parse_intent(
            "Now suggest some Disney TV shows",
            state_with_scifi
        )
        
        # Key regression test: "now" should NOT trigger exclusion
        assert result.request_type == RequestType.FRESH_SEARCH
        assert result.media_type == MediaType.TV
        # "Disney" detection is complex, but at minimum should not exclude anything incorrectly
        assert 27 not in result.exclude_genres  # Should NOT have horror exclusion
        assert result.parser_used == "fallback"
    
    @pytest.mark.asyncio
    async def test_mood_extraction(self, parser, empty_state):
        """Test mood extraction: 'funny comedy movies'"""
        result = await parser.parse_intent(
            "funny comedy movies",
            empty_state
        )
        
        assert result.mood == "relaxed"  # "funny" maps to relaxed
        assert 35 in result.include_genres  # Comedy
    
    @pytest.mark.asyncio
    async def test_runtime_extraction(self, parser, empty_state):
        """Test runtime: 'short action movies'"""
        result = await parser.parse_intent(
            "short action movies",
            empty_state
        )
        
        assert result.runtime_preference == "under_90"
        assert 28 in result.include_genres  # Action
    
    @pytest.mark.asyncio
    async def test_empty_message_raises(self, parser, empty_state):
        """Test empty message raises ValueError"""
        with pytest.raises(ValueError, match="Empty message"):
            await parser.parse_intent("", empty_state)
    
    @pytest.mark.asyncio
    async def test_whitespace_message_raises(self, parser, empty_state):
        """Test whitespace-only message raises ValueError"""
        with pytest.raises(ValueError, match="Empty message"):
            await parser.parse_intent("   \n  ", empty_state)
    
    @pytest.mark.asyncio
    async def test_multi_word_genre_exclusion_science_fiction(self, parser, empty_state):
        """Test: 'No science fiction, please'"""
        result = await parser.parse_intent(
            "No science fiction, please",
            empty_state
        )
        
        assert result.request_type == RequestType.CONSTRAINT_ONLY
        assert 878 in result.exclude_genres  # Movie sci-fi
        assert 10765 in result.exclude_genres  # TV sci-fi & fantasy
        assert result.include_genres == []
        assert result.parser_used == "fallback"
    
    @pytest.mark.asyncio
    async def test_multi_word_genre_exclusion_action_adventure(self, parser, empty_state):
        """Test: 'Without action and adventure'"""
        result = await parser.parse_intent(
            "Without action and adventure",
            empty_state
        )
        
        assert result.request_type == RequestType.CONSTRAINT_ONLY
        assert 28 in result.exclude_genres  # Movie action
        assert 10759 in result.exclude_genres  # TV action & adventure
        assert result.include_genres == []
    
    @pytest.mark.asyncio
    async def test_multi_word_genre_exclusion_romantic_comedy(self, parser, empty_state):
        """Test: 'No romantic comedy'"""
        result = await parser.parse_intent(
            "No romantic comedy",
            empty_state
        )
        
        assert result.request_type == RequestType.CONSTRAINT_ONLY
        # Romantic comedy uses romance for movies, comedy for TV
        assert 10749 in result.exclude_genres or 35 in result.exclude_genres
        assert result.include_genres == []
    
    @pytest.mark.asyncio
    async def test_multi_word_exclusion_with_inclusion_same_message(self, parser, empty_state):
        """Test: 'Suggest action movies, but no science fiction'"""
        result = await parser.parse_intent(
            "Suggest action movies, but no science fiction",
            empty_state
        )
        
        assert result.request_type == RequestType.FRESH_SEARCH
        assert 28 in result.include_genres  # Action movies
        assert 878 in result.exclude_genres  # Sci-fi movies excluded
        # When media_type=MOVIE, only movie genres should be excluded
        assert result.media_type == MediaType.MOVIE
    
    @pytest.mark.asyncio
    async def test_fantasy_genre_movies_explicit(self, parser, empty_state):
        """Test: 'fantasy movies' should use movie fantasy ID only"""
        result = await parser.parse_intent(
            "Suggest fantasy movies",
            empty_state
        )
        
        assert result.request_type == RequestType.FRESH_SEARCH
        assert result.media_type == MediaType.MOVIE
        assert 14 in result.include_genres  # Movie fantasy
        assert 10765 not in result.include_genres  # TV sci-fi & fantasy should NOT be included
    
    @pytest.mark.asyncio
    async def test_fantasy_genre_tv_explicit(self, parser, empty_state):
        """Test: 'fantasy TV shows' should use TV sci-fi & fantasy ID"""
        result = await parser.parse_intent(
            "Suggest fantasy TV shows",
            empty_state
        )
        
        assert result.request_type == RequestType.FRESH_SEARCH
        assert result.media_type == MediaType.TV
        assert 10765 in result.include_genres  # TV sci-fi & fantasy
        assert 14 not in result.include_genres  # Movie fantasy should NOT be included
    
    @pytest.mark.asyncio
    async def test_fantasy_genre_no_media_type(self, parser, empty_state):
        """Test: 'fantasy' with no media type should include both IDs"""
        result = await parser.parse_intent(
            "Suggest some fantasy",
            empty_state
        )
        
        assert result.request_type == RequestType.FRESH_SEARCH
        assert result.media_type is None  # No explicit media type
        # Should include both since media type is unspecified
        assert 14 in result.include_genres  # Movie fantasy
        assert 10765 in result.include_genres  # TV sci-fi & fantasy
    
    @pytest.mark.asyncio
    async def test_no_fantasy_exclusion_explicit_movie(self, parser, empty_state):
        """Test: 'no fantasy' for movies should only exclude movie fantasy"""
        result = await parser.parse_intent(
            "Suggest action movies, no fantasy",
            empty_state
        )
        
        assert result.request_type == RequestType.FRESH_SEARCH
        assert result.media_type == MediaType.MOVIE
        assert 28 in result.include_genres  # Action
        assert 14 in result.exclude_genres  # Movie fantasy excluded
        assert 10765 not in result.exclude_genres  # TV should not be excluded when media_type=MOVIE
    
    @pytest.mark.asyncio
    async def test_exclusion_does_not_spread_to_later_genres(self, parser, empty_state):
        """Test: 'No horror, suggest thriller' should not exclude thriller"""
        result = await parser.parse_intent(
            "No horror, suggest some thriller movies",
            empty_state
        )
        
        assert result.request_type == RequestType.FRESH_SEARCH
        assert 27 in result.exclude_genres  # Horror excluded
        assert 53 in result.include_genres  # Thriller included (not excluded)
        assert result.media_type == MediaType.MOVIE


class TestLLMParsing:
    """Test LLM-based parsing with mocked Gemini."""
    
    @pytest.mark.asyncio
    async def test_llm_fresh_search(self, parser, empty_state):
        """Test LLM parsing for fresh search."""
        mock_response = {
            "request_type": "fresh_search",
            "confidence": "high",
            "media_type": "tv",
            "include_genres": [10765],
            "exclude_genres": [],
            "mood": None,
            "tone_modifiers": [],
            "provider_id": None,
            "provider_name": None,
            "watch_region": "IN",
            "response_message": "Finding great sci-fi TV series for you!",
            "clarification_needed": None,
            "raw_user_message": "Suggest some sci-fi TV shows",
            "parser_used": "llm"
        }
        
        mock_interaction = Mock()
        mock_interaction.output_text = json.dumps(mock_response)
        
        mock_client = Mock()
        mock_client.interactions.create.return_value = mock_interaction
        
        with patch.object(parser, '_get_client', return_value=mock_client):
            parser.gemini_configured = True
            
            result = await parser.parse_intent(
                "Suggest some sci-fi TV shows",
                empty_state
            )
            
            assert result.request_type == RequestType.FRESH_SEARCH
            assert result.media_type == MediaType.TV
            assert result.parser_used == "llm"
            assert 10765 in result.include_genres
    
    @pytest.mark.asyncio
    async def test_llm_refinement(self, parser, state_with_scifi):
        """Test LLM parsing for refinement."""
        mock_response = {
            "request_type": "refinement",
            "confidence": "high",
            "media_type": None,
            "include_genres": [18],
            "exclude_genres": [],
            "mood": "emotional",
            "tone_modifiers": ["darker"],
            "response_message": "Adding more dramatic, intense options.",
            "clarification_needed": None,
            "raw_user_message": "Make them darker",
            "parser_used": "llm"
        }
        
        mock_interaction = Mock()
        mock_interaction.output_text = json.dumps(mock_response)
        
        mock_client = Mock()
        mock_client.interactions.create.return_value = mock_interaction
        
        with patch.object(parser, '_get_client', return_value=mock_client):
            parser.gemini_configured = True
            
            result = await parser.parse_intent(
                "Make them darker",
                state_with_scifi
            )
            
            assert result.request_type == RequestType.REFINEMENT
            assert result.parser_used == "llm"
            assert "darker" in result.tone_modifiers
    
    @pytest.mark.asyncio
    async def test_llm_constraint_no_horror(self, parser, state_with_scifi):
        """Test LLM parsing for constraint (exclusion)."""
        mock_response = {
            "request_type": "constraint_only",
            "confidence": "high",
            "media_type": None,
            "include_genres": [],
            "exclude_genres": [27],
            "mood": None,
            "tone_modifiers": [],
            "response_message": "Removing horror from the search.",
            "clarification_needed": None,
            "raw_user_message": "no horror please",
            "parser_used": "llm"
        }
        
        mock_interaction = Mock()
        mock_interaction.output_text = json.dumps(mock_response)
        
        mock_client = Mock()
        mock_client.interactions.create.return_value = mock_interaction
        
        with patch.object(parser, '_get_client', return_value=mock_client):
            parser.gemini_configured = True
            
            result = await parser.parse_intent(
                "no horror please",
                state_with_scifi
            )
            
            assert result.request_type == RequestType.CONSTRAINT_ONLY
            assert result.parser_used == "llm"
            assert 27 in result.exclude_genres
    
    @pytest.mark.asyncio
    async def test_llm_timeout_fallback(self, parser, empty_state):
        """Test LLM timeout falls back to deterministic."""
        import asyncio
        
        mock_client = Mock()
        mock_client.interactions.create.side_effect = asyncio.TimeoutError()
        
        with patch.object(parser, '_get_client', return_value=mock_client):
            parser.gemini_configured = True
            
            result = await parser.parse_intent(
                "Suggest action movies",
                empty_state
            )
            
            # Should fall back to deterministic
            assert result.parser_used == "fallback"
            assert result.request_type == RequestType.FRESH_SEARCH
    
    @pytest.mark.asyncio
    async def test_llm_invalid_json_fallback(self, parser, empty_state):
        """Test LLM invalid JSON falls back to deterministic."""
        mock_interaction = Mock()
        mock_interaction.output_text = "This is not valid JSON at all"
        
        mock_client = Mock()
        mock_client.interactions.create.return_value = mock_interaction
        
        with patch.object(parser, '_get_client', return_value=mock_client):
            parser.gemini_configured = True
            
            result = await parser.parse_intent(
                "Suggest action movies",
                empty_state
            )
            
            # Should fall back to deterministic
            assert result.parser_used == "fallback"
    
    @pytest.mark.asyncio
    async def test_llm_validation_error_fallback(self, parser, empty_state):
        """Test LLM response failing validation falls back."""
        mock_response = {
            "request_type": "invalid_type",  # Invalid enum value
            "confidence": "super_high",  # Invalid enum value
            "media_type": "book",  # Invalid enum value
            "include_genres": ["sci-fi"],  # Should be list of ints
        }
        
        mock_interaction = Mock()
        mock_interaction.output_text = json.dumps(mock_response)
        
        mock_client = Mock()
        mock_client.interactions.create.return_value = mock_interaction
        
        with patch.object(parser, '_get_client', return_value=mock_client):
            parser.gemini_configured = True
            
            result = await parser.parse_intent(
                "Suggest action movies",
                empty_state
            )
            
            # Should fall back to deterministic
            assert result.parser_used == "fallback"
    
    @pytest.mark.asyncio
    async def test_llm_not_configured(self, parser, empty_state):
        """Test parser with no Gemini config uses fallback."""
        parser.gemini_configured = False
        
        result = await parser.parse_intent(
            "Suggest action movies",
            empty_state
        )
        
        assert result.parser_used == "fallback"


class TestEdgeCases:
    """Test edge cases and special scenarios."""
    
    @pytest.mark.asyncio
    async def test_both_media_type(self, parser, empty_state):
        """Test message requesting both movies and TV."""
        result = await parser.parse_intent(
            "Suggest sci-fi movies and TV shows",
            empty_state
        )
        
        assert result.media_type == MediaType.BOTH
        # Should include both movie and TV genre IDs
        assert 878 in result.include_genres or 10765 in result.include_genres
    
    @pytest.mark.asyncio
    async def test_multiple_genres(self, parser, empty_state):
        """Test multiple genres: 'action comedy movies'"""
        result = await parser.parse_intent(
            "action comedy movies",
            empty_state
        )
        
        assert 28 in result.include_genres  # Action
        assert 35 in result.include_genres  # Comedy
        assert result.media_type == MediaType.MOVIE
    
    @pytest.mark.asyncio
    async def test_genre_exclusion_with_inclusion(self, parser, empty_state):
        """Test: 'sci-fi movies but no horror'"""
        result = await parser.parse_intent(
            "sci-fi movies but no horror",
            empty_state
        )
        
        assert 878 in result.include_genres  # Sci-fi
        assert 27 in result.exclude_genres  # Horror
        assert result.media_type == MediaType.MOVIE
    
    @pytest.mark.asyncio
    async def test_confidence_levels(self, parser, empty_state):
        """Test that parser sets appropriate confidence."""
        # Chat should be high confidence
        result = await parser.parse_intent("hi", empty_state)
        assert result.confidence == IntentConfidence.HIGH
        
        # Deterministic fallback should be medium
        result = await parser.parse_intent(
            "Suggest something interesting",
            empty_state
        )
        assert result.confidence == IntentConfidence.MEDIUM
    
    @pytest.mark.asyncio
    async def test_case_insensitive(self, parser, empty_state):
        """Test parser is case-insensitive."""
        result = await parser.parse_intent(
            "SUGGEST SOME SCI-FI MOVIES",
            empty_state
        )
        
        assert result.request_type == RequestType.FRESH_SEARCH
        assert 878 in result.include_genres

    @pytest.mark.asyncio
    async def test_long_casual_greeting_returns_chat_intent(self, parser, empty_state):
        """Test that long casual messages and greetings beyond 7 words return CHAT intent."""
        msg = "Good afternoon Scout, hope you are having an absolutely wonderful day today!"
        result = await parser.parse_intent(msg, empty_state)
        assert result.request_type == RequestType.CHAT
        assert result.include_genres == []
        assert result.response_message != ""

    @pytest.mark.asyncio
    async def test_identity_query_returns_chat_intent(self, parser, empty_state):
        """Test that questions about Scout's identity or abilities return CHAT intent."""
        result = await parser.parse_intent("who are you and what can you do?", empty_state)
        assert result.request_type == RequestType.CHAT
        assert result.include_genres == []

    @pytest.mark.asyncio
    async def test_surprise_me_triggers_fresh_search(self, parser, empty_state):
        """Test that open-ended 'surprise me' triggers discovery recommendation."""
        result = await parser.parse_intent("surprise me!", empty_state)
        assert result.request_type == RequestType.FRESH_SEARCH

    @pytest.mark.asyncio
    async def test_fresh_search_resets_inherited_media_type(self, parser, state_with_scifi):
        """Test that fresh search phrases reset inherited media-type constraints."""
        # state_with_scifi has media_type=MOVIE
        assert state_with_scifi.temporary_constraints.media_type == MediaType.MOVIE
        result = await parser.parse_intent("now suggest something fun", state_with_scifi)
        assert result.request_type == RequestType.FRESH_SEARCH
        assert result.media_type is None


class TestResponseMessages:
    """Test natural response message generation."""
    
    @pytest.mark.asyncio
    async def test_response_message_not_empty(self, parser, empty_state):
        """All parsed intents should have response_message."""
        result = await parser.parse_intent(
            "Suggest action movies",
            empty_state
        )
        
        assert result.response_message
        assert len(result.response_message) > 0
    
    @pytest.mark.asyncio
    async def test_response_message_chat(self, parser, empty_state):
        """Chat response should be friendly."""
        result = await parser.parse_intent("hello", empty_state)
        
        assert "Hey" in result.response_message or "Hello" in result.response_message
    
    @pytest.mark.asyncio
    async def test_response_message_constraint(self, parser, state_with_scifi):
        """Constraint response should acknowledge filter."""
        result = await parser.parse_intent(
            "no horror",
            state_with_scifi
        )
        
        # Should mention removing or excluding
        assert any(word in result.response_message.lower() for word in ['removing', 'filter', 'got it'])


# Integration test with actual validation
class TestSchemaValidation:
    """Test that all outputs pass Phase 1 schema validation."""
    
    @pytest.mark.asyncio
    async def test_all_fields_valid(self, parser, empty_state):
        """Test that parsed intent has all valid Phase 1 fields."""
        result = await parser.parse_intent(
            "Suggest sci-fi TV shows from 2020",
            empty_state
        )
        
        # All required fields should be present
        assert result.request_type is not None
        assert result.confidence is not None
        assert result.response_message is not None
        assert result.raw_user_message is not None
        assert result.parser_used is not None
        
        # Lists should be initialized
        assert isinstance(result.include_genres, list)
        assert isinstance(result.exclude_genres, list)
        assert isinstance(result.tone_modifiers, list)
        
        # watch_region should have default
        assert result.watch_region == "IN"
    
    @pytest.mark.asyncio
    async def test_pydantic_validation_enforced(self, parser, empty_state):
        """Test that invalid data raises ValidationError."""
        # This tests that our parser actually validates
        # We'll mock LLM to return invalid data
        
        mock_response = {
            "request_type": "invalid_type",  # Invalid
            "confidence": "high",
            "response_message": "Test"
        }
        
        mock_interaction = Mock()
        mock_interaction.output_text = json.dumps(mock_response)
        
        mock_client = Mock()
        mock_client.interactions.create.return_value = mock_interaction
        
        with patch.object(parser, '_get_client', return_value=mock_client):
            parser.gemini_configured = True
            
            # Should fall back to deterministic due to validation error
            result = await parser.parse_intent(
                "Suggest action movies",
                empty_state
            )
            
            assert result.parser_used == "fallback"


# Import json for LLM tests
import json
