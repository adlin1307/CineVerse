"""
Tests for state management models (ConversationState, TemporaryConstraints).
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from models.state import (
    ConversationState,
    TemporaryConstraints,
    StateTransition
)


class TestTemporaryConstraints:
    """Test suite for TemporaryConstraints model."""
    
    def test_empty_constraints(self):
        """Test creating empty temporary constraints."""
        constraints = TemporaryConstraints()
        
        assert constraints.include_genres == []
        assert constraints.exclude_genres == []
        assert constraints.mood is None
        assert constraints.provider_id is None
        assert constraints.min_year is None
        assert constraints.max_year is None
        assert constraints.runtime_preference is None
        assert constraints.language is None
        assert constraints.popularity is None
    
    def test_constraints_with_genres(self):
        """Test constraints with genre filters."""
        constraints = TemporaryConstraints(
            include_genres=[878, 12],
            exclude_genres=[27, 53]
        )
        
        # Note: genres are deduplicated and may be reordered
        assert set(constraints.include_genres) == {878, 12}
        assert set(constraints.exclude_genres) == {27, 53}
    
    def test_constraints_with_mood_and_provider(self):
        """Test constraints with mood and provider."""
        constraints = TemporaryConstraints(
            mood="relaxed",
            provider_id=8
        )
        
        assert constraints.mood == "relaxed"
        assert constraints.provider_id == 8
    
    def test_constraints_with_year_range(self):
        """Test constraints with year range."""
        constraints = TemporaryConstraints(
            min_year=2010,
            max_year=2020
        )
        
        assert constraints.min_year == 2010
        assert constraints.max_year == 2020
    
    def test_is_empty_true(self):
        """Test is_empty with no filters."""
        constraints = TemporaryConstraints()
        assert constraints.is_empty()
    
    def test_is_empty_false_with_genres(self):
        """Test is_empty with genre filters."""
        constraints = TemporaryConstraints(include_genres=[878])
        assert not constraints.is_empty()
    
    def test_has_genre_context_true(self):
        """Test has_genre_context with genre filters."""
        constraints = TemporaryConstraints(include_genres=[878])
        assert constraints.has_genre_context()
    
    def test_has_provider_filter_true(self):
        """Test has_provider_filter with provider."""
        constraints = TemporaryConstraints(provider_id=8)
        assert constraints.has_provider_filter()
    
    def test_is_empty_false_with_year(self):
        """Test is_empty with year range."""
        constraints = TemporaryConstraints(min_year=2015)
        assert not constraints.is_empty()


class TestConversationState:
    """Test suite for ConversationState model."""
    
    def test_create_new_conversation(self):
        """Test creating a new conversation state."""
        state = ConversationState(
            conversation_id="conv_123",
            user_profile_id="user_456"
        )
        
        assert state.conversation_id == "conv_123"
        assert state.user_profile_id == "user_456"
        assert state.turn_count == 0
        assert state.last_transition is None
        assert isinstance(state.temporary_constraints, TemporaryConstraints)
    
    def test_conversation_with_constraints(self):
        """Test conversation with temporary constraints."""
        constraints = TemporaryConstraints(
            include_genres=[878],
            mood="curious"
        )
        state = ConversationState(
            conversation_id="conv_123",
            user_profile_id="user_456",
            temporary_constraints=constraints
        )
        
        assert state.temporary_constraints.include_genres == [878]
        assert state.temporary_constraints.mood == "curious"
    
    def test_is_empty_true(self):
        """Test is_empty with no filters."""
        state = ConversationState(
            conversation_id="conv_123",
            user_profile_id="user_456"
        )
        
        assert state.temporary_constraints.is_empty()
    
    def test_is_empty_false(self):
        """Test is_empty with filters."""
        state = ConversationState(
            conversation_id="conv_123",
            user_profile_id="user_456",
            temporary_constraints=TemporaryConstraints(mood="relaxed")
        )
        
        assert not state.temporary_constraints.is_empty()
    
    def test_add_parser_history(self):
        """Test adding to parser history."""
        state = ConversationState(
            conversation_id="conv_123",
            user_profile_id="user_456"
        )
        
        state.parser_history.append("gemini")
        
        assert len(state.parser_history) == 1
        assert state.parser_history[0] == "gemini"
    
    def test_increment_turn_count(self):
        """Test incrementing turn count."""
        state = ConversationState(
            conversation_id="conv_123",
            user_profile_id="user_456"
        )
        
        state.increment_turn()
        assert state.turn_count == 1
    
    def test_state_transition_update(self):
        """Test updating state transition."""
        state = ConversationState(
            conversation_id="conv_123",
            user_profile_id="user_456"
        )
        
        state.record_transition(StateTransition.APPLY_FRESH)
        assert state.last_transition == StateTransition.APPLY_FRESH
    
    def test_missing_required_fields(self):
        """Test that optional IDs can be None."""
        # All fields are optional, so this should work
        state = ConversationState()
        
        assert state.conversation_id is None
        assert state.user_profile_id is None
