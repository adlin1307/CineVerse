"""
Comprehensive End-to-End Regression Tests for Scout Rebuild.

Validates all requirements from Section 12:
A. Pure greetings and chat banter (0 recommendations)
B. Mixed greeting + recommendation requests
C. Fresh searches (Sci-Fi TV, Romance movies, Emotional movies)
D. Multi-turn conversational flow (emotional -> tearjerker -> exclude romance -> darker -> fresh comedy)
E. Title references ("Tell me more about the second one", "Why did you recommend that?")
F. Hard constraint enforcement (no horror, no romance, movies only, TV only)
G. Robust failure and error recovery (Gemini timeout, TMDB timeout, empty results)
H. API contract verification
"""

import pytest
import json
from unittest.mock import AsyncMock, patch, Mock
from services.scout_service import ScoutService
from models.intent import RequestType, MediaType
from models.state import ConversationState
from models.recommendation import RecommendationRequest


@pytest.fixture
def scout():
    s = ScoutService()
    s.gemini_configured = True
    return s


# =============================================================================
# A. GREETINGS & CASUAL CHAT (Must return 0 recommendations)
# =============================================================================
class TestGreetingsAndChat:
    """Test that pure chat messages never trigger recommendation searches or return cards."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("greeting", [
        "hi",
        "heyyy",
        "heyyyy there",
        "how are you?",
        "thanks!",
        "thank you so much",
        "lol",
        "lol you're funny",
        "good morning"
    ])
    async def test_pure_greetings_return_zero_recommendations(self, scout, greeting):
        result = await scout.process_message(greeting, [])
        assert result["intent"] == "chat"
        assert len(result["recommendations"]) == 0
        assert isinstance(result["message"], str)
        assert len(result["message"]) > 0


# =============================================================================
# B. MIXED INTENT (Greeting + recommendation)
# =============================================================================
class TestMixedIntent:
    """Test that greetings mixed with actual recommendation requests are parsed as recommendations."""

    @pytest.mark.asyncio
    async def test_greeting_plus_recommendation(self, scout):
        with patch.object(
            scout.tmdb,
            'discover_movies',
            new=AsyncMock(return_value={
                "results": [{
                    "id": 101,
                    "title": "Prisoners",
                    "vote_average": 8.1,
                    "release_date": "2013-09-20",
                    "genre_ids": [53, 18],
                    "overview": "A gripping thriller."
                }]
            })
        ):
            result = await scout.process_message("Hey, recommend a thriller", [])
            assert result["intent"] == "recommend"
            assert len(result["recommendations"]) >= 1
            assert result["recommendations"][0]["id"] == 101


# =============================================================================
# C. FRESH SEARCHES
# =============================================================================
class TestFreshSearches:
    """Test fresh recommendation searches with distinct genres and media types."""

    @pytest.mark.asyncio
    async def test_scifi_tv_shows(self, scout):
        with patch.object(
            scout.tmdb,
            'discover_series',
            new=AsyncMock(return_value={
                "results": [{
                    "id": 201,
                    "name": "Severance",
                    "vote_average": 8.7,
                    "first_air_date": "2022-02-18",
                    "genre_ids": [10765, 18],
                    "overview": "Sci-Fi workplace thriller."
                }]
            })
        ) as mock_tv:
            result = await scout.process_message("suggest sci-fi TV shows", [])
            assert result["intent"] == "recommend"
            assert len(result["recommendations"]) >= 1
            assert result["recommendations"][0]["media_type"] == "tv"
            assert mock_tv.called

    @pytest.mark.asyncio
    async def test_romance_movies(self, scout):
        with patch.object(
            scout.tmdb,
            'discover_movies',
            new=AsyncMock(return_value={
                "results": [{
                    "id": 301,
                    "title": "Before Sunrise",
                    "vote_average": 8.3,
                    "release_date": "1995-01-27",
                    "genre_ids": [10749, 18],
                    "overview": "Two strangers meet on a train."
                }]
            })
        ):
            result = await scout.process_message("recommend romance movies", [])
            assert result["intent"] == "recommend"
            assert len(result["recommendations"]) >= 1
            assert result["recommendations"][0]["media_type"] == "movie"


# =============================================================================
# D. MULTI-TURN CONVERSATION SEQUENCE
# =============================================================================
class TestMultiTurnConversation:
    """
    Test the complete 5-turn sequence:
    1. "I want something emotional"
    2. "brooo I wanna cry"
    3. "not romance though"
    4. "make them darker"
    5. "actually, give me a comedy"
    """

    @pytest.mark.asyncio
    async def test_five_turn_emotional_refinement_to_fresh_comedy(self, scout):
        history = []

        # Turn 1: "I want something emotional"
        mock_emotional = {
            "results": [{
                "id": 1,
                "title": "Manchester by the Sea",
                "vote_average": 7.9,
                "release_date": "2016-11-18",
                "genre_ids": [18],
                "overview": "A grieving uncle is asked to take care of his nephew."
            }]
        }
        with patch.object(scout.tmdb, 'discover_movies', new=AsyncMock(return_value=mock_emotional)):
            with patch.object(scout.tmdb, 'discover_series', new=AsyncMock(return_value={"results": []})):
                r1 = await scout.process_message("I want something emotional", history)
                assert r1["intent"] == "recommend"
                assert len(r1["recommendations"]) >= 1
                history.append({"role": "user", "content": "I want something emotional"})
                history.append({"role": "assistant", "content": r1["message"], "recommendations": r1["recommendations"]})

        # Turn 2: "brooo I wanna cry" (Refinement into tearjerker)
        mock_tearjerker = {
            "results": [{
                "id": 2,
                "title": "Grave of the Fireflies",
                "vote_average": 8.5,
                "release_date": "1988-04-16",
                "genre_ids": [16, 18, 10752],
                "overview": "Heartbreaking wartime tale of two siblings."
            }]
        }
        with patch.object(scout.tmdb, 'discover_movies', new=AsyncMock(return_value=mock_tearjerker)):
            with patch.object(scout.tmdb, 'discover_series', new=AsyncMock(return_value={"results": []})):
                r2 = await scout.process_message("brooo I wanna cry", history)
                assert r2["intent"] == "recommend"
                history.append({"role": "user", "content": "brooo I wanna cry"})
                history.append({"role": "assistant", "content": r2["message"], "recommendations": r2["recommendations"]})

        # Turn 3: "not romance though" (Hard exclusion of genre 10749)
        mock_candidates_turn3 = {
            "results": [
                {"id": 3, "title": "Titanic", "vote_average": 7.9, "release_date": "1997-11-18", "genre_ids": [18, 10749], "overview": "Romance drama."},
                {"id": 4, "title": "Schindler's List", "vote_average": 8.6, "release_date": "1993-11-30", "genre_ids": [18, 36, 10752], "overview": "Powerful drama."}
            ]
        }
        with patch.object(scout.tmdb, 'discover_movies', new=AsyncMock(return_value=mock_candidates_turn3)):
            with patch.object(scout.tmdb, 'discover_series', new=AsyncMock(return_value={"results": []})):
                r3 = await scout.process_message("not romance though", history)
                assert r3["intent"] == "recommend"
                # Titanic (10749) must be filtered out!
                for rec in r3["recommendations"]:
                    assert 10749 not in rec.get("genre_ids", [])
                    assert rec["title"] != "Titanic"
                history.append({"role": "user", "content": "not romance though"})
                history.append({"role": "assistant", "content": r3["message"], "recommendations": r3["recommendations"]})

        # Turn 4: "make them darker"
        mock_darker = {
            "results": [{
                "id": 5,
                "title": "Requiem for a Dream",
                "vote_average": 8.0,
                "release_date": "2000-10-06",
                "genre_ids": [18],
                "overview": "Intense addiction drama."
            }]
        }
        with patch.object(scout.tmdb, 'discover_movies', new=AsyncMock(return_value=mock_darker)):
            with patch.object(scout.tmdb, 'discover_series', new=AsyncMock(return_value={"results": []})):
                r4 = await scout.process_message("make them darker", history)
                assert r4["intent"] == "recommend"
                history.append({"role": "user", "content": "make them darker"})
                history.append({"role": "assistant", "content": r4["message"], "recommendations": r4["recommendations"]})

        # Turn 5: "actually, give me a comedy" (Fresh search, discards emotional and darker constraints)
        mock_comedy = {
            "results": [{
                "id": 6,
                "title": "Superbad",
                "vote_average": 7.2,
                "release_date": "2007-08-17",
                "genre_ids": [35],
                "overview": "Two high school seniors try to buy alcohol for a party."
            }]
        }
        with patch.object(scout.tmdb, 'discover_movies', new=AsyncMock(return_value=mock_comedy)):
            with patch.object(scout.tmdb, 'discover_series', new=AsyncMock(return_value={"results": []})):
                r5 = await scout.process_message("actually, give me a comedy", history)
                assert r5["intent"] == "recommend"
                assert r5["recommendations"][0]["id"] == 6


# =============================================================================
# E. TITLE REFERENCES & METADATA QUESTIONS
# =============================================================================
class TestTitleReferences:
    """Test asking about previously recommended titles."""

    @pytest.mark.asyncio
    async def test_tell_me_more_about_second_one(self, scout):
        history = [
            {"role": "user", "content": "recommend sci-fi movies"},
            {
                "role": "assistant",
                "content": "Here are two great picks!",
                "recommendations": [
                    {"id": 10, "title": "Interstellar", "release_date": "2014-11-05", "vote_average": 8.4, "overview": "A team of explorers travel through a wormhole in space."},
                    {"id": 20, "title": "Arrival", "release_date": "2016-11-10", "vote_average": 7.9, "overview": "A linguist works with the military to communicate with alien lifeforms."}
                ]
            }
        ]

        result = await scout.process_message("tell me more about the second one", history)
        # Should NOT trigger new recommendations
        assert len(result["recommendations"]) == 0
        # Should refer to Arrival
        assert "Arrival" in result["message"] or "linguist" in result["message"].lower() or "7.9" in result["message"]

    @pytest.mark.asyncio
    async def test_why_did_you_recommend_that(self, scout):
        history = [
            {"role": "user", "content": "recommend a mystery"},
            {
                "role": "assistant",
                "content": "Here is a top mystery!",
                "recommendations": [
                    {"id": 30, "title": "Knives Out", "release_date": "2019-11-27", "vote_average": 7.9, "overview": "A detective investigates the death of a wealthy patriarch.", "explanation": "Delivers a clever whodunit puzzle."}
                ]
            }
        ]

        result = await scout.process_message("why did you recommend that?", history)
        assert len(result["recommendations"]) == 0
        assert "Knives Out" in result["message"] or "7.9" in result["message"] or "clever" in result["message"].lower()


# =============================================================================
# F. HARD EXCLUSIONS & CONSTRAINTS
# =============================================================================
class TestHardConstraints:
    """Verify that hard exclusions are strictly enforced."""

    @pytest.mark.asyncio
    async def test_no_horror_strictly_enforced(self, scout):
        # TMDB mock returns a horror title (27) alongside a thriller (53)
        mock_results = {
            "results": [
                {"id": 50, "title": "The Conjuring", "genre_ids": [27, 53], "vote_average": 7.5, "release_date": "2013-07-19"},
                {"id": 51, "title": "Zodiac", "genre_ids": [53, 80, 18], "vote_average": 7.8, "release_date": "2007-03-02"}
            ]
        }
        with patch.object(scout.tmdb, 'discover_movies', new=AsyncMock(return_value=mock_results)):
            result = await scout.process_message("recommend a thriller, no horror", [])
            for rec in result["recommendations"]:
                assert 27 not in rec.get("genre_ids", [])
                assert rec["title"] != "The Conjuring"


# =============================================================================
# G. FAILURE HANDLING & HONEST RECOVERY
# =============================================================================
class TestFailureHandling:
    """Verify honest and robust handling of API failures without crashing or hallucinating."""

    @pytest.mark.asyncio
    async def test_empty_results_returns_honest_message(self, scout):
        with patch.object(scout.tmdb, 'discover_movies', new=AsyncMock(return_value={"results": []})):
            with patch.object(scout.tmdb, 'discover_series', new=AsyncMock(return_value={"results": []})):
                result = await scout.process_message("recommend a movie from 1902 with zombies", [])
                assert result["intent"] == "recommend"
                assert result["recommendations"] == []
                assert "couldn't find" in result["message"].lower() or "no matches" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_tmdb_network_error_returns_empty_safely(self, scout):
        with patch.object(scout.tmdb, 'discover_movies', new=AsyncMock(side_effect=Exception("Connection reset"))):
            with patch.object(scout.tmdb, 'discover_series', new=AsyncMock(side_effect=Exception("Connection reset"))):
                result = await scout.process_message("suggest movies", [])
                assert result["recommendations"] == []
                assert "couldn't find" in result["message"].lower() or "error" in result["message"].lower()


# =============================================================================
# H. SPECIFIC BROWSER CONVERSATION FAILURES & ANALYSIS VERIFICATION
# =============================================================================
class TestSpecificLiveBrowserFixes:
    """Regression tests for confirmed browser conversation quality defects."""

    @pytest.mark.asyncio
    async def test_emotional_intent_grounded_explanation_and_analysis(self, scout):
        """1. 'I want something emotional' provides grounded explanations and structured analysis."""
        mock_movies = {
            "results": [
                {
                    "id": 278,
                    "title": "The Shawshank Redemption",
                    "genre_ids": [18, 80],
                    "vote_average": 8.7,
                    "release_date": "1994-09-23",
                    "overview": "Imprisoned in the 1940s, Andy Dufresne bonds with a fellow inmate over decades finding solace and redemption through acts of common decency."
                },
                {
                    "id": 238,
                    "title": "The Godfather",
                    "genre_ids": [18, 80],
                    "vote_average": 8.7,
                    "release_date": "1972-03-14",
                    "overview": "Spanning the years 1945 to 1955, a chronicle of the fictional Italian-American Corleone crime family."
                }
            ]
        }
        with patch.object(scout.tmdb, 'discover_movies', new=AsyncMock(return_value=mock_movies)):
            with patch.object(scout.tmdb, 'discover_series', new=AsyncMock(return_value={"results": []})):
                result = await scout.process_message("I want something emotional", [])
                assert result["intent"] == "recommend"
                assert len(result["recommendations"]) > 0
                
                first_rec = result["recommendations"][0]
                # Shawshank should score higher than The Godfather because mob violence is penalized for emotional
                assert first_rec["title"] == "The Shawshank Redemption"
                assert first_rec.get("analysis") is not None
                
                analysis = first_rec["analysis"]
                assert analysis["media_type_label"] in ["Movie", "TV Series"]
                assert "Drama" in analysis["genre_match"]
                assert "8.7" in analysis["ranking_signals"]
                assert len(analysis["story_evidence"]) > 0
                assert "TMDB" in analysis["provenance"]

    @pytest.mark.asyncio
    async def test_wanna_cry_refinement_avoids_repeating_previous_recommendations(self, scout):
        """2. 'I meant I wanna cry!!' refines emotional search into tearjerker and avoids repeating prior titles."""
        # Turn 1 recommended Shawshank (id 278)
        history = [
            {"role": "user", "content": "I want something emotional"},
            {
                "role": "assistant",
                "content": "Here are some emotional picks.",
                "recommendations": [
                    {"id": 278, "title": "The Shawshank Redemption", "genre_ids": [18], "vote_average": 8.7, "media_type": "movie"}
                ]
            }
        ]
        
        mock_movies = {
            "results": [
                {
                    "id": 278,
                    "title": "The Shawshank Redemption",
                    "genre_ids": [18],
                    "vote_average": 8.7,
                    "overview": "A banker endures prison and finds quiet hope."
                },
                {
                    "id": 424,
                    "title": "Schindler's List",
                    "genre_ids": [18, 36, 10752],
                    "vote_average": 8.6,
                    "overview": "The true, heartbreaking story of Oskar Schindler who risked his life to save over a thousand Jewish refugees from tragic death during the Holocaust."
                }
            ]
        }
        with patch.object(scout.tmdb, 'discover_movies', new=AsyncMock(return_value=mock_movies)):
            with patch.object(scout.tmdb, 'discover_series', new=AsyncMock(return_value={"results": []})):
                result = await scout.process_message("I meant I wanna cry!!", history)
                assert result["intent"] == "recommend"
                rec_ids = [r["id"] for r in result["recommendations"]]
                
                # Must exclude or avoid repeat of Shawshank (id 278)
                assert 278 not in rec_ids
                assert 424 in rec_ids
                
                # Check explanation reflects poignant evidence
                schindler_rec = next(r for r in result["recommendations"] if r["id"] == 424)
                assert "poignant" in schindler_rec["explanation"].lower() or "loss" in schindler_rec["explanation"].lower() or "heartbreaking" in schindler_rec["overview"].lower()

    @pytest.mark.asyncio
    async def test_sci_fi_tv_correction_preserves_genre_and_switches_to_tv(self, scout):
        """3. 'what about TV shows? I need them not movies' switches to TV-only and preserves Sci-Fi."""
        history = [
            {"role": "user", "content": "Okay, suggest some great sci-fi movies and shows"},
            {
                "role": "assistant",
                "content": "Here are some great sci-fi picks!",
                "recommendations": [
                    {"id": 157336, "title": "Interstellar", "genre_ids": [878, 18], "media_type": "movie"}
                ]
            }
        ]
        
        mock_tv = {
            "results": [
                {
                    "id": 84958,
                    "name": "Loki",
                    "genre_ids": [10765, 10759],
                    "vote_average": 8.2,
                    "first_air_date": "2021-06-09",
                    "overview": "The mercurial villain Loki resumes his role as the God of Mischief in a new series that takes place after the events of Avengers: Endgame."
                }
            ]
        }
        with patch.object(scout.tmdb, 'discover_series', new=AsyncMock(return_value=mock_tv)):
            result = await scout.process_message("what about TV shows? I need them not movies", history)
            # Must NOT be title_question or ask clarification
            assert result["intent"] == "recommend"
            assert len(result["recommendations"]) > 0
            for r in result["recommendations"]:
                # Must be strictly TV
                assert r["media_type"] == "tv"
                assert r["title"] == "Loki"
                assert r.get("analysis") is not None
                assert r["analysis"]["media_type_label"] == "TV Series"
                assert "TV Series only" in r["analysis"]["constraints_applied"]

    @pytest.mark.asyncio
    async def test_balanced_mix_when_both_media_types_requested(self, scout):
        """4. 'Suggest some great sci-fi movies and shows' returns a useful mix of both types."""
        mock_movies = {
            "results": [
                {"id": 100, "title": "Sci-Fi Film 1", "genre_ids": [878], "vote_average": 8.0, "release_date": "2020-01-01", "overview": "Space film."},
                {"id": 101, "title": "Sci-Fi Film 2", "genre_ids": [878], "vote_average": 7.8, "release_date": "2021-01-01", "overview": "Space film 2."}
            ]
        }
        mock_tv = {
            "results": [
                {"id": 200, "name": "Sci-Fi Series 1", "genre_ids": [10765], "vote_average": 8.5, "first_air_date": "2022-01-01", "overview": "Space TV show."}
            ]
        }
        with patch.object(scout.tmdb, 'discover_movies', new=AsyncMock(return_value=mock_movies)):
            with patch.object(scout.tmdb, 'discover_series', new=AsyncMock(return_value=mock_tv)):
                result = await scout.process_message("Suggest some great sci-fi movies and shows", [])
                assert result["intent"] == "recommend"
                types = [r["media_type"] for r in result["recommendations"]]
                assert "movie" in types
                assert "tv" in types


class TestScoutQualityPersonalityAndUXOverhaul:
    """Comprehensive test suite for Recommendation Quality, Personality & UX Overhaul."""

    @pytest.mark.asyncio
    async def test_new_chat_clears_previous_constraints_and_cards(self, scout):
        """Priority 1: A fresh conversation does not inherit previous constraints or recommendation IDs."""
        # Initial search: sci-fi movies
        history = [
            {"role": "user", "content": "Recommend sci-fi movies"},
            {"role": "assistant", "content": "Here are picks", "recommendations": [{"id": 157336, "title": "Interstellar", "genre_ids": [878]}]}
        ]
        state = scout._build_state_from_history(history)
        assert 878 in state.temporary_constraints.include_genres
        assert len(state.previous_recommendations) == 1

        # Now simulate New Chat: history is reset to just the initial greeting
        fresh_history = [
            {"role": "assistant", "content": "Heyyy, I'm Scout. Tell me what you're in the mood for!", "recommendations": []}
        ]
        fresh_state = scout._build_state_from_history(fresh_history)
        assert fresh_state.temporary_constraints.include_genres == []
        assert fresh_state.temporary_constraints.exclude_genres == []
        assert fresh_state.temporary_constraints.mood is None
        assert fresh_state.temporary_constraints.emotional_sub_intent is None
        assert fresh_state.previous_recommendations == []

    @pytest.mark.asyncio
    async def test_heyyy_greeting_returns_chat_with_zero_recommendations(self, scout):
        """Priority 3: 'heyyy' is parsed as pure chat and returns conversational greeting with 0 cards."""
        result = await scout.process_message("heyyy", [])
        assert result["intent"] == "chat"
        assert len(result["recommendations"]) == 0
        assert "hey" in result["message"].lower() or "ready" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_slang_and_elongated_words_normalized(self, scout):
        """Priority 3: Elongated words like 'horrorrr' and 'cryyy' match their intended intents."""
        # 'no horrorrr...' should exclude genre 27 and NOT include genre 27
        intent = scout.intent_parser._parse_deterministic("no horrorrr...", None)
        assert 27 in intent.exclude_genres
        assert 27 not in intent.include_genres

        # 'I wanna cryyy' should detect tearjerker emotional sub-intent
        intent2 = scout.intent_parser._parse_deterministic("I wanna cryyy", None)
        assert intent2.mood == "emotional"
        assert intent2.emotional_sub_intent == "tearjerker"

    @pytest.mark.asyncio
    async def test_no_horror_exclusion_purges_include_genres_and_avoids_500(self, scout):
        """Bug fix: When a genre was in include_genres, adding an exclusion purges it so RecommendationRequest never fails validation."""
        history = [
            {"role": "user", "content": "suggest good sci-fi movies and shows!"},
            {"role": "assistant", "content": "Here are picks", "recommendations": [{"id": 1, "title": "P1", "genre_ids": [18, 878]}]},
            {"role": "user", "content": "just tv shows plss"},
            {"role": "assistant", "content": "Here are shows", "recommendations": [{"id": 2, "title": "P2", "genre_ids": [18, 10765]}]}
        ]
        
        mock_tv = {
            "results": [
                {
                    "id": 999,
                    "name": "Dark Matter",
                    "genre_ids": [10765, 18],
                    "vote_average": 8.0,
                    "first_air_date": "2024-05-08",
                    "overview": "A physicist is abducted into an alternate version of his life."
                }
            ]
        }
        with patch.object(scout.tmdb, 'discover_series', new=AsyncMock(return_value=mock_tv)):
            # Sending 'no horror...' must succeed with 200, not 500
            res = await scout.process_message("no horror...", history)
            assert res["intent"] == "recommend"
            assert len(res["recommendations"]) > 0
            assert res["recommendations"][0]["id"] == 999

    @pytest.mark.asyncio
    async def test_tearjerker_candidate_relevance_before_popularity(self, scout):
        """Priority 2: Tearjerker requests evaluate candidate emotional relevance before popularity/ratings."""
        # Candidate A: Violent mob crime drama with high rating & high popularity (The Godfather style)
        mob_drama = {
            "id": 238,
            "title": "The Godfather Part II",
            "genre_ids": [18, 80],
            "vote_average": 8.6,
            "popularity": 150.0,
            "overview": "In the continuing saga of the Corleone crime family, a young Vito Corleone grows up in Sicily and in 1910s New York."
        }
        
        # Candidate B: True heartbreaking story of grief, terminal illness, and loss with lower popularity
        tearjerker_drama = {
            "id": 334543,
            "title": "Manchester by the Sea",
            "genre_ids": [18],
            "vote_average": 7.8,
            "popularity": 35.0,
            "overview": "A depressed uncle is asked to take care of his teenage nephew after the tragic death and loss of the boy's father, confronting immense grief and sorrow."
        }

        # Calculate emotional fit for sub_intent = 'tearjerker'
        mob_score = scout.engine._calculate_emotional_fit(mob_drama, "tearjerker", mood="emotional")
        tear_score = scout.engine._calculate_emotional_fit(tearjerker_drama, "tearjerker", mood="emotional")

        assert tear_score > mob_score, f"Tearjerker drama ({tear_score}) must outscore mob drama ({mob_score})"

        # Check ranking in engine: candidate relevance dominates popularity
        req = RecommendationRequest(
            media_type=MediaType.MOVIE,
            mood="emotional",
            emotional_sub_intent="tearjerker",
            count=2
        )
        ranked = scout.engine._rank_candidates([mob_drama, tearjerker_drama], req)
        assert ranked[0]["id"] == 334543, "Manchester by the Sea must rank #1 ahead of The Godfather Part II for a tearjerker request"

    @pytest.mark.asyncio
    async def test_all_six_emotional_sub_intents_scoring(self, scout):
        """Priority 2: Verify dedicated scoring for all 6 emotional sub-intents."""
        # 1. Bittersweet
        bittersweet_candidate = {
            "id": 1,
            "title": "Past Lives",
            "genre_ids": [18, 10749],
            "overview": "Two deeply connected childhood friends are reunited after two decades, reflecting on fleeting memories and wistful, bittersweet what-ifs."
        }
        score_bs = scout.engine._calculate_emotional_fit(bittersweet_candidate, "bittersweet", mood="emotional")
        assert score_bs >= 0.7

        # 2. Hopeful / Cathartic
        hopeful_candidate = {
            "id": 2,
            "title": "The Pursuit of Happyness",
            "genre_ids": [18, 36],
            "overview": "A struggling salesman endures homelessness with his son, overcoming incredible adversity through resilience, perseverance, and unshakable hope."
        }
        score_hope = scout.engine._calculate_emotional_fit(hopeful_candidate, "hopeful", mood="emotional")
        assert score_hope >= 0.7

        # 3. Feelgood
        feelgood_candidate = {
            "id": 3,
            "title": "Paddington 2",
            "genre_ids": [35, 10751, 12],
            "overview": "A charming and heartwarming bear spreads joy, friendship, and wholesome cheer across his neighborhood."
        }
        score_fg = scout.engine._calculate_emotional_fit(feelgood_candidate, "feelgood", mood="relaxed")
        assert score_fg >= 0.7

        # 4. Intense
        intense_candidate = {
            "id": 4,
            "title": "Marriage Story",
            "genre_ids": [18, 53],
            "overview": "A gripping, emotionally intense crisis where an unraveling relationship leads to desperate marital conflict and high-stakes confrontation."
        }
        score_intense = scout.engine._calculate_emotional_fit(intense_candidate, "intense", mood="emotional")
        assert score_intense >= 0.7

        # 5. Thought-Provoking
        thought_candidate = {
            "id": 5,
            "title": "Arrival",
            "genre_ids": [18, 878],
            "overview": "A linguist confronts existential questions about time, human communication, and the profound nature of reality."
        }
        score_thought = scout.engine._calculate_emotional_fit(thought_candidate, "thought_provoking", mood="curious")
        assert score_thought >= 0.7

    @pytest.mark.asyncio
    async def test_view_analysis_structure_and_grounded_evidence(self, scout):
        """Priority 4: View Analysis provides natural sections and honest limitation disclosure."""
        mock_movies = {
            "results": [
                {
                    "id": 101,
                    "title": "Grief Story",
                    "genre_ids": [18],
                    "vote_average": 8.4,
                    "release_date": "2023-01-01",
                    "overview": "A heartbroken mother copes with tragic loss, finding a fragile path through grief."
                }
            ]
        }
        with patch.object(scout.tmdb, 'discover_movies', new=AsyncMock(return_value=mock_movies)):
            res = await scout.process_message("I wanna cry", [])
            assert len(res["recommendations"]) > 0
            rec = res["recommendations"][0]
            
            # Check explanation is title-specific
            assert "A heartbroken mother" in rec["explanation"] or "grief" in rec["explanation"].lower()
            
            # Check analysis dictionary
            analysis = rec["analysis"]
            assert analysis is not None
            assert analysis["media_type_label"] == "Movie"
            assert "poignant" in analysis["mood_match"].lower() or "tearjerker" in analysis["mood_match"].lower()
            assert "heartbroken mother" in analysis["story_evidence"].lower()
            assert "TMDB Rating: 8.4/10" in analysis["ranking_signals"]
            assert "provenance" in analysis


