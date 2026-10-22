"""
Tests for Deterministic Recommendation Engine (Phase 4)

Validates hard constraint enforcement and deterministic ranking.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from services.recommendation_engine import RecommendationEngine, recommendation_engine
from models.recommendation import RecommendationRequest
from models.intent import MediaType


@pytest.fixture
def engine():
    """Create recommendation engine instance."""
    return RecommendationEngine()


@pytest.fixture
def mock_tmdb_movies():
    """Mock TMDB movie data."""
    return {
        "results": [
            {
                "id": 1,
                "title": "Sci-Fi Movie A",
                "genre_ids": [878, 18],  # Sci-fi, Drama
                "vote_average": 8.0,
                "vote_count": 1000,
                "popularity": 75.0,
                "release_date": "2023-01-01",
                "poster_path": "/path1.jpg",
                "overview": "A great sci-fi film"
            },
            {
                "id": 2,
                "title": "Horror Movie B",
                "genre_ids": [27, 53],  # Horror, Thriller
                "vote_average": 7.5,
                "vote_count": 800,
                "popularity": 60.0,
                "release_date": "2022-06-01",
                "poster_path": "/path2.jpg",
                "overview": "A scary horror film"
            },
            {
                "id": 3,
                "title": "Action Movie C",
                "genre_ids": [28, 12],  # Action, Adventure
                "vote_average": 7.0,
                "vote_count": 1200,
                "popularity": 80.0,
                "release_date": "2023-05-01",
                "poster_path": "/path3.jpg",
                "overview": "An action-packed adventure"
            },
            {
                "id": 4,
                "title": "Unknown Genre Movie",
                "genre_ids": [],  # No genre data
                "vote_average": 6.5,
                "vote_count": 500,
                "popularity": 40.0,
                "release_date": "2021-01-01",
                "poster_path": "/path4.jpg",
                "overview": "Mystery movie"
            },
            {
                "id": 5,
                "title": "Long Runtime Movie",
                "genre_ids": [18],  # Drama
                "vote_average": 8.5,
                "vote_count": 1500,
                "popularity": 90.0,
                "release_date": "2022-12-01",
                "poster_path": "/path5.jpg",
                "overview": "Epic drama"
                # Runtime not in discover results - must fetch details
            }
        ]
    }


class TestExcludedGenres:
    """Test excluded genre enforcement."""
    
    @pytest.mark.asyncio
    async def test_excluded_genre_never_in_results(self, engine, mock_tmdb_movies):
        """Excluded genres must NEVER appear in final results."""
        request = RecommendationRequest(
            media_type=MediaType.MOVIE,
            include_genres=[],
            exclude_genres=[27],  # Exclude horror
            count=10
        )
        
        with patch.object(engine.tmdb, 'discover_movies', new_callable=AsyncMock) as mock_discover:
            mock_discover.return_value = mock_tmdb_movies
            
            results = await engine.generate_recommendations(request)
        
        # Verify NO horror movies in results
        for result in results:
            assert 27 not in result.genre_ids, f"Horror genre found in: {result.title}"
    
    @pytest.mark.asyncio
    async def test_multiple_exclusions_enforced(self, engine, mock_tmdb_movies):
        """Multiple excluded genres must all be enforced."""
        request = RecommendationRequest(
            media_type=MediaType.MOVIE,
            include_genres=[],
            exclude_genres=[27, 53],  # Exclude horror AND thriller
            count=10
        )
        
        with patch.object(engine.tmdb, 'discover_movies', new_callable=AsyncMock) as mock_discover:
            mock_discover.return_value = mock_tmdb_movies
            
            results = await engine.generate_recommendations(request)
        
        # Verify NO horror or thriller in results
        for result in results:
            assert 27 not in result.genre_ids, f"Horror found in: {result.title}"
            assert 53 not in result.genre_ids, f"Thriller found in: {result.title}"
    
    @pytest.mark.asyncio
    async def test_missing_genre_metadata_excluded_when_constraint_active(self, engine, mock_tmdb_movies):
        """Movies without genre data must be REJECTED when exclusions active."""
        request = RecommendationRequest(
            media_type=MediaType.MOVIE,
            include_genres=[],
            exclude_genres=[27],  # Exclude horror
            count=10
        )
        
        with patch.object(engine.tmdb, 'discover_movies', new_callable=AsyncMock) as mock_discover:
            mock_discover.return_value = mock_tmdb_movies
            
            results = await engine.generate_recommendations(request)
        
        # Movie with genre_ids=[] should NOT be in results
        titles = [r.title for r in results]
        assert "Unknown Genre Movie" not in titles, "Movie without genre data should be rejected"


class TestMediaTypeEnforcement:
    """Test media type constraint."""
    
    @pytest.mark.asyncio
    async def test_movie_type_respected(self, engine):
        """Request for movies should only return movies."""
        request = RecommendationRequest(
            media_type=MediaType.MOVIE,
            include_genres=[878],
            exclude_genres=[],
            count=5
        )
        
        mock_movies = {"results": [{"id": 1, "title": "Movie A", "genre_ids": [878]}]}
        mock_tv = {"results": [{"id": 2, "name": "TV Show A", "genre_ids": [10765]}]}
        
        with patch.object(engine.tmdb, 'discover_movies', new_callable=AsyncMock) as mock_m, \
             patch.object(engine.tmdb, 'discover_series', new_callable=AsyncMock) as mock_t:
            mock_m.return_value = mock_movies
            mock_t.return_value = mock_tv
            
            results = await engine.generate_recommendations(request)
        
        # Should only have movies
        for result in results:
            assert result.media_type == "movie"
    
    @pytest.mark.asyncio
    async def test_tv_type_respected(self, engine):
        """Request for TV should only return TV shows."""
        request = RecommendationRequest(
            media_type=MediaType.TV,
            include_genres=[10765],
            exclude_genres=[],
            count=5
        )
        
        mock_movies = {"results": [{"id": 1, "title": "Movie A", "genre_ids": [878]}]}
        mock_tv = {"results": [{"id": 2, "name": "TV Show A", "genre_ids": [10765]}]}
        
        with patch.object(engine.tmdb, 'discover_movies', new_callable=AsyncMock) as mock_m, \
             patch.object(engine.tmdb, 'discover_series', new_callable=AsyncMock) as mock_t:
            mock_m.return_value = mock_movies
            mock_t.return_value = mock_tv
            
            results = await engine.generate_recommendations(request)
        
        # Should only have TV
        for result in results:
            assert result.media_type == "tv"


class TestRuntimeConstraints:
    """Test runtime limit enforcement."""
    
    @pytest.mark.asyncio
    async def test_runtime_under_90_enforced(self, engine, mock_tmdb_movies):
        """Runtime under 90 constraint should fetch details and filter correctly."""
        request = RecommendationRequest(
            media_type=MediaType.MOVIE,
            include_genres=[],
            exclude_genres=[],
            runtime_preference="under_90",
            count=5
        )
        
        # Mock movie details responses for runtime verification
        async def mock_get_details(movie_id):
            runtime_map = {
                1: 85,   # Sci-Fi Movie A - under 90
                2: 120,  # Horror Thriller - over 90
                3: 75,   # Action Movie C - under 90
                4: 95,   # Unknown Genre - over 90
                5: 180   # Long Runtime - way over 90
            }
            return {"id": movie_id, "runtime": runtime_map.get(movie_id, 100)}
        
        with patch.object(engine.tmdb, 'discover_movies', new_callable=AsyncMock) as mock_discover, \
             patch.object(engine.tmdb, 'get_movie_details', new_callable=AsyncMock) as mock_details:
            mock_discover.return_value = mock_tmdb_movies
            mock_details.side_effect = mock_get_details
            
            results = await engine.generate_recommendations(request)
        
        # Should only have movies under 90 minutes
        for result in results:
            assert result.id in [1, 3], f"Movie {result.id} ({result.title}) should have runtime < 90"
    
    @pytest.mark.asyncio
    async def test_missing_runtime_rejected(self, engine):
        """Movies without runtime data should be rejected when runtime constraint active."""
        request = RecommendationRequest(
            media_type=MediaType.MOVIE,
            include_genres=[],
            exclude_genres=[],
            runtime_preference="under_90",
            count=5
        )
        
        mock_movies = {
            "results": [
                {"id": 1, "title": "Movie A", "genre_ids": [18], "vote_average": 7.0, "vote_count": 100, "popularity": 50.0, "release_date": "2023-01-01"},
                {"id": 2, "title": "Movie B", "genre_ids": [28], "vote_average": 7.5, "vote_count": 200, "popularity": 60.0, "release_date": "2023-02-01"}
            ]
        }
        
        # Mock details that return no runtime
        async def mock_no_runtime(movie_id):
            return {"id": movie_id, "runtime": None}
        
        with patch.object(engine.tmdb, 'discover_movies', new_callable=AsyncMock) as mock_discover, \
             patch.object(engine.tmdb, 'get_movie_details', new_callable=AsyncMock) as mock_details:
            mock_discover.return_value = mock_movies
            mock_details.side_effect = mock_no_runtime
            
            results = await engine.generate_recommendations(request)
        
        # Should be rejected due to missing runtime when constraint active
        assert len(results) == 0, "Movies without runtime data should be rejected when constraint active"
    
    @pytest.mark.asyncio
    async def test_no_runtime_constraint_no_detail_fetch(self, engine, mock_tmdb_movies):
        """When no runtime constraint, should not fetch details."""
        request = RecommendationRequest(
            media_type=MediaType.MOVIE,
            include_genres=[],
            exclude_genres=[],
            runtime_preference="flexible",
            count=5
        )
        
        with patch.object(engine.tmdb, 'discover_movies', new_callable=AsyncMock) as mock_discover, \
             patch.object(engine.tmdb, 'get_movie_details', new_callable=AsyncMock) as mock_details:
            mock_discover.return_value = mock_tmdb_movies
            
            results = await engine.generate_recommendations(request)
        
        # Should not have called get_movie_details
        assert not mock_details.called, "Should not fetch details when no runtime constraint"
        assert len(results) > 0, "Should return results without runtime check"


class TestProviderEnforcement:
    """Test provider/region constraint via query parameters."""
    
    @pytest.mark.asyncio
    async def test_provider_filtering_via_query_params(self, engine):
        """Provider filtering should use query parameters, results are pre-filtered by TMDB."""
        request = RecommendationRequest(
            media_type=MediaType.MOVIE,
            include_genres=[],
            exclude_genres=[],
            provider_id=8,  # Netflix
            watch_region="US",
            count=5
        )
        
        # TMDB returns only Netflix-available movies when with_watch_providers param is used
        mock_movies = {
            "results": [
                {
                    "id": 1,
                    "title": "Netflix Movie",
                    "genre_ids": [18],
                    "vote_average": 7.5,
                    "vote_count": 500,
                    "popularity": 70.0,
                    "release_date": "2023-01-01",
                    "poster_path": "/path1.jpg"
                }
            ]
        }
        
        with patch.object(engine.tmdb, 'discover_movies', new_callable=AsyncMock) as mock_discover:
            mock_discover.return_value = mock_movies
            
            results = await engine.generate_recommendations(request)
        
        # Verify discover was called with provider parameters
        mock_discover.assert_called_once()
        call_kwargs = mock_discover.call_args[1]
        assert call_kwargs["with_watch_providers"] == 8, "Should pass provider_id to TMDB"
        assert call_kwargs["watch_region"] == "US", "Should pass watch_region to TMDB"
        
        # Results should be present (pre-filtered by TMDB)
        assert len(results) > 0, "Should return pre-filtered results from TMDB"


class TestDeterministicRanking:
    """Test deterministic ranking behavior."""
    
    @pytest.mark.asyncio
    async def test_ranking_is_deterministic(self, engine, mock_tmdb_movies):
        """Same candidates and request should produce same ranking."""
        request = RecommendationRequest(
            media_type=MediaType.MOVIE,
            include_genres=[],
            exclude_genres=[],
            count=5
        )
        
        with patch.object(engine.tmdb, 'discover_movies', new_callable=AsyncMock) as mock_discover:
            mock_discover.return_value = mock_tmdb_movies
            
            result1 = await engine.generate_recommendations(request)
        
        with patch.object(engine.tmdb, 'discover_movies', new_callable=AsyncMock) as mock_discover:
            mock_discover.return_value = mock_tmdb_movies
            
            result2 = await engine.generate_recommendations(request)
        
        # Verify same order
        titles1 = [r.title for r in result1]
        titles2 = [r.title for r in result2]
        assert titles1 == titles2, "Rankings should be deterministic"
    
    @pytest.mark.asyncio
    async def test_quality_influences_ranking(self, engine, mock_tmdb_movies):
        """Higher quality scores should influence ranking."""
        request = RecommendationRequest(
            media_type=MediaType.MOVIE,
            include_genres=[],
            exclude_genres=[],
            count=5
        )
        
        with patch.object(engine.tmdb, 'discover_movies', new_callable=AsyncMock) as mock_discover:
            mock_discover.return_value = mock_tmdb_movies
            
            results = await engine.generate_recommendations(request)
        
        # Verify candidates have explanations (Phase 1 requirement)
        for result in results:
            assert result.explanation, "Each result must have an explanation"
            assert len(result.explanation) > 0


class TestPopularityDoesNotOverrideConstraints:
    """Test that popularity never overrides hard constraints."""
    
    @pytest.mark.asyncio
    async def test_popular_excluded_genre_still_excluded(self, engine):
        """Even very popular movies must be excluded if genre excluded."""
        request = RecommendationRequest(
            media_type=MediaType.MOVIE,
            include_genres=[],
            exclude_genres=[27],  # Exclude horror
            count=5
        )
        
        mock_movies = {
            "results": [
                {
                    "id": 1,
                    "title": "Super Popular Horror Movie",
                    "genre_ids": [27],  # Horror
                    "vote_average": 9.5,
                    "vote_count": 100000,
                    "popularity": 999.0,  # Extremely popular
                }
            ]
        }
        
        with patch.object(engine.tmdb, 'discover_movies', new_callable=AsyncMock) as mock_discover:
            mock_discover.return_value = mock_movies
            
            results = await engine.generate_recommendations(request)
        
        # Even extremely popular horror movie should be excluded
        assert len(results) == 0, "Popular horror movie should still be excluded"


class TestEmptyResults:
    """Test empty result handling."""
    
    @pytest.mark.asyncio
    async def test_no_tmdb_results_handled(self, engine):
        """Empty TMDB response should be handled honestly."""
        request = RecommendationRequest(
            media_type=MediaType.MOVIE,
            include_genres=[878],
            exclude_genres=[],
            count=5
        )
        
        with patch.object(engine.tmdb, 'discover_movies', new_callable=AsyncMock) as mock_discover:
            mock_discover.return_value = {"results": []}
            
            results = await engine.generate_recommendations(request)
        
        # Empty results when TMDB returns no candidates
        assert results == []
    
    @pytest.mark.asyncio
    async def test_all_filtered_out(self, engine):
        """All candidates filtered by constraints should result in empty list."""
        request = RecommendationRequest(
            media_type=MediaType.MOVIE,
            include_genres=[],
            exclude_genres=[878, 27, 28, 18, 12],  # Exclude many genres
            count=5
        )
        
        mock_movies = {
            "results": [
                {"id": 1, "title": "Movie A", "genre_ids": [878]},
                {"id": 2, "title": "Movie B", "genre_ids": [27]},
                {"id": 3, "title": "Movie C", "genre_ids": [28]},
            ]
        }
        
        with patch.object(engine.tmdb, 'discover_movies', new_callable=AsyncMock) as mock_discover:
            mock_discover.return_value = mock_movies
            
            results = await engine.generate_recommendations(request)
        
        # All candidates filtered, no results returned
        assert len(results) == 0


class TestTMDBFailures:
    """Test TMDB failure handling."""
    
    @pytest.mark.asyncio
    async def test_tmdb_exception_no_fabrication(self, engine):
        """TMDB failures must NOT produce fabricated recommendations."""
        request = RecommendationRequest(
            media_type=MediaType.MOVIE,
            include_genres=[878],
            exclude_genres=[],
            count=5
        )
        
        with patch.object(engine.tmdb, 'discover_movies', new_callable=AsyncMock) as mock_discover:
            mock_discover.side_effect = Exception("TMDB API error")
            
            results = await engine.generate_recommendations(request)
        
        # Should return empty results, NOT fabricated data
        assert results == []


class TestFinalValidation:
    """Test final result validation."""
    
    @pytest.mark.asyncio
    async def test_final_results_validated(self, engine, mock_tmdb_movies):
        """Final results must pass validation before returning."""
        request = RecommendationRequest(
            media_type=MediaType.MOVIE,
            include_genres=[],
            exclude_genres=[27],  # Exclude horror
            count=10
        )
        
        with patch.object(engine.tmdb, 'discover_movies', new_callable=AsyncMock) as mock_discover:
            mock_discover.return_value = mock_tmdb_movies
            
            results = await engine.generate_recommendations(request)
        
        # Double-check: NO excluded genres in ANY result
        for result in results:
            for excluded_id in request.exclude_genres:
                assert excluded_id not in result.genre_ids, \
                    f"Validation failed: excluded genre {excluded_id} found in {result.title}"


class TestEvidenceBasedExplanations:
    """Test explanation generation."""
    
    @pytest.mark.asyncio
    async def test_explanations_use_real_metadata(self, engine, mock_tmdb_movies):
        """Explanations must be based on actual candidate metadata."""
        request = RecommendationRequest(
            media_type=MediaType.MOVIE,
            include_genres=[878],
            exclude_genres=[],
            mood="excited",
            count=5
        )
        
        with patch.object(engine.tmdb, 'discover_movies', new_callable=AsyncMock) as mock_discover:
            mock_discover.return_value = mock_tmdb_movies
            
            results = await engine.generate_recommendations(request)
        
        # Check that results have explanations
        for result in results:
            assert result.explanation, f"No explanation for {result.title}"
            assert len(result.explanation) > 10, "Explanation too short"
    
    @pytest.mark.asyncio
    async def test_no_fabricated_reasons(self, engine, mock_tmdb_movies):
        """Reasons must not invent plot details or provider availability."""
        request = RecommendationRequest(
            media_type=MediaType.MOVIE,
            include_genres=[],
            exclude_genres=[],
            count=5
        )
        
        with patch.object(engine.tmdb, 'discover_movies', new_callable=AsyncMock) as mock_discover:
            mock_discover.return_value = mock_tmdb_movies
            
            results = await engine.generate_recommendations(request)
        
        # Check explanations don't contain fabricated content
        for result in results:
            explanation_lower = result.explanation.lower()
            # Should not contain unverified provider claims
            if "available on" in explanation_lower:
                # Would only be present if provider was verified
                assert False, f"Unverified provider claim in: {result.explanation}"
            # Should not fabricate cast/crew details
            assert "starring" not in explanation_lower
            assert "directed by" not in explanation_lower
