"""
Tests for the recommendation service.

These tests use mocked TMDB data and do not require a live API connection.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from services.recommendation_service import (
    RecommendationService,
    GENRE_MAP,
    VALID_MOODS,
    VALID_OCCASIONS,
    VALID_RUNTIME_PREFS
)


# Mock movie data for testing
MOCK_MOVIES = [
    {
        "id": 1,
        "title": "Action Thriller",
        "genre_ids": [28, 53],  # Action, Thriller
        "runtime": 120,
        "vote_average": 8.0,
        "vote_count": 5000,
        "popularity": 100.0,
        "overview": "An exciting action movie"
    },
    {
        "id": 2,
        "title": "Romantic Comedy",
        "genre_ids": [35, 10749],  # Comedy, Romance
        "runtime": 95,
        "vote_average": 7.5,
        "vote_count": 3000,
        "popularity": 80.0,
        "overview": "A heartwarming romantic comedy"
    },
    {
        "id": 3,
        "title": "Horror Film",
        "genre_ids": [27],  # Horror
        "runtime": 85,
        "vote_average": 6.5,
        "vote_count": 2000,
        "popularity": 60.0,
        "overview": "A scary horror movie"
    },
    {
        "id": 4,
        "title": "Family Animation",
        "genre_ids": [16, 10751],  # Animation, Family
        "runtime": 100,
        "vote_average": 8.5,
        "vote_count": 8000,
        "popularity": 150.0,
        "overview": "A fun family movie"
    },
    {
        "id": 5,
        "title": "Long Drama",
        "genre_ids": [18],  # Drama
        "runtime": 180,
        "vote_average": 9.0,
        "vote_count": 10000,
        "popularity": 200.0,
        "overview": "An epic drama"
    },
    {
        "id": 6,
        "title": "Short Comedy",
        "genre_ids": [35],  # Comedy
        "runtime": 75,
        "vote_average": 7.0,
        "vote_count": 1500,
        "popularity": 50.0,
        "overview": "A quick comedy"
    },
    {
        "id": 7,
        "title": "No Runtime Data",
        "genre_ids": [18, 9648],  # Drama, Mystery
        "runtime": None,  # Missing runtime
        "vote_average": 7.8,
        "vote_count": 2500,
        "popularity": 70.0,
        "overview": "Movie without runtime info"
    },
    {
        "id": 8,
        "title": "No Ratings",
        "genre_ids": [878],  # Sci-Fi
        "runtime": 110,
        "vote_average": None,  # Missing rating
        "vote_count": None,
        "popularity": 40.0,
        "overview": "Movie without ratings"
    },
    {
        "id": 9,
        "title": "No Genres",
        "genre_ids": [],  # Missing genres
        "runtime": 95,
        "vote_average": 7.2,
        "vote_count": 1800,
        "popularity": 55.0,
        "overview": "Movie without genre data"
    },
    {
        "id": 10,
        "title": "Documentary",
        "genre_ids": [99],  # Documentary
        "runtime": 90,
        "vote_average": 8.2,
        "vote_count": 4000,
        "popularity": 90.0,
        "overview": "An informative documentary"
    }
]


@pytest.fixture
def service():
    """Create a recommendation service instance with mocked TMDB."""
    svc = RecommendationService()
    
    # Mock the TMDB service
    mock_tmdb = MagicMock()
    
    # Mock discover_movies to return our test data
    async def mock_discover(*args, **kwargs):
        return {"results": MOCK_MOVIES, "page": 1, "total_pages": 1}
    
    mock_tmdb.discover_movies = AsyncMock(side_effect=mock_discover)
    svc.tmdb = mock_tmdb
    
    return svc


class TestInputValidation:
    """Test input validation."""
    
    @pytest.mark.asyncio
    async def test_invalid_mood(self, service):
        """Test that invalid mood raises ValueError."""
        with pytest.raises(ValueError, match="Invalid mood"):
            await service.get_situation_aware_recommendations(
                mood="invalid_mood",
                occasion="alone",
                runtime_preference="flexible"
            )
    
    @pytest.mark.asyncio
    async def test_invalid_occasion(self, service):
        """Test that invalid occasion raises ValueError."""
        with pytest.raises(ValueError, match="Invalid occasion"):
            await service.get_situation_aware_recommendations(
                mood="relaxed",
                occasion="invalid_occasion",
                runtime_preference="flexible"
            )
    
    @pytest.mark.asyncio
    async def test_invalid_runtime_preference(self, service):
        """Test that invalid runtime preference raises ValueError."""
        with pytest.raises(ValueError, match="Invalid runtime_preference"):
            await service.get_situation_aware_recommendations(
                mood="relaxed",
                occasion="alone",
                runtime_preference="invalid_runtime"
            )
    
    @pytest.mark.asyncio
    async def test_invalid_genre_id(self, service):
        """Test that invalid genre IDs raise ValueError."""
        with pytest.raises(ValueError, match="Invalid genre IDs"):
            await service.get_situation_aware_recommendations(
                mood="relaxed",
                occasion="alone",
                runtime_preference="flexible",
                excluded_genres=[999, 1000]  # Invalid IDs
            )
    
    @pytest.mark.asyncio
    async def test_valid_inputs(self, service):
        """Test that valid inputs are accepted."""
        result = await service.get_situation_aware_recommendations(
            mood="relaxed",
            occasion="alone",
            runtime_preference="flexible"
        )
        assert "recommendations" in result
        assert "situation_context" in result


class TestGenreExclusion:
    """Test genre exclusion hard constraints."""
    
    @pytest.mark.asyncio
    async def test_exclude_horror(self, service):
        """Test that horror genre is properly excluded."""
        result = await service.get_situation_aware_recommendations(
            mood="relaxed",
            occasion="alone",
            runtime_preference="flexible",
            excluded_genres=[27]  # Horror
        )
        
        # Check that horror movie is not in recommendations
        horror_ids = [movie["id"] for movie in result["recommendations"] if 27 in movie.get("genre_ids", [])]
        assert len(horror_ids) == 0, "Horror movie should be excluded"
    
    @pytest.mark.asyncio
    async def test_exclude_multiple_genres(self, service):
        """Test excluding multiple genres."""
        result = await service.get_situation_aware_recommendations(
            mood="relaxed",
            occasion="alone",
            runtime_preference="flexible",
            excluded_genres=[27, 28]  # Horror and Action
        )
        
        # Check that horror and action movies are excluded
        for movie in result["recommendations"]:
            genre_ids = movie.get("genre_ids", [])
            assert 27 not in genre_ids, "Horror should be excluded"
            assert 28 not in genre_ids, "Action should be excluded"
    
    @pytest.mark.asyncio
    async def test_no_exclusions(self, service):
        """Test that no movies are excluded when list is empty."""
        result = await service.get_situation_aware_recommendations(
            mood="relaxed",
            occasion="alone",
            runtime_preference="flexible",
            excluded_genres=[]
        )
        
        # All movies should be present
        assert len(result["recommendations"]) > 0


class TestRuntimeFiltering:
    """Test runtime filtering hard constraints."""
    
    @pytest.mark.asyncio
    async def test_under_90_minutes(self, service):
        """Test under_90 runtime preference."""
        result = await service.get_situation_aware_recommendations(
            mood="relaxed",
            occasion="alone",
            runtime_preference="under_90"
        )
        
        # Check that all movies with runtime data are under 90 minutes
        for movie in result["recommendations"]:
            runtime = movie.get("runtime")
            if runtime is not None:  # Only check if runtime available
                assert runtime < 90, f"Movie {movie['title']} runtime {runtime} should be < 90"
    
    @pytest.mark.asyncio
    async def test_90_to_130_minutes(self, service):
        """Test 90_to_130 runtime preference."""
        result = await service.get_situation_aware_recommendations(
            mood="relaxed",
            occasion="alone",
            runtime_preference="90_to_130"
        )
        
        # Check that all movies with runtime data are in range
        for movie in result["recommendations"]:
            runtime = movie.get("runtime")
            if runtime is not None:
                assert 90 <= runtime <= 130, f"Movie {movie['title']} runtime {runtime} should be 90-130"
    
    @pytest.mark.asyncio
    async def test_flexible_runtime(self, service):
        """Test flexible runtime preference accepts all runtimes."""
        result = await service.get_situation_aware_recommendations(
            mood="relaxed",
            occasion="alone",
            runtime_preference="flexible"
        )
        
        # Should include movies of all runtimes
        runtimes = [m.get("runtime") for m in result["recommendations"] if m.get("runtime")]
        assert len(runtimes) > 0
        # Check we have variety (not all the same)
        assert len(set(runtimes)) > 1
    
    @pytest.mark.asyncio
    async def test_missing_runtime_kept(self, service):
        """Test that movies without runtime data are kept in pool."""
        result = await service.get_situation_aware_recommendations(
            mood="relaxed",
            occasion="alone",
            runtime_preference="under_90"
        )
        
        # Movie with ID 7 has no runtime data - it should be included
        movie_ids = [m["id"] for m in result["recommendations"]]
        assert 7 in movie_ids, "Movie without runtime data should be kept"


class TestScoring:
    """Test scoring and ranking logic."""
    
    @pytest.mark.asyncio
    async def test_scores_assigned(self, service):
        """Test that all movies get scored."""
        result = await service.get_situation_aware_recommendations(
            mood="relaxed",
            occasion="alone",
            runtime_preference="flexible"
        )
        
        for movie in result["recommendations"]:
            assert "score" in movie
            assert "score_breakdown" in movie
            assert 0 <= movie["score"] <= 1, "Score should be normalized 0-1"
    
    @pytest.mark.asyncio
    async def test_score_breakdown_components(self, service):
        """Test that score breakdown has all components."""
        result = await service.get_situation_aware_recommendations(
            mood="relaxed",
            occasion="alone",
            runtime_preference="flexible"
        )
        
        movie = result["recommendations"][0]
        breakdown = movie["score_breakdown"]
        
        assert "situation_fit" in breakdown
        assert "quality" in breakdown
        assert "popularity" in breakdown
        
        # All components should be in [0, 1] range
        assert 0 <= breakdown["situation_fit"] <= 1
        assert 0 <= breakdown["quality"] <= 1
        assert 0 <= breakdown["popularity"] <= 1
    
    @pytest.mark.asyncio
    async def test_ranking_order(self, service):
        """Test that movies are ranked in descending score order."""
        result = await service.get_situation_aware_recommendations(
            mood="excited",
            occasion="friends",
            runtime_preference="flexible",
            count=10
        )
        
        scores = [m["score"] for m in result["recommendations"]]
        assert scores == sorted(scores, reverse=True), "Movies should be ranked by score descending"
    
    @pytest.mark.asyncio
    async def test_high_quality_scored_higher(self, service):
        """Test that high-rated movies with many votes score well."""
        result = await service.get_situation_aware_recommendations(
            mood="emotional",
            occasion="alone",
            runtime_preference="flexible"
        )
        
        # Movie 5 (Long Drama) has highest rating (9.0) and most votes (10000)
        # It should score highly despite being long
        movie_5 = next((m for m in result["recommendations"] if m["id"] == 5), None)
        assert movie_5 is not None
        assert movie_5["score_breakdown"]["quality"] > 0.7, "High-quality movie should have high quality score"
    
    @pytest.mark.asyncio
    async def test_mood_affects_scoring(self, service):
        """Test that different moods affect genre preferences."""
        # Get recommendations for "excited" mood
        result_excited = await service.get_situation_aware_recommendations(
            mood="excited",
            occasion="alone",
            runtime_preference="flexible",
            count=5
        )
        
        # Get recommendations for "relaxed" mood
        result_relaxed = await service.get_situation_aware_recommendations(
            mood="relaxed",
            occasion="alone",
            runtime_preference="flexible",
            count=5
        )
        
        # The top results should differ (not identical order)
        excited_ids = [m["id"] for m in result_excited["recommendations"]]
        relaxed_ids = [m["id"] for m in result_relaxed["recommendations"]]
        
        # At least some difference in rankings
        assert excited_ids != relaxed_ids, "Different moods should produce different rankings"


class TestMissingMetadata:
    """Test handling of missing metadata."""
    
    @pytest.mark.asyncio
    async def test_missing_runtime_handled(self, service):
        """Test that movies without runtime are scored appropriately."""
        result = await service.get_situation_aware_recommendations(
            mood="curious",
            occasion="alone",
            runtime_preference="flexible"
        )
        
        # Movie 7 has no runtime
        movie_7 = next((m for m in result["recommendations"] if m["id"] == 7), None)
        assert movie_7 is not None, "Movie without runtime should be included"
        assert "score" in movie_7
    
    @pytest.mark.asyncio
    async def test_missing_ratings_handled(self, service):
        """Test that movies without ratings are scored appropriately."""
        result = await service.get_situation_aware_recommendations(
            mood="curious",
            occasion="alone",
            runtime_preference="flexible"
        )
        
        # Movie 8 has no ratings
        movie_8 = next((m for m in result["recommendations"] if m["id"] == 8), None)
        assert movie_8 is not None, "Movie without ratings should be included"
        assert movie_8["score_breakdown"]["quality"] == 0.3, "Missing ratings should get low quality score"
    
    @pytest.mark.asyncio
    async def test_missing_genres_handled(self, service):
        """Test that movies without genres are scored appropriately when NO exclusions active."""
        result = await service.get_situation_aware_recommendations(
            mood="relaxed",
            occasion="alone",
            runtime_preference="flexible"
            # No excluded_genres - should include movie without genres
        )
        
        # Movie 9 has no genres
        movie_9 = next((m for m in result["recommendations"] if m["id"] == 9), None)
        assert movie_9 is not None, "Movie without genres should be included when no exclusions"
        assert movie_9["score_breakdown"]["situation_fit"] == 0.5, "Missing genres should get neutral score"
    
    @pytest.mark.asyncio
    async def test_missing_genres_excluded_when_exclusions_active(self, service):
        """Test that movies without genre data are excluded when ANY genre exclusion is active."""
        result = await service.get_situation_aware_recommendations(
            mood="relaxed",
            occasion="alone",
            runtime_preference="flexible",
            excluded_genres=[27]  # Exclude horror - should also exclude unknowns
        )
        
        # Movie 9 has no genres - should be EXCLUDED when exclusions are active
        movie_9 = next((m for m in result["recommendations"] if m["id"] == 9), None)
        assert movie_9 is None, "Movie without genre data should be excluded when genre exclusions active (fail-safe)"
    
    @pytest.mark.asyncio
    async def test_all_movies_not_same_score(self, service):
        """Test that missing metadata doesn't make all movies score identically."""
        result = await service.get_situation_aware_recommendations(
            mood="relaxed",
            occasion="alone",
            runtime_preference="flexible"
        )
        
        scores = [m["score"] for m in result["recommendations"]]
        unique_scores = set(scores)
        
        assert len(unique_scores) > 1, "Movies should have different scores"


class TestMatchReasons:
    """Test match reason generation."""
    
    @pytest.mark.asyncio
    async def test_match_reasons_present(self, service):
        """Test that all movies have match reasons."""
        result = await service.get_situation_aware_recommendations(
            mood="relaxed",
            occasion="alone",
            runtime_preference="flexible"
        )
        
        for movie in result["recommendations"]:
            assert "match_reason" in movie
            assert isinstance(movie["match_reason"], str)
            assert len(movie["match_reason"]) > 0
    
    @pytest.mark.asyncio
    async def test_match_reason_metadata_grounded(self, service):
        """Test that match reasons reference actual metadata."""
        result = await service.get_situation_aware_recommendations(
            mood="relaxed",
            occasion="alone",
            runtime_preference="flexible"
        )
        
        # Check a movie with full metadata
        movie_1 = next((m for m in result["recommendations"] if m["id"] == 1), None)
        if movie_1:
            reason = movie_1["match_reason"]
            # Should mention genres, rating, runtime (metadata that exists)
            assert "Genre" in reason or "Rating" in reason or "Runtime" in reason
            # Should not make unsupported claims
            assert "happy ending" not in reason.lower()
            assert "emotional impact" not in reason.lower()


class TestEmptyCandidates:
    """Test handling of empty candidate lists."""
    
    @pytest.mark.asyncio
    async def test_no_candidates_returned(self):
        """Test handling when TMDB returns no candidates."""
        # Create service with empty results
        svc = RecommendationService()
        mock_tmdb = MagicMock()
        
        async def mock_empty_discover(*args, **kwargs):
            return {"results": [], "page": 1, "total_pages": 0}
        
        mock_tmdb.discover_movies = AsyncMock(side_effect=mock_empty_discover)
        svc.tmdb = mock_tmdb
        
        result = await svc.get_situation_aware_recommendations(
            mood="relaxed",
            occasion="alone",
            runtime_preference="flexible"
        )
        
        assert result["recommendations"] == []
        assert result["total_candidates"] == 0
    
    @pytest.mark.asyncio
    async def test_all_filtered_by_constraints(self, service):
        """Test when all candidates are filtered out by hard constraints."""
        result = await service.get_situation_aware_recommendations(
            mood="relaxed",
            occasion="alone",
            runtime_preference="under_90",
            excluded_genres=[16, 27, 28, 35, 53, 10749, 18, 99, 878]  # Exclude almost all
        )
        
        # Should handle gracefully even if few/no results
        assert "recommendations" in result


class TestDeterminism:
    """Test that results are deterministic."""
    
    @pytest.mark.asyncio
    async def test_identical_inputs_identical_outputs(self, service):
        """Test that identical inputs produce identical results."""
        params = {
            "mood": "excited",
            "occasion": "friends",
            "runtime_preference": "90_to_130",
            "excluded_genres": [27]
        }
        
        result1 = await service.get_situation_aware_recommendations(**params)
        result2 = await service.get_situation_aware_recommendations(**params)
        
        # Should get same recommendations in same order
        ids1 = [m["id"] for m in result1["recommendations"]]
        ids2 = [m["id"] for m in result2["recommendations"]]
        
        assert ids1 == ids2, "Identical inputs should produce identical results"
        
        # Scores should also match
        scores1 = [m["score"] for m in result1["recommendations"]]
        scores2 = [m["score"] for m in result2["recommendations"]]
        
        assert scores1 == scores2, "Scores should be deterministic"


class TestTMDBErrors:
    """Test handling of TMDB service errors."""
    
    @pytest.mark.asyncio
    async def test_tmdb_connection_error(self):
        """Test handling when TMDB connection fails."""
        # Create service with error mock
        svc = RecommendationService()
        mock_tmdb = MagicMock()
        mock_tmdb.discover_movies = AsyncMock(side_effect=Exception("Connection failed"))
        svc.tmdb = mock_tmdb
        
        # Should handle gracefully and return empty results
        result = await svc.get_situation_aware_recommendations(
            mood="relaxed",
            occasion="alone",
            runtime_preference="flexible"
        )
        
        assert result["recommendations"] == []
        assert result["total_candidates"] == 0


class TestResponseStructure:
    """Test response structure and metadata."""
    
    @pytest.mark.asyncio
    async def test_response_structure(self, service):
        """Test that response has expected structure."""
        result = await service.get_situation_aware_recommendations(
            mood="relaxed",
            occasion="date",
            runtime_preference="90_to_130",
            excluded_genres=[27],
            count=10
        )
        
        # Top-level keys
        assert "recommendations" in result
        assert "total_candidates" in result
        assert "filtered_count" in result
        assert "situation_context" in result
        assert "scoring_info" in result
        
        # Situation context should echo inputs
        context = result["situation_context"]
        assert context["mood"] == "relaxed"
        assert context["occasion"] == "date"
        assert context["runtime_preference"] == "90_to_130"
        assert context["excluded_genres"] == [27]
    
    @pytest.mark.asyncio
    async def test_recommendation_structure(self, service):
        """Test that each recommendation has expected fields."""
        result = await service.get_situation_aware_recommendations(
            mood="relaxed",
            occasion="alone",
            runtime_preference="flexible"
        )
        
        if result["recommendations"]:
            movie = result["recommendations"][0]
            
            # Should have original TMDB fields
            assert "id" in movie
            assert "title" in movie
            
            # Should have added scoring fields
            assert "score" in movie
            assert "score_breakdown" in movie
            assert "match_reason" in movie


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
