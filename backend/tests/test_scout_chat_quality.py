"""
Tests for Scout chat quality improvements.

Tests greeting handling, emotional sub-intent, refinement depth, and recommendation limits.
"""

import pytest
import json
from unittest.mock import AsyncMock, patch
from services.scout_service import scout_service


class TestGreetingHandling:
    """Test that greetings don't trigger recommendations."""
    
    @pytest.mark.asyncio
    async def test_simple_greeting_no_recommendations(self):
        """Simple greetings should not trigger recommendations."""
        result = scout_service._fallback_parse("Hi", [])
        
        assert result["intent"] == "chat"
        # Chat intent should have empty preferences (no genres to fetch)
        assert result.get("preferences", {}).get("include_genres", []) == []
        assert "recommendations" not in result or result.get("recommendations") == []
    
    @pytest.mark.asyncio
    async def test_how_are_you_no_recommendations(self):
        """'How are you?' should be chat, not recommendations."""
        result = scout_service._fallback_parse("How are you?", [])
        
        assert result["intent"] == "chat"
        assert "Doing great" in result["message"] or "Ready" in result["message"]
        assert result.get("preferences", {}).get("include_genres", []) == []
    
    @pytest.mark.asyncio
    async def test_thanks_no_recommendations(self):
        """'Thanks' should not trigger recommendations."""
        result = scout_service._fallback_parse("Thanks!", [])
        
        assert result["intent"] == "chat"
        assert "welcome" in result["message"].lower()
        assert result.get("preferences", {}).get("include_genres", []) == []


class TestEmotionalSubIntent:
    """Test emotional sub-intent detection and classification."""
    
    @pytest.mark.asyncio
    async def test_emotional_general(self):
        """'I want something emotional' should detect general emotional."""
        result = scout_service._fallback_parse("I want something emotional", [])
        
        assert result["intent"] == "recommend"
        assert result["preferences"]["emotional_sub_intent"] == "general"
        assert 18 in result["preferences"]["include_genres"]  # Drama
    
    @pytest.mark.asyncio
    async def test_cry_tearjerker(self):
        """'I wanna cry' should detect tearjerker sub-intent."""
        result = scout_service._fallback_parse("brooo I wanna cry", [])
        
        assert result["intent"] == "recommend"
        assert result["preferences"]["emotional_sub_intent"] == "tearjerker"
        assert 18 in result["preferences"]["include_genres"]  # Drama
    
    @pytest.mark.asyncio
    async def test_feelgood_uplifting(self):
        """'Something feel-good' should detect feelgood sub-intent."""
        result = scout_service._fallback_parse("I want something feel-good and uplifting", [])
        
        assert result["intent"] == "recommend"
        assert result["preferences"]["emotional_sub_intent"] == "feelgood"
        assert 18 in result["preferences"]["include_genres"]  # Drama
        assert 10751 in result["preferences"]["include_genres"]  # Family
    
    @pytest.mark.asyncio
    async def test_heartbreaking_tearjerker(self):
        """'Heartbreaking' should map to tearjerker."""
        result = scout_service._fallback_parse("something heartbreaking", [])
        
        assert result["intent"] == "recommend"
        assert result["preferences"]["emotional_sub_intent"] == "tearjerker"
    
    @pytest.mark.asyncio
    async def test_bittersweet(self):
        """'Bittersweet' should be detected as emotional sub-intent."""
        result = scout_service._fallback_parse("bittersweet drama", [])
        
        assert result["intent"] == "recommend"
        assert result["preferences"]["emotional_sub_intent"] == "bittersweet"


class TestRefinementPreservation:
    """Test that refinements preserve emotional context."""
    
    @pytest.mark.asyncio
    async def test_exclude_romance_preserves_emotional(self):
        """'Not romance though' should preserve emotional intent."""
        # First request
        history = []
        result1 = scout_service._fallback_parse("I want something emotional", history)
        
        # Add to history
        history = [
            {"role": "user", "content": "I want something emotional"},
            {"role": "assistant", "content": "Here are some emotional picks"}
        ]
        
        # Refinement
        result2 = scout_service._fallback_parse("Not romance though", history)
        
        assert result2["intent"] == "recommend"
        assert 10749 in result2["preferences"]["exclude_genres"]  # Romance excluded
        # Should preserve emotional mood
        assert result2["preferences"]["mood"] == "emotional" or 18 in result2["preferences"]["include_genres"]
    
    @pytest.mark.asyncio
    async def test_fresh_comedy_replaces_emotional(self):
        """'Actually, give me a comedy' should start fresh."""
        history = [
            {"role": "user", "content": "I want something emotional"},
            {"role": "assistant", "content": "Here are some emotional picks"}
        ]
        
        result = scout_service._fallback_parse("Actually, give me a comedy", history)
        
        assert result["intent"] == "recommend"
        assert 35 in result["preferences"]["include_genres"]  # Comedy
        # Should NOT have emotional genres
        assert result["preferences"]["mood"] == "relaxed" or 35 in result["preferences"]["include_genres"]


class TestRecommendationCount:
    """Test that recommendation count is limited to 3."""
    
    @pytest.mark.asyncio
    async def test_max_three_recommendations(self):
        """Default recommendations should be limited to 3."""
        mock_movies = {
            "results": [
                {"id": i, "title": f"Movie {i}", "genre_ids": [18], "vote_average": 7.0, "vote_count": 100, 
                 "popularity": 50.0, "release_date": "2023-01-01", "overview": "Test movie"}
                for i in range(1, 11)  # 10 movies
            ]
        }
        
        with patch.object(scout_service.tmdb, 'discover_movies', new_callable=AsyncMock) as mock_discover:
            mock_discover.return_value = mock_movies
            
            preferences = {
                "mood": "emotional",
                "include_genres": [18],
                "exclude_genres": [],
                "media_type": "movie",
                "provider_id": None,
                "watch_region": "US"
            }
            
            results = await scout_service._generate_recommendations(preferences)
        
        # Should return max 3
        assert len(results) <= 3, f"Expected max 3 recommendations, got {len(results)}"


class TestNoFabrication:
    """Test that explanations don't fabricate emotional claims."""
    
    @pytest.mark.asyncio
    async def test_no_will_make_you_cry_claim(self):
        """Explanations should not claim 'will make you cry'."""
        mock_movies = {
            "results": [
                {
                    "id": 1,
                    "title": "Test Drama",
                    "genre_ids": [18],
                    "vote_average": 8.0,
                    "vote_count": 1000,
                    "popularity": 80.0,
                    "release_date": "2023-01-01",
                    "overview": "A powerful emotional story",
                    "poster_path": "/test.jpg"
                }
            ]
        }
        
        with patch.object(scout_service.tmdb, 'discover_movies', new_callable=AsyncMock) as mock_discover:
            mock_discover.return_value = mock_movies
            
            preferences = {
                "mood": "emotional",
                "include_genres": [18],
                "exclude_genres": [],
                "media_type": "movie",
                "provider_id": None,
                "watch_region": "US",
                "emotional_sub_intent": "tearjerker"
            }
            
            results = await scout_service._generate_recommendations(preferences)
        
        # Check explanations don't fabricate
        for result in results:
            explanation = result.get("explanation", "").lower()
            # Should not make absolute emotional claims
            assert "will make you cry" not in explanation
            assert "definitely" not in explanation
            assert "guaranteed" not in explanation


class TestTMDBFailureHandling:
    """Test TMDB failure produces honest error."""
    
    @pytest.mark.asyncio
    async def test_tmdb_failure_no_fabrication(self):
        """TMDB failure should return empty results, not fabricated."""
        with patch.object(scout_service.tmdb, 'discover_movies', new_callable=AsyncMock) as mock_discover:
            mock_discover.side_effect = Exception("TMDB API error")
            
            preferences = {
                "mood": "emotional",
                "include_genres": [18],
                "exclude_genres": [],
                "media_type": "movie",
                "provider_id": None,
                "watch_region": "US"
            }
            
            results = await scout_service._generate_recommendations(preferences)
        
        # Should return empty list on failure
        assert results == []


class TestGenreExclusionEnforcement:
    """Test that excluded genres are never in final results."""
    
    @pytest.mark.asyncio
    async def test_no_horror_in_results(self):
        """'No horror' should exclude horror from results."""
        mock_movies = {
            "results": [
                {"id": 1, "title": "Drama", "genre_ids": [18], "vote_average": 7.0, "vote_count": 100, "popularity": 50.0, "release_date": "2023-01-01"},
                {"id": 2, "title": "Horror", "genre_ids": [27], "vote_average": 7.0, "vote_count": 100, "popularity": 50.0, "release_date": "2023-01-01"},
                {"id": 3, "title": "Horror Drama", "genre_ids": [27, 18], "vote_average": 7.0, "vote_count": 100, "popularity": 50.0, "release_date": "2023-01-01"}
            ]
        }
        
        with patch.object(scout_service.tmdb, 'discover_movies', new_callable=AsyncMock) as mock_discover:
            mock_discover.return_value = mock_movies
            
            preferences = {
                "mood": "emotional",
                "include_genres": [18],
                "exclude_genres": [27],  # No horror
                "media_type": "movie",
                "provider_id": None,
                "watch_region": "US"
            }
            
            results = await scout_service._generate_recommendations(preferences)
        
        # Check no horror in results
        for result in results:
            assert 27 not in result.get("genre_ids", []), f"Horror found in {result.get('title')}"
