"""
Tests for user preference models (UserPreference, SavedGenrePreference, SavedExclusion).
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from models.user_preferences import (
    UserPreference,
    SavedGenrePreference,
    SavedExclusion,
    PreferenceType
)


class TestSavedGenrePreference:
    """Test suite for SavedGenrePreference model."""
    
    def test_create_genre_preference(self):
        """Test creating a saved genre preference."""
        pref = SavedGenrePreference(
            genre_id=878,
            genre_name="Science Fiction",
            preference_type=PreferenceType.GENRE_LIKE,
            media_type="movie",
            strength=0.8
        )
        
        assert pref.genre_id == 878
        assert pref.genre_name == "Science Fiction"
        assert pref.preference_type == PreferenceType.GENRE_LIKE
        assert pref.media_type == "movie"
        assert pref.strength == 0.8
    
    def test_default_strength(self):
        """Test default strength value."""
        pref = SavedGenrePreference(
            genre_id=878,
            genre_name="Science Fiction",
            preference_type=PreferenceType.GENRE_LIKE,
            media_type="movie"
        )
        
        assert pref.strength == 1.0
    
    def test_invalid_genre_id(self):
        """Test that invalid genre ID is rejected."""
        with pytest.raises(ValidationError):
            SavedGenrePreference(
                genre_id=0,  # Invalid
                genre_name="Test",
                preference_type=PreferenceType.GENRE_LIKE,
                media_type="movie"
            )
    
    def test_invalid_strength(self):
        """Test that invalid strength is rejected."""
        with pytest.raises(ValidationError):
            SavedGenrePreference(
                genre_id=878,
                genre_name="Test",
                preference_type=PreferenceType.GENRE_LIKE,
                media_type="movie",
                strength=1.5  # Max is 1.0
            )
    
    def test_empty_genre_name_rejected(self):
        """Test that empty genre name is rejected."""
        with pytest.raises(ValidationError):
            SavedGenrePreference(
                genre_id=878,
                genre_name="",  # Empty
                preference_type=PreferenceType.GENRE_LIKE,
                media_type="movie"
            )


class TestSavedExclusion:
    """Test suite for SavedExclusion model."""
    
    def test_genre_exclusion(self):
        """Test creating a genre exclusion."""
        exclusion = SavedExclusion(
            exclusion_type="genre",
            exclusion_value="27",
            reason="Too scary"
        )
        
        assert exclusion.exclusion_type == "genre"
        assert exclusion.exclusion_value == "27"
        assert exclusion.reason == "Too scary"
    
    def test_title_exclusion(self):
        """Test creating a title exclusion."""
        exclusion = SavedExclusion(
            exclusion_type="title",
            exclusion_value="12345",
            reason="Already watched"
        )
        
        assert exclusion.exclusion_type == "title"
        assert exclusion.exclusion_value == "12345"
    
    def test_optional_reason(self):
        """Test that reason is optional."""
        exclusion = SavedExclusion(
            exclusion_type="genre",
            exclusion_value="27"
        )
        
        assert exclusion.reason is None


class TestUserPreference:
    """Test suite for UserPreference model."""
    
    def test_create_new_user_preference(self):
        """Test creating a new user preference profile."""
        pref = UserPreference(
            profile_id="user_123"
        )
        
        assert pref.profile_id == "user_123"
        assert pref.liked_genres == []
        assert pref.disliked_genres == []
        assert pref.permanent_exclusions == []
    
    def test_preference_with_liked_genres(self):
        """Test preference with liked genres."""
        pref = UserPreference(
            profile_id="user_123",
            liked_genres=[
                SavedGenrePreference(
                    genre_id=878,
                    genre_name="Science Fiction",
                    preference_type=PreferenceType.GENRE_LIKE,
                    media_type="movie",
                    strength=0.9
                ),
                SavedGenrePreference(
                    genre_id=12,
                    genre_name="Adventure",
                    preference_type=PreferenceType.GENRE_LIKE,
                    media_type="movie",
                    strength=0.8
                )
            ]
        )
        
        assert len(pref.liked_genres) == 2
        assert pref.liked_genres[0].genre_id == 878
        assert pref.liked_genres[1].genre_id == 12
    
    def test_preference_with_disliked_genres(self):
        """Test preference with disliked genres."""
        pref = UserPreference(
            profile_id="user_123",
            disliked_genres=[
                SavedGenrePreference(
                    genre_id=27,
                    genre_name="Horror",
                    preference_type=PreferenceType.GENRE_DISLIKE,
                    media_type="movie",
                    strength=0.9
                )
            ]
        )
        
        assert len(pref.disliked_genres) == 1
        assert pref.disliked_genres[0].genre_id == 27
    
    def test_preference_with_exclusions(self):
        """Test preference with permanent exclusions."""
        pref = UserPreference(
            profile_id="user_123",
            permanent_exclusions=[
                SavedExclusion(
                    exclusion_type="genre",
                    exclusion_value="27",
                    reason="Too scary"
                ),
                SavedExclusion(
                    exclusion_type="title",
                    exclusion_value="12345",
                    reason="Already watched"
                )
            ]
        )
        
        assert len(pref.permanent_exclusions) == 2
        assert pref.permanent_exclusions[0].exclusion_type == "genre"
        assert pref.permanent_exclusions[1].exclusion_type == "title"
    
    def test_preference_with_all_fields(self):
        """Test preference with all fields populated."""
        pref = UserPreference(
            profile_id="user_123",
            liked_genres=[
                SavedGenrePreference(
                    genre_id=878,
                    genre_name="Science Fiction",
                    preference_type=PreferenceType.GENRE_LIKE,
                    media_type="movie"
                )
            ],
            disliked_genres=[
                SavedGenrePreference(
                    genre_id=27,
                    genre_name="Horror",
                    preference_type=PreferenceType.GENRE_DISLIKE,
                    media_type="movie"
                )
            ],
            permanent_exclusions=[
                SavedExclusion(
                    exclusion_type="genre",
                    exclusion_value="27"
                )
            ],
            preferred_language="en",
            preferred_runtime="90_to_130"
        )
        
        assert len(pref.liked_genres) == 1
        assert len(pref.disliked_genres) == 1
        assert len(pref.permanent_exclusions) == 1
        assert pref.preferred_language == "en"
        assert pref.preferred_runtime == "90_to_130"
    
    def test_invalid_profile_id(self):
        """Test that invalid profile ID is rejected."""
        with pytest.raises(ValidationError):
            UserPreference(
                profile_id="user@#$%"  # Invalid characters
            )
    
    def test_empty_profile_id_rejected(self):
        """Test that empty profile ID is rejected."""
        with pytest.raises(ValidationError):
            UserPreference(
                profile_id=""  # Empty
            )
