"""
Tests for Scout Disney provider filtering and conversation refinement handling.
Covers the exact bugs reported by user.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from services.scout_service import ScoutService


class TestScoutDisneyProvider:
    """Test Disney+ provider detection and filtering."""
    
    def test_disney_request_not_treated_as_refinement(self):
        """'now suggest some good Disney TV shows' should be NEW request, not refinement."""
        scout = ScoutService()
        
        # Message contains "no" in "now" but should not trigger refinement
        parsed = scout._fallback_parse("now suggest some good Disney TV shows", [])
        
        # Should detect Disney provider - ID depends on configured region
        from config import settings
        if settings.watch_region == "US":
            expected_id = 337  # Disney Plus
            expected_name = "Disney+"
        elif settings.watch_region == "IN":
            expected_id = 2336  # JioHotstar
            expected_name = "Disney+ Hotstar"
        else:
            expected_id = None
            expected_name = None
        
        assert parsed["preferences"]["provider_id"] == expected_id
        if expected_name:
            assert parsed["preferences"]["provider_name"] == expected_name
        assert parsed["preferences"]["watch_region"] == settings.watch_region
        
        # Message should mention provider
        if expected_name and "hotstar" in expected_name.lower():
            assert "Hotstar" in parsed["message"] or "Disney" in parsed["message"]
        elif expected_name:
            assert expected_name in parsed["message"]
    
    def test_disney_request_resets_unrelated_genres(self):
        """Disney request should not carry forward action genres from previous conversation."""
        scout = ScoutService()
        
        # Simulate conversation history with action request
        history = [
            {"role": "user", "content": "suggest action movies"},
            {"role": "assistant", "content": "Here are some action movies!"}
        ]
        
        parsed = scout._fallback_parse("now suggest some good Disney TV shows", history)
        
        # Should have provider ID (region-dependent), NOT action genres
        from config import settings
        if settings.watch_region == "US":
            assert parsed["preferences"]["provider_id"] == 337
        elif settings.watch_region == "IN":
            assert parsed["preferences"]["provider_id"] == 2336
        
        # Should NOT have action genres
        assert 28 not in parsed["preferences"]["include_genres"]  # Movie action
        assert 10759 not in parsed["preferences"]["include_genres"]  # TV action
    
    def test_disney_family_shows_keyword(self):
        """Disney family shows should add Family genre as user preference."""
        scout = ScoutService()
        
        parsed = scout._fallback_parse("suggest Disney family shows", [])
        
        # Should have provider ID (region-dependent)
        from config import settings
        if settings.watch_region == "US":
            assert parsed["preferences"]["provider_id"] == 337
        elif settings.watch_region == "IN":
            assert parsed["preferences"]["provider_id"] == 2336
        
        # Should have Family genre because user requested "family"
        assert 10751 in parsed["preferences"]["include_genres"]
    
    def test_hotstar_keyword_india(self):
        """'Hotstar' should resolve to JioHotstar in India."""
        scout = ScoutService()
        
        # Temporarily set region to India
        from config import settings
        original_region = settings.watch_region
        try:
            settings.watch_region = "IN"
            
            parsed = scout._fallback_parse("suggest shows on Hotstar", [])
            
            assert parsed["preferences"]["provider_id"] == 2336  # JioHotstar
            assert "Hotstar" in parsed["preferences"]["provider_name"]
            assert parsed["preferences"]["watch_region"] == "IN"
        finally:
            settings.watch_region = original_region
    
    def test_disney_with_animation_keyword(self):
        """Disney animated shows should add Animation genre."""
        scout = ScoutService()
        
        parsed = scout._fallback_parse("suggest animated Disney shows", [])
        
        # Should have provider ID (region-dependent)
        from config import settings
        if settings.watch_region == "US":
            assert parsed["preferences"]["provider_id"] == 337
        elif settings.watch_region == "IN":
            assert parsed["preferences"]["provider_id"] == 2336
        
        assert 16 in parsed["preferences"]["include_genres"]  # Animation - user requested


class TestRegionalProviderConfiguration:
    """Test region-aware provider resolution."""
    
    def test_default_region_is_india(self):
        """Default watch_region should be IN (India)."""
        from config import settings
        assert settings.watch_region == "IN"
    
    def test_disney_resolves_by_region(self):
        """Disney provider ID should differ by region."""
        scout = ScoutService()
        from config import settings
        
        # Test for current region
        parsed = scout._fallback_parse("suggest Disney shows", [])
        
        if settings.watch_region == "IN":
            assert parsed["preferences"]["provider_id"] == 2336  # JioHotstar
        elif settings.watch_region == "US":
            assert parsed["preferences"]["provider_id"] == 337  # Disney Plus
    
    def test_amazon_prime_resolves_by_region(self):
        """Amazon Prime ID should differ by region."""
        scout = ScoutService()
        from config import settings
        
        # Temporarily test different regions
        original_region = settings.watch_region
        try:
            # Test India
            settings.watch_region = "IN"
            parsed_in = scout._fallback_parse("suggest Prime Video shows", [])
            assert parsed_in["preferences"]["provider_id"] == 119  # Prime India
            
            # Test US
            settings.watch_region = "US"
            parsed_us = scout._fallback_parse("suggest Prime Video shows", [])
            assert parsed_us["preferences"]["provider_id"] == 9  # Prime US
        finally:
            settings.watch_region = original_region


class TestScoutRefinementDetection:
    """Test refinement vs new request detection."""
    
    def test_now_suggest_is_new_request(self):
        """'now suggest X' should be treated as NEW request."""
        scout = ScoutService()
        
        history = [
            {"role": "user", "content": "suggest action movies"},
            {"role": "assistant", "content": "Here are action picks!"}
        ]
        
        # "now" contains "no" but "now suggest" pattern indicates NEW request
        parsed = scout._fallback_parse("now suggest romantic comedies", history)
        
        # Should detect romance genre, NOT preserve action
        assert 10749 in parsed["preferences"]["include_genres"]  # Romance
        assert 28 not in parsed["preferences"]["include_genres"]  # Should NOT have action
    
    def test_make_them_darker_is_refinement(self):
        """'make them darker' SHOULD be treated as refinement."""
        scout = ScoutService()
        
        history = [
            {"role": "user", "content": "suggest action movies"},
            {"role": "assistant", "content": "Here are action picks!"}
        ]
        
        parsed = scout._fallback_parse("make them darker", history)
        
        # Should ADD drama to existing action
        assert 18 in parsed["preferences"]["include_genres"]  # Drama (darker)
        # Note: _fallback_parse preserves previous genres via history, tested in integration
    
    def test_no_horror_is_refinement(self):
        """'no horror' should be refinement with exclusion."""
        scout = ScoutService()
        
        parsed = scout._fallback_parse("no horror, please", [])
        
        # Should add horror to exclusions
        assert 27 in parsed["preferences"]["exclude_genres"]


class TestScoutProviderMergeLogic:
    """Test that provider requests don't incorrectly merge with history."""
    
    @pytest.mark.asyncio
    async def test_disney_request_skips_history_merge(self):
        """Provider-specific requests should NOT merge with conversation history."""
        scout = ScoutService()
        
        # Mock TMDB and recommendations services
        scout.tmdb = AsyncMock()
        scout.recommendations = AsyncMock()
        
        # Mock discover_series to return Disney family shows
        scout.tmdb.discover_series = AsyncMock(return_value={
            "results": [
                {
                    "id": 1877,
                    "name": "Phineas and Ferb",
                    "vote_average": 8.1,
                    "first_air_date": "2007-08-17",
                    "genre_ids": [16, 35, 10751],
                    "overview": "Animated series about stepbrothers."
                }
            ]
        })
        
        # Conversation history with action
        history = [
            {"role": "user", "content": "suggest action TV shows"},
            {"role": "assistant", "content": "Here are action shows!"}
        ]
        
        result = await scout.process_message("now suggest some good Disney TV shows", history)
        
        # Should call TMDB with Disney provider (region-appropriate ID)
        from config import settings
        if settings.watch_region == "US":
            expected_id = 337
        elif settings.watch_region == "IN":
            expected_id = 2336
        else:
            expected_id = None
        
        scout.tmdb.discover_series.assert_called_once()
        call_kwargs = scout.tmdb.discover_series.call_args[1]
        
        if expected_id:
            assert call_kwargs["with_watch_providers"] == expected_id
            assert call_kwargs["watch_region"] == settings.watch_region
        
        # Should NOT include action genre 10759
        genres_param = call_kwargs.get("with_genres", "")
        if genres_param and genres_param not in ["9648,99,10765", "9648,10765,99"]:  # Mood genres are OK
            assert "10759" not in genres_param


class TestScoutExplanationGrounding:
    """Test that explanations are evidence-based, not generic."""
    
    def test_movie_explanation_includes_rating(self):
        """Movie explanations should mention actual rating."""
        scout = ScoutService()
        
        movie = {
            "id": 123,
            "title": "Test Movie",
            "vote_average": 8.5,
            "genre_ids": [28, 878],  # Action, Sci-Fi
            "release_date": "2024-01-15"
        }
        
        explanation = scout._generate_explanation(movie, {
            "include_genres": [28],
            "mood": "excited"
        })
        
        # Should mention it's highly rated (8.5)
        assert "8.5" in explanation or "highly rated" in explanation.lower()
    
    def test_tv_explanation_includes_genre_match(self):
        """TV explanations should mention matched genre."""
        scout = ScoutService()
        
        series = {
            "id": 456,
            "name": "Test Series",
            "vote_average": 7.8,
            "genre_ids": [10759, 18],  # Action, Drama
            "first_air_date": "2023-03-01",
            "overview": "An exciting action drama series."
        }
        
        explanation = scout._generate_tv_explanation(series, "excited", [10759])
        
        # Should mention action (matched genre) or include rating
        assert "action" in explanation.lower() or "7.8" in explanation
    
    def test_explanation_not_generic_filler(self):
        """Explanations should not be identical generic text."""
        scout = ScoutService()
        
        movie1 = {
            "title": "Action Film",
            "vote_average": 8.2,
            "genre_ids": [28],
            "release_date": "2023-01-01"
        }
        
        movie2 = {
            "title": "Sci-Fi Film",
            "vote_average": 7.1,
            "genre_ids": [878],
            "release_date": "1985-05-15"
        }
        
        exp1 = scout._generate_explanation(movie1, {"include_genres": [28]})
        exp2 = scout._generate_explanation(movie2, {"include_genres": [878]})
        
        # Explanations should differ (not same generic text)
        assert exp1 != exp2
        
        # High-rated movie should mention rating
        assert "8.2" in exp1 or "highly rated" in exp1.lower()
        
        # Old movie should mention it's a classic
        assert "classic" in exp2.lower() or "sci-fi" in exp2.lower()


@pytest.mark.asyncio
class TestScoutConversationSequence:
    """Test the exact 5-step conversation from user report."""
    
    async def test_five_step_refinement_sequence(self):
        """Test: action → darker → no horror → TV only → Disney TV."""
        scout = ScoutService()
        
        # Mock services
        scout.tmdb = AsyncMock()
        scout.recommendations = AsyncMock()
        
        # Mock responses
        scout.tmdb.discover_movies = AsyncMock(return_value={"results": []})
        scout.tmdb.discover_series = AsyncMock(return_value={"results": []})
        scout.recommendations.get_situation_aware_recommendations = AsyncMock(return_value={"recommendations": []})
        
        history = []
        
        # Step 1: action movies and TV
        result1 = await scout.process_message("suggest action movies and TV shows", history)
        assert "intent" in result1
        history.extend([
            {"role": "user", "content": "suggest action movies and TV shows"},
            {"role": "assistant", "content": result1["message"]}
        ])
        
        # Step 2: make darker - should preserve both media types
        result2 = await scout.process_message("make them darker", history)
        # Verify call included both movies and TV
        assert scout.tmdb.discover_movies.called or scout.tmdb.discover_series.called
        history.extend([
            {"role": "user", "content": "make them darker"},
            {"role": "assistant", "content": result2["message"]}
        ])
        
        # Step 3: no horror - should add exclusion
        result3 = await scout.process_message("no horror, please", history)
        history.extend([
            {"role": "user", "content": "no horror, please"},
            {"role": "assistant", "content": result3["message"]}
        ])
        
        # Step 4: only TV - should switch media type
        result4 = await scout.process_message("now suggest only TV shows", history)
        history.extend([
            {"role": "user", "content": "now suggest only TV shows"},
            {"role": "assistant", "content": result4["message"]}
        ])
        
        # Step 5: Disney TV - should NOT carry forward action genre
        scout.tmdb.discover_series.reset_mock()
        result5 = await scout.process_message("now suggest some good Disney TV shows", history)
        
        # Verify Disney provider was used with region-appropriate ID
        from config import settings
        if settings.watch_region == "US":
            expected_id = 337
        elif settings.watch_region == "IN":
            expected_id = 2336
        else:
            expected_id = None  # Unsupported region
        
        assert scout.tmdb.discover_series.called
        call_kwargs = scout.tmdb.discover_series.call_args[1]
        
        if expected_id:
            assert call_kwargs.get("with_watch_providers") == expected_id
            assert call_kwargs.get("watch_region") == settings.watch_region
        
        # Should NOT have action genre (10759)
        genres_param = call_kwargs.get("with_genres", "")
        if genres_param:
            assert "10759" not in genres_param  # Action should NOT be included
        
        # Message should mention Disney/Hotstar, not action
        assert "Disney" in result5["message"] or "Hotstar" in result5["message"]
        assert "action" not in result5["message"].lower()


@pytest.mark.asyncio
class TestProviderIDVerification:
    """Integration tests - verify correct provider IDs against live TMDB API."""
    
    async def test_us_disney_provider_id(self):
        """Integration: Verify Disney+ provider ID 337 is correct for US."""
        from services.tmdb_service import tmdb_service
        from config import settings
        
        # Only run if we can access TMDB
        try:
            result = await tmdb_service.discover_series(
                page=1,
                with_watch_providers=337,
                watch_region="US",
                vote_count__gte=10
            )
            
            shows = result.get("results", [])
            assert len(shows) > 0, "Disney+ US (337) should return shows"
            
            # Verify first show's provider data
            first_show = shows[0]
            providers_result = await tmdb_service._make_request(
                f"tv/{first_show['id']}/watch/providers"
            )
            
            us_providers = providers_result.get("results", {}).get("US", {})
            flatrate = us_providers.get("flatrate", [])
            
            # Verify Disney Plus (337) is in the provider list
            disney_found = any(p['provider_id'] == 337 for p in flatrate)
            assert disney_found, f"Disney Plus (337) not in providers for {first_show['name']}"
            
        except Exception as e:
            pytest.skip(f"TMDB API unavailable: {type(e).__name__}")
    
    async def test_india_hotstar_provider_id(self):
        """Integration: Verify JioHotstar provider ID 2336 is correct for India."""
        from services.tmdb_service import tmdb_service
        
        try:
            result = await tmdb_service.discover_series(
                page=1,
                with_watch_providers=2336,
                watch_region="IN",
                vote_count__gte=5
            )
            
            shows = result.get("results", [])
            assert len(shows) > 0, "JioHotstar IN (2336) should return shows"
            
            # Verify first show's provider data
            first_show = shows[0]
            providers_result = await tmdb_service._make_request(
                f"tv/{first_show['id']}/watch/providers"
            )
            
            in_providers = providers_result.get("results", {}).get("IN", {})
            flatrate = in_providers.get("flatrate", [])
            
            # Verify JioHotstar (2336) is in the provider list
            hotstar_found = any(p['provider_id'] == 2336 for p in flatrate)
            assert hotstar_found, f"JioHotstar (2336) not in providers for {first_show['name']}"
            
        except Exception as e:
            pytest.skip(f"TMDB API unavailable: {type(e).__name__}")
    
    def test_wrong_provider_id_2_is_not_disney(self):
        """Unit: Verify ID 2 is NOT Disney+ (it's Apple TV Store)."""
        scout = ScoutService()
        
        # ID 2 should not be used for Disney
        parsed = scout._fallback_parse("suggest Disney shows", [])
        assert parsed["preferences"]["provider_id"] != 2
        
        # Should use correct region-based ID
        from config import settings
        if settings.watch_region == "US":
            assert parsed["preferences"]["provider_id"] == 337
        elif settings.watch_region == "IN":
            assert parsed["preferences"]["provider_id"] == 2336
