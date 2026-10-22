"""
Tests for Conversation State Machine (Phase 3)

Validates state transitions and constraint management.
"""

import pytest
from datetime import datetime, UTC

from services.conversation_state import ConversationStateMachine, conversation_state_machine
from models.intent import ParsedIntent, RequestType, MediaType, IntentConfidence
from models.state import ConversationState, TemporaryConstraints, StateTransition


@pytest.fixture
def state_machine():
    """Create state machine instance."""
    return ConversationStateMachine()


@pytest.fixture
def fresh_intent_scifi_tv():
    """Fresh search intent: sci-fi TV shows."""
    return ParsedIntent(
        request_type=RequestType.FRESH_SEARCH,
        confidence=IntentConfidence.HIGH,
        media_type=MediaType.TV,
        include_genres=[10765],
        exclude_genres=[],
        response_message="Finding great sci-fi TV series!",
        raw_user_message="Suggest sci-fi TV shows",
        parser_used="fallback"
    )


@pytest.fixture
def refinement_darker():
    """Refinement intent: make them darker."""
    return ParsedIntent(
        request_type=RequestType.REFINEMENT,
        confidence=IntentConfidence.HIGH,
        media_type=None,
        include_genres=[18],  # Drama
        exclude_genres=[],
        mood="emotional",
        tone_modifiers=["darker"],
        response_message="Adding more dramatic options.",
        raw_user_message="Make them darker",
        parser_used="fallback"
    )


@pytest.fixture
def constraint_no_horror():
    """Constraint intent: no horror."""
    return ParsedIntent(
        request_type=RequestType.CONSTRAINT_ONLY,
        confidence=IntentConfidence.HIGH,
        media_type=None,
        include_genres=[],
        exclude_genres=[27],  # Horror
        response_message="Removing horror from search.",
        raw_user_message="no horror",
        parser_used="fallback"
    )


@pytest.fixture
def correction_movies():
    """Correction intent: actually I want movies."""
    return ParsedIntent(
        request_type=RequestType.CORRECTION,
        confidence=IntentConfidence.HIGH,
        media_type=MediaType.MOVIE,
        include_genres=[],
        exclude_genres=[],
        response_message="Switching to movies.",
        raw_user_message="actually I want movies",
        parser_used="fallback"
    )


@pytest.fixture
def chat_greeting():
    """Chat intent: greeting."""
    return ParsedIntent(
        request_type=RequestType.CHAT,
        confidence=IntentConfidence.HIGH,
        media_type=None,
        include_genres=[],
        exclude_genres=[],
        response_message="Hey! Ready to find something great?",
        raw_user_message="hi",
        parser_used="fallback"
    )


class TestFreshSearchTransition:
    """Test fresh search transitions."""
    
    def test_fresh_search_from_empty_state(self, state_machine, fresh_intent_scifi_tv):
        """Fresh search creates new state with constraints."""
        result = state_machine.apply_intent(fresh_intent_scifi_tv, None)
        
        assert result.temporary_constraints.media_type == MediaType.TV
        assert 10765 in result.temporary_constraints.include_genres
        assert result.temporary_constraints.exclude_genres == []
        assert result.last_transition == StateTransition.APPLY_FRESH
        assert result.turn_count == 1
    
    def test_fresh_search_clears_previous_constraints(self, state_machine, fresh_intent_scifi_tv):
        """Fresh search clears unrelated previous constraints."""
        # Start with action movies and no horror
        existing_state = ConversationState(
            temporary_constraints=TemporaryConstraints(
                media_type=MediaType.MOVIE,
                include_genres=[28],  # Action
                exclude_genres=[27],  # Horror
                mood="excited"
            )
        )
        
        # Apply fresh search for sci-fi TV
        result = state_machine.apply_intent(fresh_intent_scifi_tv, existing_state)
        
        # Previous constraints should be cleared
        assert result.temporary_constraints.media_type == MediaType.TV
        assert result.temporary_constraints.include_genres == [10765]  # Only sci-fi TV
        assert 28 not in result.temporary_constraints.include_genres  # Action cleared
        assert result.temporary_constraints.exclude_genres == []  # Horror exclusion cleared
        assert result.temporary_constraints.mood is None  # Mood cleared
    
    def test_fresh_search_with_exclusions(self, state_machine):
        """Fresh search can include exclusions."""
        intent = ParsedIntent(
            request_type=RequestType.FRESH_SEARCH,
            confidence=IntentConfidence.HIGH,
            media_type=MediaType.MOVIE,
            include_genres=[878],  # Sci-fi
            exclude_genres=[27],  # No horror
            response_message="Sci-fi movies without horror!",
            raw_user_message="sci-fi movies but no horror",
            parser_used="fallback"
        )
        
        result = state_machine.apply_intent(intent, None)
        
        assert 878 in result.temporary_constraints.include_genres
        assert 27 in result.temporary_constraints.exclude_genres


class TestRefinementTransition:
    """Test refinement transitions."""
    
    def test_refinement_preserves_context(self, state_machine, fresh_intent_scifi_tv, refinement_darker):
        """Refinement preserves existing search context."""
        # Start with sci-fi TV
        state = state_machine.apply_intent(fresh_intent_scifi_tv, None)
        
        # Refine with "darker"
        result = state_machine.apply_intent(refinement_darker, state)
        
        # Should preserve sci-fi TV and add drama + mood
        assert result.temporary_constraints.media_type == MediaType.TV
        assert 10765 in result.temporary_constraints.include_genres  # Sci-fi preserved
        assert 18 in result.temporary_constraints.include_genres  # Drama added
        assert result.temporary_constraints.mood == "emotional"
        assert "darker" in result.temporary_constraints.tone_modifiers
        assert result.last_transition == StateTransition.APPLY_REFINEMENT
    
    def test_refinement_accumulates_genres(self, state_machine):
        """Refinements accumulate genres, don't replace."""
        # Start with action
        state = ConversationState(
            temporary_constraints=TemporaryConstraints(
                media_type=MediaType.MOVIE,
                include_genres=[28]  # Action
            )
        )
        
        # Add thriller
        intent = ParsedIntent(
            request_type=RequestType.REFINEMENT,
            confidence=IntentConfidence.HIGH,
            include_genres=[53],  # Thriller
            exclude_genres=[],
            response_message="Adding thriller elements.",
            raw_user_message="add thriller",
            parser_used="fallback"
        )
        
        result = state_machine.apply_intent(intent, state)
        
        # Should have both action and thriller
        assert 28 in result.temporary_constraints.include_genres
        assert 53 in result.temporary_constraints.include_genres
        assert len(result.temporary_constraints.include_genres) == 2
    
    def test_refinement_updates_mood(self, state_machine):
        """Refinement can update mood."""
        state = ConversationState(
            temporary_constraints=TemporaryConstraints(
                media_type=MediaType.MOVIE,
                include_genres=[35],  # Comedy
                mood="relaxed"
            )
        )
        
        intent = ParsedIntent(
            request_type=RequestType.REFINEMENT,
            confidence=IntentConfidence.HIGH,
            include_genres=[],
            exclude_genres=[],
            mood="excited",
            response_message="Shifting to more exciting options.",
            raw_user_message="something more exciting",
            parser_used="fallback"
        )
        
        result = state_machine.apply_intent(intent, state)
        
        assert result.temporary_constraints.mood == "excited"  # Updated
        assert 35 in result.temporary_constraints.include_genres  # Genre preserved


class TestConstraintOnlyTransition:
    """Test constraint-only transitions."""
    
    def test_constraint_adds_exclusion(self, state_machine, fresh_intent_scifi_tv, constraint_no_horror):
        """Constraint-only adds exclusions without changing search."""
        # Start with sci-fi TV
        state = state_machine.apply_intent(fresh_intent_scifi_tv, None)
        
        # Add "no horror" constraint
        result = state_machine.apply_intent(constraint_no_horror, state)
        
        # Original search preserved
        assert result.temporary_constraints.media_type == MediaType.TV
        assert 10765 in result.temporary_constraints.include_genres
        
        # Exclusion added
        assert 27 in result.temporary_constraints.exclude_genres
        assert result.last_transition == StateTransition.APPLY_CONSTRAINT
    
    def test_constraint_accumulates_exclusions(self, state_machine):
        """Multiple constraints accumulate exclusions."""
        state = ConversationState(
            temporary_constraints=TemporaryConstraints(
                media_type=MediaType.MOVIE,
                include_genres=[28],  # Action
                exclude_genres=[27]  # No horror
            )
        )
        
        # Add "no thriller" constraint
        intent = ParsedIntent(
            request_type=RequestType.CONSTRAINT_ONLY,
            confidence=IntentConfidence.HIGH,
            include_genres=[],
            exclude_genres=[53],  # Thriller
            response_message="Also removing thriller.",
            raw_user_message="no thriller either",
            parser_used="fallback"
        )
        
        result = state_machine.apply_intent(intent, state)
        
        # Should have both exclusions
        assert 27 in result.temporary_constraints.exclude_genres
        assert 53 in result.temporary_constraints.exclude_genres
        assert len(result.temporary_constraints.exclude_genres) == 2
    
    def test_constraint_exclusions_are_hard(self, state_machine):
        """Exclusions remain as hard constraints."""
        state = ConversationState(
            temporary_constraints=TemporaryConstraints(
                include_genres=[878]  # Sci-fi
            )
        )
        
        # Add horror exclusion
        intent = ParsedIntent(
            request_type=RequestType.CONSTRAINT_ONLY,
            confidence=IntentConfidence.HIGH,
            include_genres=[],
            exclude_genres=[27],
            response_message="No horror.",
            raw_user_message="no horror",
            parser_used="fallback"
        )
        
        result = state_machine.apply_intent(intent, state)
        
        # Horror is excluded (hard constraint)
        assert 27 in result.temporary_constraints.exclude_genres
        assert 27 not in result.temporary_constraints.include_genres


class TestCorrectionTransition:
    """Test correction transitions."""
    
    def test_correction_updates_media_type(self, state_machine, fresh_intent_scifi_tv, correction_movies):
        """Correction can change media type."""
        # Start with TV
        state = state_machine.apply_intent(fresh_intent_scifi_tv, None)
        
        # Correct to movies
        result = state_machine.apply_intent(correction_movies, state)
        
        assert result.temporary_constraints.media_type == MediaType.MOVIE
        assert result.last_media_type == MediaType.MOVIE
        assert result.last_transition == StateTransition.APPLY_CORRECTION
    
    def test_correction_replaces_genres(self, state_machine):
        """Correction replaces genre preferences."""
        state = ConversationState(
            temporary_constraints=TemporaryConstraints(
                include_genres=[28, 53]  # Action, Thriller
            )
        )
        
        # Correct to just comedy
        intent = ParsedIntent(
            request_type=RequestType.CORRECTION,
            confidence=IntentConfidence.HIGH,
            include_genres=[35],  # Comedy
            exclude_genres=[],
            response_message="Switching to comedy.",
            raw_user_message="actually I want comedy",
            parser_used="fallback"
        )
        
        result = state_machine.apply_intent(intent, state)
        
        # Genres replaced, not accumulated
        assert result.temporary_constraints.include_genres == [35]
        assert 28 not in result.temporary_constraints.include_genres
        assert 53 not in result.temporary_constraints.include_genres

    def test_correction_accumulates_genre_exclusions(self, state_machine):
        """Correction preserves and accumulates existing genre exclusions."""
        state = ConversationState(
            temporary_constraints=TemporaryConstraints(
                include_genres=[28],  # Action
                exclude_genres=[27]   # No horror
            )
        )
        
        # Add no romance as correction
        intent = ParsedIntent(
            request_type=RequestType.CORRECTION,
            confidence=IntentConfidence.HIGH,
            include_genres=[28],
            exclude_genres=[10749],  # No romance
            response_message="No romance either.",
            raw_user_message="actually no romance either",
            parser_used="fallback"
        )
        
        result = state_machine.apply_intent(intent, state)
        assert 27 in result.temporary_constraints.exclude_genres
        assert 10749 in result.temporary_constraints.exclude_genres


class TestClarificationAndChat:
    """Test clarification and chat transitions."""
    
    def test_chat_preserves_context(self, state_machine, fresh_intent_scifi_tv, chat_greeting):
        """Chat messages preserve search context."""
        # Start with sci-fi TV search
        state = state_machine.apply_intent(fresh_intent_scifi_tv, None)
        
        # User says "thanks"
        result = state_machine.apply_intent(chat_greeting, state)
        
        # Context preserved
        assert result.temporary_constraints.media_type == MediaType.TV
        assert 10765 in result.temporary_constraints.include_genres
        
        # No transition recorded for chat
        assert result.last_transition == StateTransition.APPLY_FRESH  # Still from previous
    
    def test_clarification_preserves_context(self, state_machine):
        """Clarification requests preserve context."""
        state = ConversationState(
            temporary_constraints=TemporaryConstraints(
                media_type=MediaType.MOVIE,
                include_genres=[878, 18],
                exclude_genres=[27]
            )
        )
        
        intent = ParsedIntent(
            request_type=RequestType.CLARIFICATION,
            confidence=IntentConfidence.LOW,
            include_genres=[],
            exclude_genres=[],
            response_message="Did you want recent releases or classics?",
            clarification_needed="year_range",
            raw_user_message="something interesting",
            parser_used="fallback"
        )
        
        result = state_machine.apply_intent(intent, state)
        
        # All constraints preserved
        assert result.temporary_constraints.media_type == MediaType.MOVIE
        assert set(result.temporary_constraints.include_genres) == {878, 18}
        assert set(result.temporary_constraints.exclude_genres) == {27}


class TestEmptyAndMissingState:
    """Test handling of empty or missing state."""
    
    def test_none_state_initializes(self, state_machine, fresh_intent_scifi_tv):
        """None state is safely initialized."""
        result = state_machine.apply_intent(fresh_intent_scifi_tv, None)
        
        assert result is not None
        assert result.turn_count == 1
        assert result.temporary_constraints is not None
    
    def test_empty_constraints_handled(self, state_machine):
        """Empty constraints don't cause errors."""
        state = ConversationState()
        
        intent = ParsedIntent(
            request_type=RequestType.REFINEMENT,
            confidence=IntentConfidence.HIGH,
            include_genres=[28],
            exclude_genres=[],
            response_message="Adding action.",
            raw_user_message="action",
            parser_used="fallback"
        )
        
        result = state_machine.apply_intent(intent, state)
        
        assert 28 in result.temporary_constraints.include_genres


class TestMultiTurnSequence:
    """Test multi-turn conversation sequences."""
    
    def test_five_turn_sequence(self, state_machine):
        """Test realistic five-turn conversation."""
        state = None
        
        # Turn 1: Fresh search - sci-fi TV
        intent1 = ParsedIntent(
            request_type=RequestType.FRESH_SEARCH,
            confidence=IntentConfidence.HIGH,
            media_type=MediaType.TV,
            include_genres=[10765],
            exclude_genres=[],
            response_message="Sci-fi TV!",
            raw_user_message="sci-fi TV shows",
            parser_used="fallback"
        )
        state = state_machine.apply_intent(intent1, state)
        assert state.turn_count == 1
        assert 10765 in state.temporary_constraints.include_genres
        
        # Turn 2: Refinement - make darker
        intent2 = ParsedIntent(
            request_type=RequestType.REFINEMENT,
            confidence=IntentConfidence.HIGH,
            include_genres=[18],  # Drama
            exclude_genres=[],
            mood="emotional",
            tone_modifiers=["darker"],
            response_message="Darker!",
            raw_user_message="darker",
            parser_used="fallback"
        )
        state = state_machine.apply_intent(intent2, state)
        assert state.turn_count == 2
        assert 10765 in state.temporary_constraints.include_genres
        assert 18 in state.temporary_constraints.include_genres
        assert state.temporary_constraints.mood == "emotional"
        
        # Turn 3: Constraint - no horror
        intent3 = ParsedIntent(
            request_type=RequestType.CONSTRAINT_ONLY,
            confidence=IntentConfidence.HIGH,
            include_genres=[],
            exclude_genres=[27],
            response_message="No horror.",
            raw_user_message="no horror",
            parser_used="fallback"
        )
        state = state_machine.apply_intent(intent3, state)
        assert state.turn_count == 3
        assert 27 in state.temporary_constraints.exclude_genres
        assert 10765 in state.temporary_constraints.include_genres  # Preserved
        
        # Turn 4: Fresh search - Disney TV (should clear previous)
        intent4 = ParsedIntent(
            request_type=RequestType.FRESH_SEARCH,
            confidence=IntentConfidence.HIGH,
            media_type=MediaType.TV,
            include_genres=[],
            exclude_genres=[],
            provider_name="Disney+ Hotstar",
            response_message="Disney TV!",
            raw_user_message="Disney TV shows",
            parser_used="fallback"
        )
        state = state_machine.apply_intent(intent4, state)
        assert state.turn_count == 4
        assert state.temporary_constraints.include_genres == []  # Cleared
        assert state.temporary_constraints.exclude_genres == []  # Cleared
        assert state.temporary_constraints.provider_name == "Disney+ Hotstar"
        
        # Turn 5: Chat - preserve Disney context
        intent5 = ParsedIntent(
            request_type=RequestType.CHAT,
            confidence=IntentConfidence.HIGH,
            include_genres=[],
            exclude_genres=[],
            response_message="Sure thing!",
            raw_user_message="thanks",
            parser_used="fallback"
        )
        state = state_machine.apply_intent(intent5, state)
        assert state.turn_count == 5
        assert state.temporary_constraints.provider_name == "Disney+ Hotstar"  # Preserved


class TestConstraintRemoval:
    """Test removing specific constraints."""
    
    def test_remove_exclusion(self, state_machine):
        """Remove specific exclusion."""
        state = ConversationState(
            temporary_constraints=TemporaryConstraints(
                include_genres=[878],
                exclude_genres=[27, 53]  # Horror, Thriller
            )
        )
        
        result = state_machine.remove_constraint(state, "exclude_genre", 27)
        
        assert 27 not in result.temporary_constraints.exclude_genres
        assert 53 in result.temporary_constraints.exclude_genres  # Other exclusion preserved
    
    def test_remove_mood(self, state_machine):
        """Remove mood constraint."""
        state = ConversationState(
            temporary_constraints=TemporaryConstraints(
                include_genres=[35],
                mood="excited"
            )
        )
        
        result = state_machine.remove_constraint(state, "mood")
        
        assert result.temporary_constraints.mood is None
        assert 35 in result.temporary_constraints.include_genres  # Genre preserved
    
    def test_clear_state(self, state_machine):
        """Clear all constraints."""
        state = ConversationState(
            temporary_constraints=TemporaryConstraints(
                media_type=MediaType.TV,
                include_genres=[10765, 18],
                exclude_genres=[27],
                mood="emotional"
            )
        )
        
        result = state_machine.clear_state(state)
        
        assert result.temporary_constraints.is_empty()
        assert result.last_transition == StateTransition.CLEAR
