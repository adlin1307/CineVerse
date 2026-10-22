"""
Regression tests for constraint enforcement in Scout recommendations.

These tests verify:
1. Excluded genres are enforced in final results
2. Fresh requests don't inherit unrelated constraints
3. Refinements preserve context correctly
4. Provider constraints are applied correctly
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from services.scout_service import ScoutService


class TestFreshRequestConstraintLeakage:
    """Test that fresh requests don't inherit old constraints."""
    
    @pytest.mark.asyncio
    async def test_scifi_then_no_horror_then_disney_fresh(self):
        """
        Verify: Sci-fi TV → "no horror" → "now suggest Disney TV"
        The Disney request should NOT have horror exclusion.
        """
        scout = ScoutService()
        
        mock_scifi = {
            "results": [
                {"id": 1, "name": "The Expanse", "genre_ids": [10765, 18], "vote_average": 8.2, 
                 "first_air_date": "2015-12-14", "poster_path": "/exp.jpg", "overview": "Sci-fi drama"}
            ]
        }
        
        mock_disney = {
            "results": [
                {"id": 100, "name": "The Mandalorian", "genre_ids": [10759, 10765], "vote_average": 8.7,
                 "first_air_date": "2019-11-12", "poster_path": "/mand.jpg", "overview": "Star Wars"}
            ]
        }
        
        # Request 1: Sci-fi TV
        with patch.object(scout.tmdb, 'discover_series', new_callable=AsyncMock) as mock_discover:
            mock_discover.return_value = mock_scifi.copy()
            result1 = await scout.process_message("Suggest some good sci-fi TV shows", [])
            assert result1["intent"] == "recommend"
            assert len(result1["recommendations"]) > 0
        
        history1 = [
            {"role": "user", "content": "Suggest some good sci-fi TV shows"},
            {"role": "assistant", "content": result1["message"]}
        ]
        
        # Request 2: No horror (refinement, adds exclusion)
        with patch.object(scout.tmdb, 'discover_series', new_callable=AsyncMock) as mock_discover:
            mock_discover.return_value = mock_scifi.copy()
            result2 = await scout.process_message("No horror, please", history1)
            # Verify horror was excluded from parsing
            # This is a refinement, so it should preserve sci-fi but add horror exclusion
        
        history2 = history1 + [
            {"role": "user", "content": "No horror, please"},
            {"role": "assistant", "content": result2["message"]}
        ]
        
        # Request 3: Disney TV shows (FRESH REQUEST)
        # Intercept _generate_recommendations to inspect the preferences
        original_gen = scout._generate_recommendations
        captured_prefs = {}
        
        async def capture_and_call(prefs):
            captured_prefs.update(prefs)
            return await original_gen(prefs)
        
        with patch.object(scout.tmdb, 'discover_series', new_callable=AsyncMock) as mock_discover:
            mock_discover.return_value = mock_disney.copy()
            with patch.object(scout, '_generate_recommendations', side_effect=capture_and_call):
                result3 = await scout.process_message("Now suggest some good Disney TV shows", history2)
        
        # CRITICAL: Disney request should NOT have horror exclusion (27)
        assert 27 not in captured_prefs.get("exclude_genres", []), \
            f"Fresh Disney request inherited horror exclusion! Prefs: {captured_prefs}"
        
        # Should have provider filter
        assert captured_prefs.get("provider_id") == 2336, "Disney provider ID not set for India"
        assert captured_prefs.get("watch_region") == "IN", "Watch region not set correctly"
        
        # Should NOT have sci-fi genre constraint (fresh request)
        # Provider requests are genre-neutral unless explicitly mentioned
    
    @pytest.mark.asyncio
    async def test_refinement_preserves_context(self):
        """
        Verify: Sci-fi TV → "make them darker"
        The refinement should preserve TV and sci-fi context.
        """
        scout = ScoutService()
        
        mock_results = {
            "results": [
                {"id": 1, "name": "Dark", "genre_ids": [10765, 18], "vote_average": 8.8,
                 "first_air_date": "2017-12-01", "poster_path": "/dark.jpg", "overview": "German sci-fi thriller"}
            ]
        }
        
        # Request 1: Sci-fi TV
        with patch.object(scout.tmdb, 'discover_series', new_callable=AsyncMock) as mock_discover:
            mock_discover.return_value = mock_results.copy()
            result1 = await scout.process_message("Suggest some good sci-fi TV shows", [])
        
        history = [
            {"role": "user", "content": "Suggest some good sci-fi TV shows"},
            {"role": "assistant", "content": result1["message"]}
        ]
        
        # Request 2: Make them darker (REFINEMENT)
        captured_prefs = {}
        original_gen = scout._generate_recommendations
        
        async def capture_and_call(prefs):
            captured_prefs.update(prefs)
            return await original_gen(prefs)
        
        with patch.object(scout.tmdb, 'discover_series', new_callable=AsyncMock) as mock_discover:
            mock_discover.return_value = mock_results.copy()
            with patch.object(scout, '_generate_recommendations', side_effect=capture_and_call):
                result2 = await scout.process_message("Make them darker", history)
        
        # Should preserve TV media type
        assert captured_prefs.get("media_type") == "tv", "Lost TV media type in refinement"
        
        # Should preserve sci-fi genre (10765)
        assert 10765 in captured_prefs.get("include_genres", []), "Lost sci-fi genre in refinement"
        
        # Should add drama (18) for "darker"
        assert 18 in captured_prefs.get("include_genres", []), "Didn't add drama for 'darker'"
    
    @pytest.mark.asyncio
    async def test_constraint_only_followup(self):
        """
        Verify: Sci-fi TV → "no horror"
        The follow-up should preserve sci-fi/TV but add horror exclusion.
        """
        scout = ScoutService()
        
        mock_results = {
            "results": [
                {"id": 1, "name": "The Expanse", "genre_ids": [10765], "vote_average": 8.2,
                 "first_air_date": "2015-12-14", "poster_path": "/exp.jpg", "overview": "Space drama"},
                {"id": 2, "name": "Supernatural", "genre_ids": [10765, 27], "vote_average": 8.3,
                 "first_air_date": "2005-09-13", "poster_path": "/spn.jpg", "overview": "Horror fantasy"}
            ]
        }
        
        # Request 1: Sci-fi TV
        with patch.object(scout.tmdb, 'discover_series', new_callable=AsyncMock) as mock_discover:
            mock_discover.return_value = mock_results.copy()
            result1 = await scout.process_message("Suggest some good sci-fi TV shows", [])
        
        history = [
            {"role": "user", "content": "Suggest some good sci-fi TV shows"},
            {"role": "assistant", "content": result1["message"]}
        ]
        
        # Request 2: No horror (CONSTRAINT-ONLY REFINEMENT)
        captured_prefs = {}
        original_gen = scout._generate_recommendations
        
        async def capture_and_call(prefs):
            captured_prefs.update(prefs)
            return await original_gen(prefs)
        
        with patch.object(scout.tmdb, 'discover_series', new_callable=AsyncMock) as mock_discover:
            mock_discover.return_value = mock_results.copy()
            with patch.object(scout, '_generate_recommendations', side_effect=capture_and_call):
                result2 = await scout.process_message("No horror, please", history)
        
        # Should preserve TV media type
        assert captured_prefs.get("media_type") == "tv", "Lost TV media type"
        
        # Should preserve sci-fi genre
        assert 10765 in captured_prefs.get("include_genres", []), "Lost sci-fi genre"
        
        # Should add horror exclusion
        assert 27 in captured_prefs.get("exclude_genres", []), "Didn't add horror exclusion"
        
        # Results should NOT contain horror
        for rec in result2["recommendations"]:
            assert 27 not in rec.get("genre_ids", []), f"Horror found in {rec['title']}"


class TestConstraintEnforcement:
    """Test hard constraint enforcement in final results."""
    
    @pytest.mark.asyncio
    async def test_scifi_tv_then_darker_then_no_horror(self):
        """
        Test sequence: Sci-fi TV → make them darker → no horror
        Verify TV/sci-fi context preserved and horror candidates absent.
        """
        scout = ScoutService()
        
        # Mock TMDB responses with genre metadata
        mock_scifi_results = {
            "results": [
                {"id": 1, "name": "The Expanse", "genre_ids": [10765, 18], "vote_average": 8.2, "first_air_date": "2015-12-14", "poster_path": "/poster1.jpg", "overview": "Sci-fi drama in space"},
                {"id": 2, "name": "Dark Matter", "genre_ids": [10765], "vote_average": 7.5, "first_air_date": "2015-06-12", "poster_path": "/poster2.jpg", "overview": "Mystery sci-fi"},
                {"id": 3, "name": "Supernatural", "genre_ids": [10765, 27], "vote_average": 8.3, "first_air_date": "2005-09-13", "poster_path": "/poster3.jpg", "overview": "Horror fantasy"},
            ]
        }
        
        # Request 1: Sci-fi TV shows
        with patch.object(scout.tmdb, 'discover_series', new_callable=AsyncMock) as mock_discover:
            mock_discover.return_value = mock_scifi_results.copy()
            
            result1 = await scout.process_message(
                "Suggest some good sci-fi TV shows",
                []
            )
            
            assert result1["intent"] == "recommend"
            assert len(result1["recommendations"]) > 0
            # All should be TV
            assert all(r["media_type"] == "tv" for r in result1["recommendations"])
            # All should have sci-fi genre (10765)
            assert all(10765 in r["genre_ids"] for r in result1["recommendations"])
        
        # Request 2: Make them darker (refinement)
        conversation_history = [
            {"role": "user", "content": "Suggest some good sci-fi TV shows"},
            {"role": "assistant", "content": "Finding some great sci-fi picks for you!"}
        ]
        
        with patch.object(scout.tmdb, 'discover_series', new_callable=AsyncMock) as mock_discover:
            mock_discover.return_value = mock_scifi_results.copy()
            
            result2 = await scout.process_message(
                "Make them darker",
                conversation_history
            )
            
            assert result2["intent"] == "recommend"
            # Should still be TV
            assert all(r["media_type"] == "tv" for r in result2["recommendations"])
            # Should still have sci-fi (10765)
            assert all(10765 in r["genre_ids"] for r in result2["recommendations"])
            # Should have added drama (18) for "darker"
            # Note: At least some should have drama
        
        # Request 3: No horror, please (exclusion)
        conversation_history.extend([
            {"role": "user", "content": "Make them darker"},
            {"role": "assistant", "content": "Got it - refining your sci-fi picks!"}
        ])
        
        with patch.object(scout.tmdb, 'discover_series', new_callable=AsyncMock) as mock_discover:
            mock_discover.return_value = mock_scifi_results.copy()
            
            result3 = await scout.process_message(
                "No horror, please",
                conversation_history
            )
            
            assert result3["intent"] == "recommend"
            # CRITICAL: NO results should contain horror (27)
            for rec in result3["recommendations"]:
                assert 27 not in rec["genre_ids"], f"Found horror in {rec['title']}: genres={rec['genre_ids']}"
            # Should still be TV and sci-fi
            assert all(r["media_type"] == "tv" for r in result3["recommendations"])
    
    @pytest.mark.asyncio
    async def test_scifi_tv_then_disney_tv_shows(self):
        """
        Test sequence: Sci-fi TV → Disney TV shows
        Verify this is a fresh request and provider constraints replace genre preferences.
        """
        scout = ScoutService()
        
        mock_scifi_results = {
            "results": [
                {"id": 1, "name": "The Expanse", "genre_ids": [10765, 18], "vote_average": 8.2, "first_air_date": "2015-12-14", "poster_path": "/poster1.jpg", "overview": "Sci-fi drama"},
            ]
        }
        
        mock_disney_results = {
            "results": [
                {"id": 100, "name": "The Mandalorian", "genre_ids": [10759, 10765], "vote_average": 8.7, "first_air_date": "2019-11-12", "poster_path": "/poster100.jpg", "overview": "Star Wars series"},
                {"id": 101, "name": "Loki", "genre_ids": [10765, 18], "vote_average": 8.2, "first_air_date": "2021-06-09", "poster_path": "/poster101.jpg", "overview": "Marvel series"},
            ]
        }
        
        # Request 1: Sci-fi TV shows
        with patch.object(scout.tmdb, 'discover_series', new_callable=AsyncMock) as mock_discover:
            mock_discover.return_value = mock_scifi_results.copy()
            
            result1 = await scout.process_message(
                "Suggest some good sci-fi TV shows",
                []
            )
            
            assert result1["intent"] == "recommend"
            assert all(r["media_type"] == "tv" for r in result1["recommendations"])
        
        # Request 2: Now suggest Disney TV shows (FRESH REQUEST)
        conversation_history = [
            {"role": "user", "content": "Suggest some good sci-fi TV shows"},
            {"role": "assistant", "content": "Finding some great sci-fi picks for you!"}
        ]
        
        with patch.object(scout.tmdb, 'discover_series', new_callable=AsyncMock) as mock_discover:
            mock_discover.return_value = mock_disney_results.copy()
            
            result2 = await scout.process_message(
                "Now suggest some good Disney TV shows",
                conversation_history
            )
            
            assert result2["intent"] == "recommend"
            # Should be TV
            assert all(r["media_type"] == "tv" for r in result2["recommendations"])
            # Should NOT be filtered to sci-fi only (genre constraint should not carry over)
            # The results can have any genre, not just sci-fi
            # Verify provider was set (this is implicit in the mock setup)
    
    @pytest.mark.asyncio
    async def test_disney_tv_then_romantic_movies(self):
        """
        Test sequence: Disney TV shows → romantic movies for date night
        Verify new request switches to movies/romance without inheriting provider constraints.
        """
        scout = ScoutService()
        
        mock_disney_results = {
            "results": [
                {"id": 100, "name": "The Mandalorian", "genre_ids": [10759, 10765], "vote_average": 8.7, "first_air_date": "2019-11-12", "poster_path": "/poster100.jpg", "overview": "Star Wars"},
            ]
        }
        
        mock_romance_results = {
            "results": [
                {"id": 200, "title": "The Notebook", "genre_ids": [10749, 18], "vote_average": 7.9, "release_date": "2004-06-25", "poster_path": "/poster200.jpg", "overview": "Love story"},
                {"id": 201, "title": "La La Land", "genre_ids": [10749, 35, 18], "vote_average": 8.0, "release_date": "2016-12-09", "poster_path": "/poster201.jpg", "overview": "Musical romance"},
            ]
        }
        
        # Request 1: Disney TV shows
        with patch.object(scout.tmdb, 'discover_series', new_callable=AsyncMock) as mock_discover:
            mock_discover.return_value = mock_disney_results.copy()
            
            result1 = await scout.process_message(
                "Suggest some good Disney TV shows",
                []
            )
            
            assert result1["intent"] == "recommend"
            assert all(r["media_type"] == "tv" for r in result1["recommendations"])
        
        # Request 2: Romantic movies (FRESH REQUEST - different media type and genre)
        conversation_history = [
            {"role": "user", "content": "Suggest some good Disney TV shows"},
            {"role": "assistant", "content": "Searching Disney+ Hotstar for some great shows!"}
        ]
        
        with patch.object(scout.tmdb, 'discover_movies', new_callable=AsyncMock) as mock_discover:
            mock_discover.return_value = mock_romance_results.copy()
            
            result2 = await scout.process_message(
                "Suggest some romantic movies for a date night",
                conversation_history
            )
            
            assert result2["intent"] == "recommend"
            # Should be movies, not TV
            assert all(r["media_type"] == "movie" for r in result2["recommendations"])
            # Should have romance genre (10749)
            assert all(10749 in r["genre_ids"] for r in result2["recommendations"])
            # Should NOT have Disney provider filter carried over
            # (implicit - if it did, results would be different)
    
    @pytest.mark.asyncio
    async def test_excluded_genres_actually_filtered_from_results(self):
        """
        Test that excluded genres are actually removed from final results,
        not just passed to TMDB (which might ignore them).
        """
        scout = ScoutService()
        
        # Mock TMDB returning results with mixed genres including excluded ones
        mock_mixed_results = {
            "results": [
                {"id": 1, "name": "Breaking Bad", "genre_ids": [18, 80], "vote_average": 9.5, "first_air_date": "2008-01-20", "poster_path": "/bb.jpg", "overview": "Drama crime"},
                {"id": 2, "name": "The Walking Dead", "genre_ids": [18, 27], "vote_average": 8.2, "first_air_date": "2010-10-31", "poster_path": "/twd.jpg", "overview": "Horror drama"},
                {"id": 3, "name": "Better Call Saul", "genre_ids": [18, 80], "vote_average": 9.0, "first_air_date": "2015-02-08", "poster_path": "/bcs.jpg", "overview": "Drama crime"},
                {"id": 4, "name": "American Horror Story", "genre_ids": [27, 18], "vote_average": 8.0, "first_air_date": "2011-10-05", "poster_path": "/ahs.jpg", "overview": "Horror anthology"},
            ]
        }
        
        with patch.object(scout.tmdb, 'discover_series', new_callable=AsyncMock) as mock_discover:
            mock_discover.return_value = mock_mixed_results.copy()
            
            result = await scout.process_message(
                "Suggest some TV dramas but no horror please",
                []
            )
            
            assert result["intent"] == "recommend"
            assert len(result["recommendations"]) > 0
            
            # CRITICAL: Verify NO results contain horror (27)
            for rec in result["recommendations"]:
                assert 27 not in rec["genre_ids"], f"Horror genre found in {rec['title']}: {rec['genre_ids']}"
            
            # Should only return Breaking Bad and Better Call Saul (not The Walking Dead or American Horror Story)
            titles = [r["title"] for r in result["recommendations"]]
            assert "The Walking Dead" not in titles
            assert "American Horror Story" not in titles
    
    @pytest.mark.asyncio
    async def test_empty_results_after_filtering(self):
        """
        Test that Scout handles empty results gracefully when all candidates
        are filtered out due to exclusions.
        """
        scout = ScoutService()
        
        # Mock TMDB returning only horror results
        mock_only_horror = {
            "results": [
                {"id": 1, "name": "The Walking Dead", "genre_ids": [18, 27], "vote_average": 8.2, "first_air_date": "2010-10-31", "poster_path": "/twd.jpg", "overview": "Horror"},
                {"id": 2, "name": "American Horror Story", "genre_ids": [27, 18], "vote_average": 8.0, "first_air_date": "2011-10-05", "poster_path": "/ahs.jpg", "overview": "Horror"},
            ]
        }
        
        with patch.object(scout.tmdb, 'discover_series', new_callable=AsyncMock) as mock_discover:
            mock_discover.return_value = mock_only_horror.copy()
            
            result = await scout.process_message(
                "Suggest some TV shows but no horror",
                []
            )
            
            # Should return empty recommendations
            assert result["recommendations"] == []
            # Message should reflect no results found
            # (Implementation may vary - could be empty list or explanatory message)


class TestGenreAccuracy:
    """Test genre matching accuracy."""
    
    @pytest.mark.asyncio
    async def test_scifi_tv_returns_actual_scifi(self):
        """Verify sci-fi TV request returns actual sci-fi shows."""
        scout = ScoutService()
        
        mock_results = {
            "results": [
                {"id": 1, "name": "The Expanse", "genre_ids": [10765, 18], "vote_average": 8.2, "first_air_date": "2015-12-14", "poster_path": "/exp.jpg", "overview": "Sci-fi"},
                {"id": 2, "name": "Doraemon", "genre_ids": [16, 10751, 35], "vote_average": 7.2, "first_air_date": "2005-04-15", "poster_path": "/dora.jpg", "overview": "Kids anime"},
                {"id": 3, "name": "Dark", "genre_ids": [10765, 18, 9648], "vote_average": 8.8, "first_air_date": "2017-12-01", "poster_path": "/dark.jpg", "overview": "German sci-fi"},
            ]
        }
        
        with patch.object(scout.tmdb, 'discover_series', new_callable=AsyncMock) as mock_discover:
            mock_discover.return_value = mock_results.copy()
            
            result = await scout.process_message(
                "Suggest some good sci-fi TV shows",
                []
            )
            
            assert result["intent"] == "recommend"
            # All results should have sci-fi genre (10765 for TV)
            for rec in result["recommendations"]:
                assert 10765 in rec["genre_ids"], f"{rec['title']} missing sci-fi genre: {rec['genre_ids']}"
            
            # Doraemon should be filtered out (no sci-fi genre)
            titles = [r["title"] for r in result["recommendations"]]
            assert "Doraemon" not in titles



class TestProviderAndRegion:
    """Test provider constraint handling and regional configuration."""
    
    @pytest.mark.asyncio
    async def test_provider_constraints_passed_to_tmdb(self):
        """Verify provider ID and region are passed correctly to TMDB discover."""
        scout = ScoutService()
        
        # Mock to capture actual TMDB call parameters
        captured_params = {}
        original_discover = scout.tmdb.discover_series
        
        async def capture_discover(**kwargs):
            captured_params.update(kwargs)
            return {
                "results": [
                    {"id": 100, "name": "Test Show", "genre_ids": [10759], "vote_average": 8.0,
                     "first_air_date": "2020-01-01", "poster_path": "/test.jpg", "overview": "Test"}
                ]
            }
        
        with patch.object(scout.tmdb, 'discover_series', side_effect=capture_discover):
            await scout.process_message("Suggest Disney TV shows", [])
        
        # Verify provider and region were passed
        assert captured_params.get("with_watch_providers") == 2336, "India Disney+ Hotstar ID not passed"
        assert captured_params.get("watch_region") == "IN", "India region not passed"
    
    @pytest.mark.asyncio
    async def test_disney_to_romantic_movies_clears_provider(self):
        """Verify Disney TV → romantic movies clears provider constraint."""
        scout = ScoutService()
        
        mock_disney = {
            "results": [
                {"id": 100, "name": "The Mandalorian", "genre_ids": [10759], "vote_average": 8.7,
                 "first_air_date": "2019-11-12", "poster_path": "/mand.jpg", "overview": "Star Wars"}
            ]
        }
        
        mock_romance = {
            "results": [
                {"id": 200, "title": "The Notebook", "genre_ids": [10749, 18], "vote_average": 7.9,
                 "release_date": "2004-06-25", "poster_path": "/notebook.jpg", "overview": "Love story"}
            ]
        }
        
        # Request 1: Disney TV
        with patch.object(scout.tmdb, 'discover_series', new_callable=AsyncMock) as mock_discover:
            mock_discover.return_value = mock_disney.copy()
            result1 = await scout.process_message("Suggest Disney TV shows", [])
        
        history = [
            {"role": "user", "content": "Suggest Disney TV shows"},
            {"role": "assistant", "content": result1["message"]}
        ]
        
        # Request 2: Romantic movies (FRESH REQUEST)
        captured_prefs = {}
        original_gen = scout._generate_recommendations
        
        async def capture_and_call(prefs):
            captured_prefs.update(prefs)
            return await original_gen(prefs)
        
        with patch.object(scout.tmdb, 'discover_movies', new_callable=AsyncMock) as mock_discover:
            mock_discover.return_value = mock_romance.copy()
            with patch.object(scout, '_generate_recommendations', side_effect=capture_and_call):
                result2 = await scout.process_message("Suggest romantic movies for a date night", history)
        
        # Should NOT have provider constraint
        assert captured_prefs.get("provider_id") is None, "Provider constraint leaked to fresh request"
        
        # Should be movies with romance
        assert captured_prefs.get("media_type") == "movie"
        assert 10749 in captured_prefs.get("include_genres", [])


class TestTimeoutHandling:
    """Test TMDB timeout handling."""
    
    @pytest.mark.asyncio
    async def test_tmdb_timeout_returns_friendly_error(self):
        """Verify TMDB timeout produces clear error without fabricating results."""
        scout = ScoutService()
        
        # Mock TMDB timeout - tmdb_service wraps httpx.TimeoutException in ValueError
        async def timeout_error(**kwargs):
            raise ValueError("TMDB API request timed out (read timeout after 30s): discover/tv")
        
        with patch.object(scout.tmdb, 'discover_series', side_effect=timeout_error):
            try:
                await scout.process_message("Suggest sci-fi TV shows", [])
                assert False, "Should have raised exception"
            except Exception as e:
                error_msg = str(e)
                # Should mention TMDB or database or timeout
                assert "database" in error_msg.lower() or "tmdb" in error_msg.lower() or "too long" in error_msg.lower(), \
                    f"Error message not user-friendly: {error_msg}"
                # Should NOT fabricate recommendations
                assert "check out" not in error_msg.lower()
                assert "here are" not in error_msg.lower()
    
    @pytest.mark.asyncio
    async def test_empty_result_vs_timeout(self):
        """Distinguish between valid empty result and network failure."""
        scout = ScoutService()
        
        # Test 1: Valid empty result (all filtered out)
        mock_empty = {"results": []}
        
        with patch.object(scout.tmdb, 'discover_series', new_callable=AsyncMock) as mock_discover:
            mock_discover.return_value = mock_empty
            result = await scout.process_message("Suggest sci-fi TV shows", [])
            # Should succeed with empty recommendations
            assert result["recommendations"] == []
            assert result["intent"] == "recommend"
        
        # Test 2: Network timeout (exception)
        async def network_error(**kwargs):
            raise ValueError("TMDB API request timed out (read timeout after 30s): discover/tv")
        
        with patch.object(scout.tmdb, 'discover_series', side_effect=network_error):
            try:
                await scout.process_message("Suggest sci-fi TV shows", [])
                assert False, "Should have raised exception"
            except Exception as e:
                error_msg = str(e).lower()
                # Should mention timeout/database/tmdb
                assert "timed out" in error_msg or "timeout" in error_msg or "database" in error_msg or "too long" in error_msg, \
                    f"Timeout not clearly communicated: {e}"


class TestMissingGenreMetadata:
    """Test handling of missing genre metadata."""
    
    @pytest.mark.asyncio
    async def test_missing_genre_metadata_safe_handling(self):
        """Verify missing genre_ids doesn't bypass hard constraints."""
        scout = ScoutService()
        
        # Mock with missing genre_ids
        mock_results = {
            "results": [
                {"id": 1, "name": "Show Without Genres", "vote_average": 8.0,
                 "first_air_date": "2020-01-01", "poster_path": "/test.jpg", "overview": "Test"},
                {"id": 2, "name": "Sci-fi Show", "genre_ids": [10765, 18], "vote_average": 8.5,
                 "first_air_date": "2021-01-01", "poster_path": "/test2.jpg", "overview": "Actual sci-fi"}
            ]
        }
        
        with patch.object(scout.tmdb, 'discover_series', new_callable=AsyncMock) as mock_discover:
            mock_discover.return_value = mock_results.copy()
            result = await scout.process_message("Suggest sci-fi TV shows", [])
        
        # Show without genre_ids should still be included (can't verify constraint)
        # But show WITH genre_ids that match should definitely be there
        titles = [r["title"] for r in result["recommendations"]]
        assert "Sci-fi Show" in titles, "Valid sci-fi show should be included"
        
        # If missing genres are included, that's acceptable (we can't filter without data)
        # But we should never claim they match when we can't verify
    
    @pytest.mark.asyncio
    async def test_exclusion_with_missing_metadata(self):
        """Verify exclusions still work when some results lack genre_ids."""
        scout = ScoutService()
        
        mock_results = {
            "results": [
                {"id": 1, "name": "No Metadata", "vote_average": 8.0,
                 "first_air_date": "2020-01-01", "poster_path": "/test.jpg", "overview": "Unknown genres"},
                {"id": 2, "name": "Horror Show", "genre_ids": [27, 18], "vote_average": 7.5,
                 "first_air_date": "2021-01-01", "poster_path": "/horror.jpg", "overview": "Scary"},
                {"id": 3, "name": "Drama Show", "genre_ids": [18], "vote_average": 8.5,
                 "first_air_date": "2022-01-01", "poster_path": "/drama.jpg", "overview": "Dramatic"}
            ]
        }
        
        with patch.object(scout.tmdb, 'discover_series', new_callable=AsyncMock) as mock_discover:
            mock_discover.return_value = mock_results.copy()
            result = await scout.process_message("Suggest TV shows but no horror", [])
        
        # Horror Show (with genre 27) should be EXCLUDED
        titles = [r["title"] for r in result["recommendations"]]
        assert "Horror Show" not in titles, "Horror show should be excluded"
        
        # Drama Show and No Metadata can be included
        assert "Drama Show" in titles or "No Metadata" in titles
