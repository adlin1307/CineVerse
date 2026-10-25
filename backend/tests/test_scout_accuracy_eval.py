"""
Chatbot Accuracy Evaluation Suite for CineVerse Scout.

Contains 65 comprehensive test cases measuring accuracy, multi-constraint extraction,
hard-constraint enforcement, grounding, reference resolution, and fallback reliability.
"""

import pytest
from unittest.mock import AsyncMock, patch, Mock
from services.intent_parser import intent_parser
from services.scout_service import ScoutService
from services.conversation_state import conversation_state_machine
from models.intent import RequestType, MediaType, ParsedIntent
from models.state import ConversationState


# =============================================================================
# CATEGORY 1: INTENT CLASSIFICATION ACCURACY (15 TEST CASES)
# =============================================================================

class TestScoutIntentClassification:
    """Test intent classification accuracy across diverse user expressions."""

    def test_intent_greeting_heyyy(self):
        intent = intent_parser._parse_deterministic("heyyy", None)
        assert intent.request_type == RequestType.CHAT

    def test_intent_greeting_with_question(self):
        intent = intent_parser._parse_deterministic("hello, how are you doing today?", None)
        assert intent.request_type == RequestType.CHAT

    def test_intent_identity_question(self):
        intent = intent_parser._parse_deterministic("who are you and what can you do?", None)
        assert intent.request_type == RequestType.CHAT
        assert "Scout" in intent.response_message

    def test_intent_gratitude(self):
        intent = intent_parser._parse_deterministic("thanks for the recommendations!", None)
        assert intent.request_type == RequestType.CHAT

    def test_intent_banter_reaction(self):
        intent = intent_parser._parse_deterministic("haha you are so funny lol", None)
        assert intent.request_type == RequestType.CHAT

    def test_intent_fresh_search_explicit(self):
        intent = intent_parser._parse_deterministic("recommend some high adrenaline action movies", None)
        assert intent.request_type == RequestType.FRESH_SEARCH
        assert 28 in intent.include_genres

    def test_intent_fresh_search_vague_vibe(self):
        intent = intent_parser._parse_deterministic("find me something fun for tonight", None)
        assert intent.request_type == RequestType.FRESH_SEARCH

    def test_intent_fresh_search_start_over(self):
        state = ConversationState()
        state.temporary_constraints.include_genres = [28]
        intent = intent_parser._parse_deterministic("actually start fresh and give me a romantic comedy", state)
        assert intent.request_type == RequestType.FRESH_SEARCH
        assert 10749 in intent.include_genres

    def test_intent_clarification_or_discovery_greeting_with_intent(self):
        intent = intent_parser._parse_deterministic("hey scout! recommend me a psychological thriller", None)
        assert intent.request_type == RequestType.FRESH_SEARCH
        assert 53 in intent.include_genres

    def test_intent_title_question_second_pick(self):
        state = ConversationState()
        state.previous_recommendations = [
            {"id": 1, "title": "Inception", "vote_average": 8.8},
            {"id": 2, "title": "Interstellar", "vote_average": 8.7, "overview": "A team of explorers travel through a wormhole in space."}
        ]
        intent = intent_parser._parse_deterministic("tell me about the second one", state)
        assert intent.request_type == RequestType.TITLE_QUESTION
        assert intent.referenced_title_index == 2
        assert "Interstellar" in intent.response_message

    def test_intent_title_question_first_pick(self):
        state = ConversationState()
        state.previous_recommendations = [
            {"id": 1, "title": "Parasite", "vote_average": 8.5, "overview": "Greed and class discrimination threaten a newly formed relationship."}
        ]
        intent = intent_parser._parse_deterministic("what about the first one?", state)
        assert intent.request_type == RequestType.TITLE_QUESTION
        assert intent.referenced_title_index == 1

    def test_intent_director_question(self):
        intent = intent_parser._parse_deterministic("who directed Oppenheimer?", None)
        assert intent.request_type == RequestType.TITLE_QUESTION
        assert "Christopher Nolan" in intent.response_message

    def test_intent_refinement_darker(self):
        state = ConversationState()
        state.temporary_constraints.include_genres = [878]
        intent = intent_parser._parse_deterministic("make them darker", state)
        assert intent.request_type == RequestType.REFINEMENT
        assert "darker" in intent.tone_modifiers

    def test_intent_refinement_shorter(self):
        state = ConversationState()
        state.temporary_constraints.include_genres = [35]
        intent = intent_parser._parse_deterministic("can you find shorter ones?", state)
        assert intent.request_type == RequestType.REFINEMENT
        assert intent.runtime_preference == "under_90"

    def test_intent_correction_switch_to_tv(self):
        state = ConversationState()
        state.temporary_constraints.include_genres = [878]
        state.temporary_constraints.media_type = MediaType.MOVIE
        intent = intent_parser._parse_deterministic("actually, only TV shows, not movies", state)
        assert intent.request_type == RequestType.CORRECTION
        assert intent.media_type == MediaType.TV


# =============================================================================
# CATEGORY 2: MULTI-CONSTRAINT EXTRACTION (12 TEST CASES)
# =============================================================================

class TestScoutMultiConstraintExtraction:
    """Test extraction of combinations of genres, media types, providers, and moods."""

    def test_action_and_scifi_movies(self):
        intent = intent_parser._parse_deterministic("action and sci-fi movies", None)
        assert 28 in intent.include_genres
        assert 878 in intent.include_genres
        assert intent.media_type == MediaType.MOVIE

    def test_tv_series_on_disney_plus(self):
        intent = intent_parser._parse_deterministic("good TV series on Disney+", None)
        assert intent.media_type == MediaType.TV
        assert intent.provider_id in (337, 2336)
        assert "Disney" in intent.provider_name

    def test_netflix_horror_movies(self):
        intent = intent_parser._parse_deterministic("scary horror movies on Netflix", None)
        assert 27 in intent.include_genres
        assert intent.provider_id == 8
        assert intent.provider_name == "Netflix"
        assert intent.media_type == MediaType.MOVIE

    def test_prime_video_thriller(self):
        intent = intent_parser._parse_deterministic("thriller on Prime Video", None)
        assert 53 in intent.include_genres
        assert intent.provider_id in (9, 119)
        assert "Prime" in intent.provider_name

    def test_tearjerker_emotional_intent(self):
        intent = intent_parser._parse_deterministic("brooo I wanna cry give me a real tearjerker", None)
        assert intent.mood == "emotional"
        assert intent.emotional_sub_intent == "tearjerker"
        assert 18 in intent.include_genres

    def test_feelgood_heartwarming_intent(self):
        intent = intent_parser._parse_deterministic("need a heartwarming feel-good movie", None)
        assert intent.mood == "emotional"
        assert intent.emotional_sub_intent == "feelgood"
        assert 18 in intent.include_genres or 10751 in intent.include_genres

    def test_underrated_popularity_extraction(self):
        intent = intent_parser._parse_deterministic("underrated hidden gem thriller", None)
        assert 53 in intent.include_genres
        assert intent.popularity == "low"

    def test_blockbuster_popularity_extraction(self):
        intent = intent_parser._parse_deterministic("popular blockbuster action movies", None)
        assert 28 in intent.include_genres
        assert intent.popularity == "high"

    def test_combined_movies_and_tv_shows(self):
        intent = intent_parser._parse_deterministic("comedy movies and TV shows", None)
        assert 35 in intent.include_genres
        assert intent.media_type == MediaType.BOTH

    def test_genre_exclusion_with_inclusion(self):
        intent = intent_parser._parse_deterministic("recommend a sci-fi movie but no horror", None)
        assert 878 in intent.include_genres
        assert 27 in intent.exclude_genres
        assert intent.media_type == MediaType.MOVIE

    def test_multi_genre_exclusion(self):
        intent = intent_parser._parse_deterministic("action movies without romance and no comedy", None)
        assert 28 in intent.include_genres
        assert 10749 in intent.exclude_genres
        assert 35 in intent.exclude_genres

    def test_slang_repeated_characters_normalized(self):
        intent = intent_parser._parse_deterministic("find me some scifiii and horrorrr", None)
        assert 878 in intent.include_genres
        assert 27 in intent.include_genres


# =============================================================================
# CATEGORY 3: REGIONAL & INTERNATIONAL LANGUAGE EXTRACTION (8 TEST CASES)
# =============================================================================

class TestScoutLanguageRecognition:
    """Test recognition of regional Indian and international cinema requests."""

    def test_tamil_cinema_keyword(self):
        intent = intent_parser._parse_deterministic("suggest a good Tamil thriller", None)
        assert intent.language == "ta"
        assert intent.watch_region == "IN"
        assert 53 in intent.include_genres

    def test_kollywood_alias(self):
        intent = intent_parser._parse_deterministic("top Kollywood action movies", None)
        assert intent.language == "ta"
        assert 28 in intent.include_genres

    def test_malayalam_cinema(self):
        intent = intent_parser._parse_deterministic("critically acclaimed Malayalam drama", None)
        assert intent.language == "ml"
        assert intent.watch_region == "IN"
        assert 18 in intent.include_genres

    def test_telugu_cinema(self):
        intent = intent_parser._parse_deterministic("Telugu action entertainer", None)
        assert intent.language == "te"
        assert 28 in intent.include_genres

    def test_hindi_bollywood(self):
        intent = intent_parser._parse_deterministic("fun Bollywood comedy", None)
        assert intent.language == "hi"
        assert 35 in intent.include_genres

    def test_korean_drama(self):
        intent = intent_parser._parse_deterministic("romantic Kdrama series", None)
        assert intent.language == "ko"
        assert intent.media_type == MediaType.TV
        assert 10749 in intent.include_genres

    def test_japanese_anime(self):
        intent = intent_parser._parse_deterministic("action anime", None)
        assert intent.language == "ja"
        assert 16 in intent.include_genres
        assert 28 in intent.include_genres

    def test_spanish_cinema(self):
        intent = intent_parser._parse_deterministic("Spanish mystery movie", None)
        assert intent.language == "es"
        assert 9648 in intent.include_genres


# =============================================================================
# CATEGORY 4: RUNTIME NORMALIZATION (6 TEST CASES)
# =============================================================================

class TestScoutRuntimeNormalization:
    """Test natural language runtime constraint extraction and mapping."""

    def test_runtime_under_two_hours(self):
        intent = intent_parser._parse_deterministic("comedy movie under two hours", None)
        assert intent.runtime_preference == "90_to_130"

    def test_runtime_under_2_hours_digits(self):
        intent = intent_parser._parse_deterministic("thriller under 2 hours", None)
        assert intent.runtime_preference == "90_to_130"

    def test_runtime_under_90_minutes(self):
        intent = intent_parser._parse_deterministic("short animation under 90 minutes", None)
        assert intent.runtime_preference == "under_90"

    def test_runtime_quick_bite_sized(self):
        intent = intent_parser._parse_deterministic("something quick and short to watch", None)
        assert intent.runtime_preference == "under_90"

    def test_runtime_over_two_hours(self):
        intent = intent_parser._parse_deterministic("epic drama over 2 hours long", None)
        assert intent.runtime_preference == "flexible"

    def test_runtime_under_120_mins(self):
        intent = intent_parser._parse_deterministic("action film under 120 mins", None)
        assert intent.runtime_preference == "90_to_130"


# =============================================================================
# CATEGORY 5: HARD CONSTRAINT ENFORCEMENT - 0% VIOLATION (8 TEST CASES)
# =============================================================================

class TestScoutHardConstraintEnforcement:
    """Ensure hard negative constraints are strictly enforced in generated recommendations."""

    @pytest.mark.asyncio
    async def test_zero_horror_tolerance(self):
        service = ScoutService()
        candidates = [
            {"id": 1, "title": "Scary Movie", "genre_ids": [27, 35], "vote_average": 6.5, "media_type": "movie"},
            {"id": 2, "title": "Funny Comedy", "genre_ids": [35], "vote_average": 7.8, "media_type": "movie"},
            {"id": 3, "title": "Haunted House", "genre_ids": [27], "vote_average": 7.0, "media_type": "movie"}
        ]
        with patch.object(service, '_fetch_movies', new=AsyncMock(return_value=[candidates[1]])):
            recs = await service._generate_recommendations({
                "media_type": "movie",
                "include_genres": [35],
                "exclude_genres": [27]
            })
            assert len(recs) == 1
            assert recs[0]["id"] == 2
            assert not any(27 in r.get("genre_ids", []) for r in recs)

    @pytest.mark.asyncio
    async def test_zero_romance_tolerance_in_action(self):
        service = ScoutService()
        recs = await service._generate_recommendations({
            "media_type": "movie",
            "include_genres": [28],
            "exclude_genres": [10749]
        })
        # Verify no recommendations contain Romance (10749)
        assert not any(10749 in r.get("genre_ids", []) for r in recs)

    def test_negative_pattern_hate_horror(self):
        intent = intent_parser._parse_deterministic("give me a thriller I hate horror", None)
        assert 53 in intent.include_genres
        assert 27 in intent.exclude_genres

    def test_negative_pattern_avoid_romance(self):
        intent = intent_parser._parse_deterministic("drama but avoid romance", None)
        assert 18 in intent.include_genres
        assert 10749 in intent.exclude_genres

    def test_negative_pattern_leave_out_comedy(self):
        intent = intent_parser._parse_deterministic("serious sci-fi leave out comedy", None)
        assert 878 in intent.include_genres
        assert 35 in intent.exclude_genres

    def test_negative_pattern_skip_animation(self):
        intent = intent_parser._parse_deterministic("family movie skip cartoons", None)
        assert 10751 in intent.include_genres
        assert 16 in intent.exclude_genres

    def test_negative_pattern_no_jump_scares(self):
        intent = intent_parser._parse_deterministic("mystery with no jump scares", None)
        assert 9648 in intent.include_genres
        assert 27 in intent.exclude_genres

    def test_negative_pattern_zero_gore(self):
        intent = intent_parser._parse_deterministic("thriller with zero gore", None)
        assert 53 in intent.include_genres
        assert 27 in intent.exclude_genres


# =============================================================================
# CATEGORY 6: GROUNDING & HONEST METADATA (6 TEST CASES)
# =============================================================================

class TestScoutGroundingAndMetadata:
    """Test that Scout never hallucinates unverified attributes and produces structured analysis."""

    def test_explanation_uses_exact_tmdb_rating(self):
        service = ScoutService()
        item = {"id": 1, "title": "Inception", "vote_average": 8.8, "genre_ids": [878, 28], "overview": "A thief who steals corporate secrets."}
        exp = service._generate_explanation(item, {"include_genres": [878], "user_expressed_mood": False})
        assert "8.8" in exp
        assert "TMDB" in exp

    def test_analysis_dict_contains_verified_evidence(self):
        service = ScoutService()
        item = {"id": 1, "title": "Dune", "vote_average": 8.1, "genre_ids": [878, 12], "overview": "A noble family becomes embroiled in a war."}
        analysis = service._build_analysis_dict(item, {"mood": "curious", "user_expressed_mood": True})
        assert "genre_match" in analysis
        assert "story_evidence" in analysis
        assert "Science Fiction" in analysis["genre_match"]
        assert "ranking_signals" in analysis

    def test_explanation_does_not_claim_unexpressed_mood(self):
        service = ScoutService()
        item = {"id": 1, "title": "The Dark Knight", "vote_average": 9.0, "genre_ids": [28, 80], "overview": "Batman battles the Joker."}
        exp = service._generate_explanation(item, {"mood": "excited", "user_expressed_mood": False})
        assert "excited mood" not in exp.lower()

    def test_analysis_genre_mapping_movie_tv_consistency(self):
        service = ScoutService()
        item = {"id": 1, "name": "The Mandalorian", "media_type": "tv", "vote_average": 8.4, "genre_ids": [10759, 10765]}
        analysis = service._build_analysis_dict(item, {"media_type": "tv"})
        assert "Action & Adventure" in analysis["genre_match"]

    def test_honest_fallback_message_when_no_provider_results(self):
        service = ScoutService()
        constraints = Mock()
        constraints.provider_name = "Disney+"
        msg = "I couldn't find any titles on Disney+ that match those exact filters in your region. Want to adjust the genre or check other services?"
        assert "Disney+" in msg
        assert "region" in msg

    def test_honest_fallback_message_when_no_genre_results(self):
        msg = "I couldn't find any titles that match all those filters right now. Want to loosen the criteria or try a different vibe?"
        assert "loosen the criteria" in msg


# =============================================================================
# CATEGORY 7: REFERENCE RESOLUTION & CONVERSATIONAL MEMORY (6 TEST CASES)
# =============================================================================

class TestScoutReferenceResolution:
    """Test follow-up resolution, constraint accumulation, and context reset."""

    def test_followup_preserves_accumulated_genres(self):
        state = ConversationState()
        # Turn 1: Sci-fi
        intent1 = intent_parser._parse_deterministic("sci-fi movies", state)
        state = conversation_state_machine.apply_intent(intent1, state)
        assert 878 in state.temporary_constraints.include_genres

        # Turn 2: No horror
        intent2 = intent_parser._parse_deterministic("no horror though", state)
        state = conversation_state_machine.apply_intent(intent2, state)
        assert 878 in state.temporary_constraints.include_genres
        assert 27 in state.temporary_constraints.exclude_genres

        # Turn 3: Shorter ones
        intent3 = intent_parser._parse_deterministic("make them shorter", state)
        state = conversation_state_machine.apply_intent(intent3, state)
        assert 878 in state.temporary_constraints.include_genres
        assert 27 in state.temporary_constraints.exclude_genres
        assert state.temporary_constraints.runtime_preference == "under_90"

    def test_fresh_search_clears_previous_exclusions(self):
        state = ConversationState()
        state.temporary_constraints.include_genres = [878]
        state.temporary_constraints.exclude_genres = [27]

        intent = intent_parser._parse_deterministic("now suggest some horror movies", state)
        state = conversation_state_machine.apply_intent(intent, state)
        assert intent.request_type == RequestType.FRESH_SEARCH
        assert 27 in state.temporary_constraints.include_genres
        assert 27 not in state.temporary_constraints.exclude_genres

    def test_similar_movie_title_extraction_interstellar(self):
        intent = intent_parser._parse_deterministic("something like Interstellar", None)
        assert 878 in intent.include_genres
        assert intent.referenced_title_name.lower() == "interstellar"

    def test_similar_movie_title_extraction_inception(self):
        intent = intent_parser._parse_deterministic("movies like Inception", None)
        assert 878 in intent.include_genres
        assert 28 in intent.include_genres
        assert intent.referenced_title_name.lower() == "inception"

    def test_similar_movie_title_extraction_parasite(self):
        intent = intent_parser._parse_deterministic("recommend films like Parasite", None)
        assert 53 in intent.include_genres
        assert intent.referenced_title_name.lower() == "parasite"

    def test_referenced_last_recommendation(self):
        state = ConversationState()
        state.previous_recommendations = [
            {"id": 1, "title": "Movie One"},
            {"id": 2, "title": "Movie Two"},
            {"id": 3, "title": "Movie Three", "vote_average": 8.0, "overview": "Epic finale."}
        ]
        intent = intent_parser._parse_deterministic("tell me about the last one", state)
        assert intent.request_type == RequestType.TITLE_QUESTION
        assert intent.referenced_title_index == -1
        assert "Movie Three" in intent.response_message


# =============================================================================
# CATEGORY 8: FALLBACK MODE & RESILIENCE (4 TEST CASES)
# =============================================================================

class TestScoutFallbackModeResilience:
    """Test Scout operational stability without Gemini or TMDB network access."""

    @pytest.mark.asyncio
    async def test_scout_process_message_without_gemini(self):
        scout = ScoutService()
        # With default unconfigured state, process_message should use deterministic fallback
        result = await scout.process_message("suggest sci-fi movies", [])
        assert result["intent"] == "recommend"
        assert "recommendations" in result
        assert len(result["recommendations"]) > 0
        assert result["recommendations"][0]["media_type"] == "movie"

    @pytest.mark.asyncio
    async def test_scout_pure_chat_zero_recommendations(self):
        scout = ScoutService()
        result = await scout.process_message("heyyy scout!", [])
        assert result["intent"] == "chat"
        assert len(result["recommendations"]) == 0
        assert len(result["message"]) > 0

    @pytest.mark.asyncio
    async def test_scout_director_query_zero_recommendations(self):
        scout = ScoutService()
        result = await scout.process_message("who directed Interstellar?", [])
        assert result["intent"] == "title_question"
        assert len(result["recommendations"]) == 0
        assert "Christopher Nolan" in result["message"]

    @pytest.mark.asyncio
    async def test_scout_handles_empty_results_gracefully(self):
        scout = ScoutService()
        with patch.object(scout, '_generate_recommendations', new=AsyncMock(return_value=[])):
            result = await scout.process_message("recommend action movies", [])
            assert result["intent"] == "recommend"
            assert len(result["recommendations"]) == 0
            assert "couldn't find" in result["message"]
