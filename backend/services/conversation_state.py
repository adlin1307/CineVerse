"""
Conversation State Machine for Scout.

Manages state transitions based on parsed intents, preserving or clearing
constraints appropriately for each request type.
"""

from typing import Optional
from copy import deepcopy

from models.intent import ParsedIntent, RequestType, MediaType
from models.state import ConversationState, TemporaryConstraints, StateTransition


class ConversationStateMachine:
    """
    State machine for managing Scout conversation state.
    
    Handles transitions between different intent types, ensuring:
    - Fresh searches clear unrelated constraints
    - Refinements preserve relevant context
    - Hard exclusions persist correctly
    - Corrections update only specified fields
    """
    
    def apply_intent(
        self,
        intent: ParsedIntent,
        current_state: Optional[ConversationState] = None
    ) -> ConversationState:
        """
        Apply parsed intent to conversation state.
        
        Args:
            intent: Parsed intent from user message
            current_state: Current conversation state (None for new conversation)
        
        Returns:
            Updated conversation state
        """
        # Initialize state if None
        if current_state is None:
            current_state = ConversationState()
            current_state.record_transition(StateTransition.INITIALIZE)
        
        # Increment turn
        current_state.increment_turn()
        
        # Update metadata
        current_state.last_request_type = intent.request_type.value
        current_state.last_response_message = intent.response_message
        
        # Apply transition based on request type
        if intent.request_type in (RequestType.FRESH_SEARCH, RequestType.NEW_SEARCH):
            new_state = self._apply_fresh_search(intent, current_state)
        elif intent.request_type == RequestType.REFINEMENT:
            new_state = self._apply_refinement(intent, current_state)
        elif intent.request_type in (RequestType.CONSTRAINT_ONLY, RequestType.CONSTRAINT_UPDATE):
            new_state = self._apply_constraint(intent, current_state)
        elif intent.request_type == RequestType.CORRECTION:
            new_state = self._apply_correction(intent, current_state)
        elif intent.request_type == RequestType.TITLE_QUESTION:
            new_state = self._apply_title_question(intent, current_state)
        elif intent.request_type in (RequestType.CLARIFICATION, RequestType.CHAT):
            new_state = self._preserve_context(intent, current_state)
        else:
            # Unknown type - preserve context safely
            new_state = self._preserve_context(intent, current_state)
        
        return new_state
    
    def _apply_title_question(
        self,
        intent: ParsedIntent,
        current_state: ConversationState
    ) -> ConversationState:
        """Preserve context for title questions."""
        current_state.record_transition(StateTransition.TITLE_QUESTION, intent.parser_used)
        return current_state
    
    def _apply_fresh_search(
        self,
        intent: ParsedIntent,
        current_state: ConversationState
    ) -> ConversationState:
        """
        Apply fresh search intent.
        
        Fresh search clears previous constraints and starts new search context.
        """
        # Create fresh constraints from intent
        new_constraints = TemporaryConstraints(
            include_genres=intent.include_genres.copy() if intent.include_genres else [],
            exclude_genres=intent.exclude_genres.copy() if intent.exclude_genres else [],
            media_type=intent.media_type,
            mood=intent.mood,
            emotional_sub_intent=intent.emotional_sub_intent,
            tone_modifiers=intent.tone_modifiers.copy() if intent.tone_modifiers else [],
            provider_id=intent.provider_id,
            provider_name=intent.provider_name,
            watch_region=intent.watch_region,
            min_year=intent.min_year,
            max_year=intent.max_year,
            runtime_preference=intent.runtime_preference,
            language=intent.language,
            popularity=intent.popularity,
            count=intent.count
        )
        
        # Update state - clear previous constraints
        current_state.temporary_constraints = new_constraints
        current_state.last_media_type = intent.media_type
        current_state.record_transition(StateTransition.APPLY_FRESH, intent.parser_used)
        
        return current_state
    
    def _apply_refinement(
        self,
        intent: ParsedIntent,
        current_state: ConversationState
    ) -> ConversationState:
        """
        Apply refinement intent.
        
        Refinements preserve existing context and layer new constraints on top.
        """
        constraints = current_state.temporary_constraints
        
        # Add new genres (don't replace)
        if intent.include_genres:
            for genre_id in intent.include_genres:
                if genre_id not in constraints.include_genres:
                    constraints.include_genres.append(genre_id)
        
        if intent.exclude_genres:
            for genre_id in intent.exclude_genres:
                if genre_id not in constraints.exclude_genres:
                    constraints.exclude_genres.append(genre_id)
                if genre_id in constraints.include_genres:
                    constraints.include_genres.remove(genre_id)
        
        # Update mood if specified (refinement can change mood)
        if intent.mood:
            constraints.mood = intent.mood
        
        # Update emotional sub-intent if specified
        if intent.emotional_sub_intent:
            constraints.emotional_sub_intent = intent.emotional_sub_intent
        
        # Append tone modifiers (don't replace)
        if intent.tone_modifiers:
            for modifier in intent.tone_modifiers:
                if modifier not in constraints.tone_modifiers:
                    constraints.tone_modifiers.append(modifier)
        
        # Update runtime if specified
        if intent.runtime_preference:
            constraints.runtime_preference = intent.runtime_preference
        
        # Media type can be refined (e.g., "actually TV only")
        if intent.media_type:
            constraints.media_type = intent.media_type
            current_state.last_media_type = intent.media_type
        
        # Year range can be refined
        if intent.min_year is not None:
            constraints.min_year = intent.min_year
        if intent.max_year is not None:
            constraints.max_year = intent.max_year
        
        # Language and popularity can be refined
        if intent.language:
            constraints.language = intent.language
        if intent.popularity:
            constraints.popularity = intent.popularity
        if intent.count:
            constraints.count = intent.count
        if intent.count:
            constraints.count = intent.count
        
        current_state.record_transition(StateTransition.APPLY_REFINEMENT, intent.parser_used)
        
        return current_state
    
    def _apply_constraint(
        self,
        intent: ParsedIntent,
        current_state: ConversationState
    ) -> ConversationState:
        """
        Apply constraint-only intent.
        
        Adds new constraints without changing the base search.
        """
        constraints = current_state.temporary_constraints
        
        # Add exclusions (most common constraint-only case)
        if intent.exclude_genres:
            for genre_id in intent.exclude_genres:
                if genre_id not in constraints.exclude_genres:
                    constraints.exclude_genres.append(genre_id)
                if genre_id in constraints.include_genres:
                    constraints.include_genres.remove(genre_id)
        
        # Can also add inclusions
        if intent.include_genres:
            for genre_id in intent.include_genres:
                if genre_id not in constraints.exclude_genres:
                    if genre_id not in constraints.include_genres:
                        constraints.include_genres.append(genre_id)
        
        # Runtime constraint
        if intent.runtime_preference:
            constraints.runtime_preference = intent.runtime_preference
        
        # Year constraints
        if intent.min_year is not None:
            constraints.min_year = intent.min_year
        if intent.max_year is not None:
            constraints.max_year = intent.max_year
        
        # Provider constraint (e.g., "only Netflix")
        if intent.provider_id is not None:
            constraints.provider_id = intent.provider_id
        if intent.provider_name:
            constraints.provider_name = intent.provider_name
        if intent.count:
            constraints.count = intent.count
        
        current_state.record_transition(StateTransition.APPLY_CONSTRAINT, intent.parser_used)
        
        return current_state
    
    def _apply_correction(
        self,
        intent: ParsedIntent,
        current_state: ConversationState
    ) -> ConversationState:
        """
        Apply correction intent.
        
        Corrects or removes specific constraints.
        """
        constraints = current_state.temporary_constraints
        
        # Media type correction (e.g., "actually I want TV shows")
        if intent.media_type:
            constraints.media_type = intent.media_type
            current_state.last_media_type = intent.media_type
        
        # Mood correction
        if intent.mood:
            constraints.mood = intent.mood
            
        # Emotional sub-intent correction (e.g. "I meant I wanna cry!!")
        if intent.emotional_sub_intent:
            constraints.emotional_sub_intent = intent.emotional_sub_intent
        
        # Genre correction: replace if specified
        if intent.include_genres:
            constraints.include_genres = [g for g in intent.include_genres if g not in constraints.exclude_genres]
        
        if intent.exclude_genres:
            # For corrections, accumulate exclusions rather than overwriting previous ones
            for genre_id in intent.exclude_genres:
                if genre_id not in constraints.exclude_genres:
                    constraints.exclude_genres.append(genre_id)
            constraints.include_genres = [g for g in constraints.include_genres if g not in constraints.exclude_genres]
        
        # Runtime correction
        if intent.runtime_preference:
            constraints.runtime_preference = intent.runtime_preference
        
        # Year correction
        if intent.min_year is not None:
            constraints.min_year = intent.min_year
        if intent.max_year is not None:
            constraints.max_year = intent.max_year
        
        # Provider correction
        if intent.provider_id is not None:
            constraints.provider_id = intent.provider_id
        if intent.provider_name:
            constraints.provider_name = intent.provider_name
        
        current_state.record_transition(StateTransition.APPLY_CORRECTION, intent.parser_used)
        
        return current_state
    
    def _preserve_context(
        self,
        intent: ParsedIntent,
        current_state: ConversationState
    ) -> ConversationState:
        """
        Preserve context for clarification/chat.
        
        No changes to constraints, just update metadata.
        """
        # No constraint changes for chat/clarification
        # Just record the parser used
        if intent.parser_used:
            current_state.parser_history.append(intent.parser_used)
        
        return current_state
    
    def clear_state(self, current_state: ConversationState) -> ConversationState:
        """
        Clear all constraints and reset state.
        
        Preserves conversation metadata but clears constraints.
        """
        current_state.temporary_constraints = TemporaryConstraints()
        current_state.record_transition(StateTransition.CLEAR)
        return current_state
    
    def remove_constraint(
        self,
        current_state: ConversationState,
        constraint_type: str,
        value: Optional[any] = None
    ) -> ConversationState:
        """
        Remove a specific constraint.
        
        Args:
            current_state: Current state
            constraint_type: Type of constraint to remove ('genre', 'mood', 'provider', etc.)
            value: Specific value to remove (e.g., genre ID)
        
        Returns:
            Updated state
        """
        constraints = current_state.temporary_constraints
        
        if constraint_type == "genre" and value:
            # Remove from both include and exclude
            if value in constraints.include_genres:
                constraints.include_genres.remove(value)
            if value in constraints.exclude_genres:
                constraints.exclude_genres.remove(value)
        
        elif constraint_type == "exclude_genre" and value:
            if value in constraints.exclude_genres:
                constraints.exclude_genres.remove(value)
        
        elif constraint_type == "mood":
            constraints.mood = None
        
        elif constraint_type == "provider":
            constraints.provider_id = None
            constraints.provider_name = None
        
        elif constraint_type == "runtime":
            constraints.runtime_preference = None
        
        elif constraint_type == "year_range":
            constraints.min_year = None
            constraints.max_year = None
        
        return current_state


# Global instance
conversation_state_machine = ConversationStateMachine()
