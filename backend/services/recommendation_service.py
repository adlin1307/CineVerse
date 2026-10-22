"""
Situation-aware movie recommendation service.

This service provides transparent, deterministic movie recommendations based on
viewing situation (mood, occasion, runtime preference) without using AI/ML models.

Scoring is broken into independent, testable components:
- Hard constraints (genre exclusions, runtime limits) filter candidates
- Soft scoring ranks remaining candidates using available metadata
"""

from typing import List, Dict, Any, Optional, Tuple
import math
from services.tmdb_service import tmdb_service


# Genre ID mapping for validation and filtering
GENRE_MAP = {
    28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy", 80: "Crime",
    99: "Documentary", 18: "Drama", 10751: "Family", 14: "Fantasy", 36: "History",
    27: "Horror", 10402: "Music", 9648: "Mystery", 10749: "Romance", 878: "Science Fiction",
    10770: "TV Movie", 53: "Thriller", 10752: "War", 37: "Western"
}

# Valid mood values
VALID_MOODS = {"relaxed", "excited", "emotional", "curious"}

# Valid occasion values
VALID_OCCASIONS = {"alone", "friends", "family", "date"}

# Valid runtime preference values
VALID_RUNTIME_PREFS = {"under_90", "90_to_130", "flexible"}


class RecommendationService:
    """
    Service for generating situation-aware movie recommendations.
    
    This service uses TMDB's discover endpoint to fetch candidates and applies
    transparent scoring based on situation fit and quality metrics.
    """
    
    def __init__(self):
        self.tmdb = tmdb_service
    
    async def get_situation_aware_recommendations(
        self,
        mood: str,
        occasion: str,
        runtime_preference: str,
        excluded_genres: Optional[List[int]] = None,
        count: int = 20
    ) -> Dict[str, Any]:
        """
        Get movie recommendations for a specific viewing situation.
        
        Args:
            mood: One of "relaxed", "excited", "emotional", "curious"
            occasion: One of "alone", "friends", "family", "date"
            runtime_preference: One of "under_90", "90_to_130", "flexible"
            excluded_genres: Optional list of genre IDs to exclude
            count: Number of recommendations to return (default 20)
        
        Returns:
            Dict containing:
                - recommendations: List of scored and ranked movies
                - total_candidates: Number of candidates before ranking
                - situation_context: Echo of input parameters
                - scoring_info: Explanation of scoring approach
        
        Raises:
            ValueError: If inputs are invalid
        """
        # Validate inputs
        self._validate_inputs(mood, occasion, runtime_preference, excluded_genres)
        
        # Get candidate movies from TMDB
        candidates = await self._fetch_candidates(
            mood, occasion, runtime_preference, excluded_genres
        )
        
        if not candidates:
            return {
                "recommendations": [],
                "total_candidates": 0,
                "filtered_count": 0,
                "situation_context": {
                    "mood": mood,
                    "occasion": occasion,
                    "runtime_preference": runtime_preference,
                    "excluded_genres": excluded_genres or []
                },
                "scoring_info": "No candidates found matching constraints"
            }
        
        # Apply hard constraints (runtime, genre exclusions)
        filtered = self._apply_hard_constraints(
            candidates, runtime_preference, excluded_genres
        )
        
        # Score and rank remaining candidates
        scored = self._score_candidates(filtered, mood, occasion, runtime_preference)
        
        # Sort by score (descending) and take top N
        ranked = sorted(scored, key=lambda x: x["score"], reverse=True)[:count]
        
        return {
            "recommendations": ranked,
            "total_candidates": len(candidates),
            "filtered_count": len(filtered),
            "situation_context": {
                "mood": mood,
                "occasion": occasion,
                "runtime_preference": runtime_preference,
                "excluded_genres": excluded_genres or []
            },
            "scoring_info": self._get_scoring_explanation()
        }
    
    def _validate_inputs(
        self,
        mood: str,
        occasion: str,
        runtime_preference: str,
        excluded_genres: Optional[List[int]]
    ) -> None:
        """Validate all input parameters."""
        if mood not in VALID_MOODS:
            raise ValueError(
                f"Invalid mood '{mood}'. Must be one of: {', '.join(VALID_MOODS)}"
            )
        
        if occasion not in VALID_OCCASIONS:
            raise ValueError(
                f"Invalid occasion '{occasion}'. Must be one of: {', '.join(VALID_OCCASIONS)}"
            )
        
        if runtime_preference not in VALID_RUNTIME_PREFS:
            raise ValueError(
                f"Invalid runtime_preference '{runtime_preference}'. "
                f"Must be one of: {', '.join(VALID_RUNTIME_PREFS)}"
            )
        
        if excluded_genres:
            invalid_genres = [g for g in excluded_genres if g not in GENRE_MAP]
            if invalid_genres:
                raise ValueError(
                    f"Invalid genre IDs: {invalid_genres}. "
                    f"Valid IDs: {list(GENRE_MAP.keys())}"
                )
    
    async def _fetch_candidates(
        self,
        mood: str,
        occasion: str,
        runtime_preference: str,
        excluded_genres: Optional[List[int]]
    ) -> List[Dict[str, Any]]:
        """
        Fetch candidate movies from TMDB discover endpoint.
        
        Uses mood and occasion to suggest genre preferences, but applies them
        as soft preferences in scoring rather than hard filters (except for
        excluded genres which are hard constraints).
        """
        # Fetch multiple pages to get diverse candidates
        all_results = []
        for page in range(1, 4):  # Fetch 3 pages (~60 movies)
            try:
                data = await self.tmdb.discover_movies(
                    page=page,
                    sort_by="popularity.desc"
                )
                all_results.extend(data.get("results", []))
            except Exception as e:
                # Log error but continue with what we have
                print(f"[Warning] Failed to fetch page {page}: {e}")
                break
        
        return all_results
    
    def _apply_hard_constraints(
        self,
        candidates: List[Dict[str, Any]],
        runtime_preference: str,
        excluded_genres: Optional[List[int]]
    ) -> List[Dict[str, Any]]:
        """
        Apply hard constraints: runtime limits and genre exclusions.
        
        Genre Exclusion Behavior:
        - When excluded_genres is provided:
          * Movies WITH genre_ids: Check if any excluded genre matches
          * Movies WITHOUT genre_ids or with empty list: EXCLUDE (fail-safe)
          * Rationale: If user excludes horror, we must not show unknown movies
                      that could be horror. Conservative = exclude unknowns.
        - When excluded_genres is None/empty: Include all movies regardless
        
        Runtime Filtering Behavior:
        - Only applies when runtime metadata is available
        - Movies without runtime data are KEPT (conservative for optional filter)
        """
        filtered = []
        
        for movie in candidates:
            # Genre exclusion (hard constraint)
            if excluded_genres:
                genre_ids = movie.get("genre_ids", [])
                
                # If movie has no genre data when exclusions are active, exclude it
                # (fail-safe: don't show unknown content when user has preferences)
                if not genre_ids:  # Covers None, [], missing field
                    continue
                
                # Check if any excluded genre matches
                if any(genre_id in excluded_genres for genre_id in genre_ids):
                    continue  # Skip this movie
            
            # Runtime constraint (hard constraint when metadata available)
            runtime = movie.get("runtime")
            if runtime is not None:  # Only apply if runtime data exists
                if runtime_preference == "under_90" and runtime >= 90:
                    continue
                elif runtime_preference == "90_to_130" and not (90 <= runtime <= 130):
                    continue
                # "flexible" accepts any runtime
            # If runtime is None, we keep the movie (conservative for optional filter)
            
            filtered.append(movie)
        
        return filtered
    
    def _score_candidates(
        self,
        candidates: List[Dict[str, Any]],
        mood: str,
        occasion: str,
        runtime_preference: str
    ) -> List[Dict[str, Any]]:
        """
        Score each candidate using transparent, metadata-based components.
        
        Scoring formula (initial heuristic weights):
            final_score = (0.40 * situation_fit) + (0.40 * quality) + (0.20 * popularity)
        
        Components:
        - situation_fit: How well genres match the mood/occasion
        - quality: Based on vote_average and vote_count
        - popularity: TMDB popularity score (normalized)
        
        All components are [0, 1] normalized for stable weighting.
        """
        scored = []
        
        for movie in candidates:
            situation_score = self._calculate_situation_fit(movie, mood, occasion)
            quality_score = self._calculate_quality_score(movie)
            popularity_score = self._calculate_popularity_score(movie)
            
            # Weighted combination (documented heuristic weights)
            final_score = (
                0.40 * situation_score +
                0.40 * quality_score +
                0.20 * popularity_score
            )
            
            scored_movie = {
                **movie,
                "score": round(final_score, 4),
                "score_breakdown": {
                    "situation_fit": round(situation_score, 4),
                    "quality": round(quality_score, 4),
                    "popularity": round(popularity_score, 4),
                },
                "match_reason": self._generate_match_reason(movie, mood, occasion)
            }
            
            scored.append(scored_movie)
        
        return scored
    
    def _calculate_situation_fit(
        self,
        movie: Dict[str, Any],
        mood: str,
        occasion: str
    ) -> float:
        """
        Calculate how well movie genres match the situation.
        
        Returns: 0.0 to 1.0 score based on genre overlap with situation preferences.
        
        Genre preferences (initial heuristic mapping):
        - relaxed: Comedy, Documentary, Romance
        - excited: Action, Thriller, Adventure
        - emotional: Drama, Romance
        - curious: Mystery, Science Fiction, Documentary
        
        - alone: Any genre (no preference)
        - friends: Comedy, Action, Thriller
        - family: Animation, Family, Adventure
        - date: Romance, Comedy, Drama
        
        If genre metadata is missing, returns neutral 0.5 score.
        """
        genre_ids = movie.get("genre_ids", [])
        if not genre_ids:
            return 0.5  # Neutral score when metadata missing
        
        # Map mood to preferred genres
        mood_genres = {
            "relaxed": [35, 99, 10749],  # Comedy, Documentary, Romance
            "excited": [28, 53, 12],     # Action, Thriller, Adventure
            "emotional": [18, 10749],    # Drama, Romance
            "curious": [9648, 878, 99],  # Mystery, Sci-Fi, Documentary
        }
        
        # Map occasion to preferred genres
        occasion_genres = {
            "alone": [],  # No specific preference
            "friends": [35, 28, 53],     # Comedy, Action, Thriller
            "family": [16, 10751, 12],   # Animation, Family, Adventure
            "date": [10749, 35, 18],     # Romance, Comedy, Drama
        }
        
        preferred = set(mood_genres.get(mood, []) + occasion_genres.get(occasion, []))
        
        if not preferred:
            return 0.5  # Neutral when no preferences
        
        # Calculate overlap
        matches = len(set(genre_ids) & preferred)
        max_possible = min(len(genre_ids), len(preferred))
        
        if max_possible == 0:
            return 0.5
        
        return matches / max_possible
    
    def _calculate_quality_score(self, movie: Dict[str, Any]) -> float:
        """
        Calculate quality score based on vote_average and vote_count.
        
        Returns: 0.0 to 1.0 normalized score.
        
        Formula:
            rating_component = vote_average / 10
            confidence = min(1.0, vote_count / 1000)
            quality_score = rating_component * confidence
        
        This penalizes movies with few votes even if rating is high,
        and rewards movies with both high ratings and many votes.
        
        If vote data is missing, returns 0.3 (low but non-zero).
        """
        vote_average = movie.get("vote_average")
        vote_count = movie.get("vote_count")
        
        if vote_average is None or vote_count is None:
            return 0.3  # Low score for missing quality data
        
        # Normalize rating to [0, 1]
        rating_component = vote_average / 10.0
        
        # Confidence based on vote count (reaches 1.0 at 1000 votes)
        confidence = min(1.0, vote_count / 1000.0)
        
        return rating_component * confidence
    
    def _calculate_popularity_score(self, movie: Dict[str, Any]) -> float:
        """
        Normalize TMDB popularity score.
        
        Returns: 0.0 to 1.0 score using logarithmic scaling.
        
        TMDB popularity ranges widely (0 to 1000+). We use log scaling
        to compress the range while preserving relative differences.
        
        Formula: min(1.0, log(popularity + 1) / 8)
        
        If popularity missing, returns 0.5 (neutral).
        """
        popularity = movie.get("popularity")
        
        if popularity is None or popularity <= 0:
            return 0.5  # Neutral score
        
        # Log scale to normalize (log(3000) ≈ 8)
        normalized = math.log(popularity + 1) / 8.0
        return min(1.0, normalized)
    
    def _generate_match_reason(
        self,
        movie: Dict[str, Any],
        mood: str,
        occasion: str
    ) -> str:
        """
        Generate a transparent match reason based on available metadata.
        
        IMPORTANT: Only makes claims that can be verified from metadata.
        Does not invent attributes or claim subjective qualities.
        """
        reasons = []
        
        # Genre-based reasoning
        genre_ids = movie.get("genre_ids", [])
        if genre_ids:
            genre_names = [GENRE_MAP.get(gid, "Unknown") for gid in genre_ids[:2]]
            reasons.append(f"Genres: {', '.join(genre_names)}")
        
        # Rating-based reasoning
        vote_average = movie.get("vote_average")
        vote_count = movie.get("vote_count")
        if vote_average and vote_count:
            reasons.append(f"Rating: {vote_average:.1f}/10 ({vote_count:,} votes)")
        
        # Runtime information (if available)
        runtime = movie.get("runtime")
        if runtime:
            reasons.append(f"Runtime: {runtime} min")
        
        if not reasons:
            return "Match based on general popularity"
        
        return " | ".join(reasons)
    
    def _get_scoring_explanation(self) -> str:
        """Return explanation of scoring methodology."""
        return (
            "Scoring: 40% situation fit (genre match to mood/occasion) + "
            "40% quality (rating × vote confidence) + "
            "20% popularity (normalized TMDB score). "
            "Weights are initial heuristics and may be refined."
        )


# Singleton instance
recommendation_service = RecommendationService()
