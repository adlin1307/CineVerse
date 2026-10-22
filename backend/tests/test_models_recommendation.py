"""
Tests for recommendation models (RecommendationRequest, RecommendationCandidate, RecommendationEvidence, RecommendationResult).
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from models.recommendation import (
    RecommendationRequest,
    RecommendationCandidate,
    RecommendationEvidence,
    RecommendationResult,
    GenreMatch
)
from models.intent import MediaType


class TestRecommendationRequest:
    """Test suite for RecommendationRequest model."""
    
    def test_minimal_request(self):
        """Test creating a minimal recommendation request."""
        request = RecommendationRequest(
            media_type=MediaType.MOVIE
        )
        
        assert request.media_type == MediaType.MOVIE
        assert request.include_genres == []
        assert request.exclude_genres == []
    
    def test_request_with_genre_filters(self):
        """Test request with genre filters."""
        request = RecommendationRequest(
            media_type=MediaType.TV,
            include_genres=[878, 12],
            exclude_genres=[27]
        )
        
        # Note: genres are deduplicated and may be reordered
        assert set(request.include_genres) == {878, 12}
        assert set(request.exclude_genres) == {27}
    
    def test_request_with_provider(self):
        """Test request with provider filter."""
        request = RecommendationRequest(
            media_type=MediaType.BOTH,
            provider_id=8
        )
        
        assert request.provider_id == 8
    
    def test_request_with_year_range(self):
        """Test request with year range."""
        request = RecommendationRequest(
            media_type=MediaType.MOVIE,
            min_year=2010,
            max_year=2020
        )
        
        assert request.min_year == 2010
        assert request.max_year == 2020
    
    def test_invalid_genre_ids(self):
        """Test that invalid genre IDs are rejected."""
        with pytest.raises(ValidationError):
            RecommendationRequest(
                media_type=MediaType.MOVIE,
                include_genres=[0, -1]  # Invalid
            )


class TestGenreMatch:
    """Test suite for GenreMatch model."""
    
    def test_create_genre_match(self):
        """Test creating a genre match."""
        match = GenreMatch(
            genre_id=878,
            genre_name="Science Fiction",
            was_requested=True
        )
        
        assert match.genre_id == 878
        assert match.genre_name == "Science Fiction"
        assert match.was_requested is True


class TestRecommendationEvidence:
    """Test suite for RecommendationEvidence model."""
    
    def test_minimal_evidence(self):
        """Test creating minimal recommendation evidence."""
        evidence = RecommendationEvidence(
            tmdb_id=12345,
            title="Test Movie",
            media_type=MediaType.MOVIE
        )
        
        assert evidence.tmdb_id == 12345
        assert evidence.title == "Test Movie"
        assert evidence.media_type == MediaType.MOVIE
    
    def test_evidence_with_all_fields(self):
        """Test evidence with all fields populated."""
        genre_match = GenreMatch(
            genre_id=878,
            genre_name="Science Fiction",
            was_requested=True
        )
        
        evidence = RecommendationEvidence(
            tmdb_id=78,
            title="Blade Runner",
            media_type=MediaType.MOVIE,
            matched_genres=[genre_match],
            vote_average=8.1,
            release_year=1982,
            overview_excerpt="A blade runner must pursue..."
        )
        
        assert evidence.tmdb_id == 78
        assert evidence.title == "Blade Runner"
        assert len(evidence.matched_genres) == 1
        assert evidence.vote_average == 8.1
        assert evidence.release_year == 1982
    
    def test_evidence_with_invalid_rating(self):
        """Test that invalid vote average is rejected."""
        with pytest.raises(ValidationError):
            RecommendationEvidence(
                tmdb_id=12345,
                title="Test",
                media_type=MediaType.MOVIE,
                vote_average=11.0  # Max is 10.0
            )
    
    def test_evidence_with_invalid_year(self):
        """Test that invalid release year is rejected."""
        with pytest.raises(ValidationError):
            RecommendationEvidence(
                tmdb_id=12345,
                title="Test",
                media_type=MediaType.MOVIE,
                release_year=1800  # Before 1900
            )


class TestRecommendationCandidate:
    """Test suite for RecommendationCandidate model."""
    
    def test_minimal_candidate(self):
        """Test creating a minimal recommendation candidate."""
        evidence = RecommendationEvidence(
            tmdb_id=12345,
            title="Test Movie",
            media_type=MediaType.MOVIE
        )
        
        candidate = RecommendationCandidate(
            evidence=evidence
        )
        
        assert candidate.evidence.tmdb_id == 12345
        assert candidate.evidence.title == "Test Movie"
        assert candidate.relevance_score == 0.0
        assert candidate.quality_score == 0.0
    
    def test_candidate_with_scores(self):
        """Test candidate with scoring information."""
        evidence = RecommendationEvidence(
            tmdb_id=78,
            title="Blade Runner",
            media_type=MediaType.MOVIE
        )
        
        candidate = RecommendationCandidate(
            evidence=evidence,
            relevance_score=0.92,
            quality_score=0.85,
            popularity_score=0.70,
            final_score=0.87,
            rank=1
        )
        
        assert candidate.relevance_score == 0.92
        assert candidate.quality_score == 0.85
        assert candidate.popularity_score == 0.70
        assert candidate.final_score == 0.87
        assert candidate.rank == 1
    
    def test_invalid_score(self):
        """Test that invalid score is rejected."""
        evidence = RecommendationEvidence(
            tmdb_id=12345,
            title="Test",
            media_type=MediaType.MOVIE
        )
        
        with pytest.raises(ValidationError):
            RecommendationCandidate(
                evidence=evidence,
                relevance_score=1.5  # Max is 1.0
            )


class TestRecommendationResult:
    """Test suite for RecommendationResult model."""
    
    def test_minimal_result(self):
        """Test creating a minimal recommendation result."""
        result = RecommendationResult(
            id=12345,
            title="Test Movie",
            media_type="movie",
            explanation="Great sci-fi film"
        )
        
        assert result.id == 12345
        assert result.title == "Test Movie"
        assert result.media_type == "movie"
        assert result.explanation == "Great sci-fi film"
    
    def test_result_with_all_fields(self):
        """Test result with all fields populated."""
        result = RecommendationResult(
            id=78,
            title="Blade Runner",
            media_type="movie",
            poster_path="/poster.jpg",
            vote_average=8.1,
            release_date="1982-06-25",
            genre_ids=[878, 53],
            explanation="Classic dystopian sci-fi — 8.1/10 rating — (1982)"
        )
        
        assert result.genre_ids == [878, 53]
        assert result.vote_average == 8.1
        assert result.release_date == "1982-06-25"
        assert result.poster_path == "/poster.jpg"
    
    def test_empty_explanation_rejected(self):
        """Test that empty explanation is rejected."""
        with pytest.raises(ValidationError):
            RecommendationResult(
                id=12345,
                title="Test",
                media_type="movie",
                explanation=""  # Empty
            )
    
    def test_from_candidate(self):
        """Test creating result from candidate."""
        evidence = RecommendationEvidence(
            tmdb_id=78,
            title="Blade Runner",
            media_type=MediaType.MOVIE,
            vote_average=8.1
        )
        
        candidate = RecommendationCandidate(
            evidence=evidence,
            final_score=0.87
        )
        
        result = RecommendationResult.from_candidate(
            candidate=candidate,
            explanation="Classic sci-fi film"
        )
        
        assert result.id == 78
        assert result.title == "Blade Runner"
        assert result.explanation == "Classic sci-fi film"
