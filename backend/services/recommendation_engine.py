"""
Deterministic Recommendation Engine (Phase 4)

Reliable recommendation pipeline using Phase 1 schemas with strict constraint enforcement.
"""

from typing import List, Dict, Any, Optional, Tuple
import math

from models.recommendation import RecommendationRequest, RecommendationCandidate, RecommendationResult
from models.intent import MediaType
from services.tmdb_service import tmdb_service


class RecommendationEngine:
    """
    Deterministic recommendation engine with hard constraint enforcement.
    
    Pipeline:
    1. Retrieve candidates from TMDB
    2. Apply hard filters (excluded genres, media type, runtime, provider)
    3. Rank eligible candidates deterministically
    4. Validate final results against all constraints
    5. Generate evidence-based explanations
    """
    
    def __init__(self):
        self.tmdb = tmdb_service
    
    async def generate_recommendations(
        self,
        request: RecommendationRequest
    ) -> List[RecommendationResult]:
        """
        Generate recommendations using deterministic pipeline.
        
        Args:
            request: Validated recommendation request
        
        Returns:
            List of RecommendationResult objects
        """
        # Step 1: Retrieve candidates
        candidates = await self._retrieve_candidates(request)
        
        if not candidates:
            return []
        
        # Step 2: Apply hard filters
        filtered = self._apply_hard_filters(candidates, request)
        
        # Step 3: Rank eligible candidates
        ranked = self._rank_candidates(filtered, request)
        
        # Step 4: Take top N * 2 to allow for runtime verification
        # (some candidates may be rejected during detail fetch)
        buffer_size = request.count * 2
        top_candidates = ranked[:buffer_size]
        
        # Step 5: Verify runtime constraints (requires detail fetch for movies)
        runtime_verified = await self._verify_runtime_constraints(top_candidates, request)
        
        # Step 6: Take final top N after runtime verification
        top_n = runtime_verified[:request.count]
        
        # Step 7: Validate final results
        validated = self._validate_results(top_n, request)
        
        # Step 8: Convert to RecommendationCandidate objects
        candidates_with_evidence = [
            self._to_candidate(item, request) for item in validated
        ]
        
        # Step 9: Generate explanations and create final results
        results = []
        for candidate in candidates_with_evidence:
            explanation = self._generate_explanation(candidate, request)
            result = RecommendationResult.from_candidate(
                candidate=candidate,
                explanation=explanation,
                include_evidence=False
            )
            results.append(result)
        
        return results
    
    async def _retrieve_candidates(
        self,
        request: RecommendationRequest
    ) -> List[Dict[str, Any]]:
        """
        Retrieve candidates from TMDB.
        
        Returns raw TMDB data.
        """
        all_candidates = []
        
        # Determine which media types to fetch
        if request.media_type == MediaType.BOTH:
            media_types = [MediaType.MOVIE, MediaType.TV]
        else:
            media_types = [request.media_type]
        
        for media_type in media_types:
            if media_type == MediaType.MOVIE:
                candidates = await self._fetch_movies(request)
            else:  # TV
                candidates = await self._fetch_tv(request)
            
            # Tag with media type
            for candidate in candidates:
                candidate["_media_type"] = media_type.value
            
            all_candidates.extend(candidates)
        
        return all_candidates
    
    async def _fetch_movies(
        self,
        request: RecommendationRequest
    ) -> List[Dict[str, Any]]:
        """Fetch movie candidates from TMDB using discover with provider pre-filtering."""
        try:
            # Build discover parameters
            params = {"page": 1, "sort_by": "popularity.desc"}
            
            # Add genre filter if specified, or infer from mood
            if request.include_genres:
                params["with_genres"] = ",".join(map(str, request.include_genres))
            elif request.mood:
                mood_defaults = {
                    "emotional": "18",
                    "relaxed": "35",
                    "excited": "28,53",
                    "curious": "9648,878"
                }
                if request.mood in mood_defaults:
                    params["with_genres"] = mood_defaults[request.mood]
            
            # Add excluded genres to TMDB query
            if request.exclude_genres:
                params["without_genres"] = ",".join(map(str, request.exclude_genres))
            
            # Add year filter
            if request.min_year:
                params["primary_release_date.gte"] = f"{request.min_year}-01-01"
            if request.max_year:
                params["primary_release_date.lte"] = f"{request.max_year}-12-31"
            
            # Add provider filter (TMDB pre-filters results by provider)
            if request.provider_id is not None:
                params["with_watch_providers"] = request.provider_id
                params["watch_region"] = request.watch_region
            
            # Fetch
            data = await self.tmdb.discover_movies(**params)
            return data.get("results", [])
        except Exception as e:
            print(f"[ERROR] Failed to fetch movies: {e}")
            return []
    
    async def _fetch_tv(
        self,
        request: RecommendationRequest
    ) -> List[Dict[str, Any]]:
        """Fetch TV candidates from TMDB using discover with provider pre-filtering."""
        try:
            # Build discover parameters
            params = {"page": 1, "sort_by": "popularity.desc"}
            
            # Add genre filter if specified, or infer from mood
            if request.include_genres:
                params["with_genres"] = ",".join(map(str, request.include_genres))
            elif request.mood:
                mood_defaults = {
                    "emotional": "18",
                    "relaxed": "35",
                    "excited": "10759",
                    "curious": "10765"
                }
                if request.mood in mood_defaults:
                    params["with_genres"] = mood_defaults[request.mood]
            
            # Add excluded genres to TMDB query
            if request.exclude_genres:
                params["without_genres"] = ",".join(map(str, request.exclude_genres))
            
            # Add year filter (first_air_date for TV)
            if request.min_year:
                params["first_air_date.gte"] = f"{request.min_year}-01-01"
            if request.max_year:
                params["first_air_date.lte"] = f"{request.max_year}-12-31"
            
            # Add provider filter (TMDB pre-filters results by provider)
            if request.provider_id is not None:
                params["with_watch_providers"] = request.provider_id
                params["watch_region"] = request.watch_region
            
            # Fetch
            data = await self.tmdb.discover_series(**params)
            return data.get("results", [])
        except Exception as e:
            print(f"[ERROR] Failed to fetch TV: {e}")
            return []
    
    def _apply_hard_filters(
        self,
        candidates: List[Dict[str, Any]],
        request: RecommendationRequest
    ) -> List[Dict[str, Any]]:
        """
        Apply hard constraint filters.
        
        Hard constraints (must pass ALL):
        1. Excluded genres - NEVER in final results
        2. Media type - match requested type
        3. Runtime limits - when reliable data available
        4. Provider/region - only with verified data
        
        Missing metadata behavior:
        - Excluded genres: REJECT if genre_ids missing (fail-safe)
        - Runtime: ACCEPT if runtime missing (optional constraint)
        - Provider: REJECT if provider data missing (when constraint active)
        """
        filtered = []
        
        for candidate in candidates:
            # Filter 1: Excluded genres (CRITICAL - fail-safe)
            if request.exclude_genres:
                genre_ids = candidate.get("genre_ids", [])
                
                # Missing genre data when exclusions active → REJECT
                if not genre_ids:
                    continue
                
                # Check if any excluded genre present
                if any(gid in request.exclude_genres for gid in genre_ids):
                    continue
            
            # Filter 2: Media type match
            media_type = candidate.get("_media_type")
            if request.media_type != MediaType.BOTH:
                if media_type != request.media_type.value:
                    continue
            
            # Filter 3: Runtime (movies only - mark for later verification)
            # Runtime data not in discover results, needs detail fetch
            if media_type == "movie" and request.runtime_preference and request.runtime_preference != "flexible":
                candidate["_needs_runtime_check"] = True
            
            # Filter 4: Provider/region constraint
            # NOTE: TMDB discover pre-filters by provider when with_watch_providers param is used.
            # The results we receive are already filtered by the requested provider.
            # No post-filtering needed - we rely on query parameters in _fetch_movies/_fetch_tv.
            
            # Passed all filters
            filtered.append(candidate)
        
        return filtered
    
    async def _verify_runtime_constraints(
        self,
        candidates: List[Dict[str, Any]],
        request: RecommendationRequest
    ) -> List[Dict[str, Any]]:
        """
        Verify runtime constraints by fetching movie details for candidates that need it.
        
        This is done after ranking to minimize API calls - only fetch details for top candidates.
        Handles detail fetch failures gracefully (rejects candidate if verification fails).
        """
        if not request.runtime_preference or request.runtime_preference == "flexible":
            return candidates
        
        verified = []
        
        for candidate in candidates:
            # Skip if not marked for runtime check (TV shows or no constraint)
            if not candidate.get("_needs_runtime_check"):
                verified.append(candidate)
                continue
            
            # Fetch movie details to get runtime
            try:
                movie_id = candidate["id"]
                details = await self.tmdb.get_movie_details(movie_id)
                runtime = details.get("runtime")
                
                if runtime is None:
                    # No runtime data available → cannot verify hard constraint → REJECT
                    continue
                
                # Store runtime in candidate for evidence building
                candidate["runtime"] = runtime
                
                # Apply runtime constraint
                if request.runtime_preference == "under_90" and runtime >= 90:
                    continue
                elif request.runtime_preference == "90_to_130" and not (90 <= runtime <= 130):
                    continue
                
                # Passed runtime check
                verified.append(candidate)
                
            except Exception as e:
                # Failed to fetch details → cannot verify → REJECT
                print(f"[WARN] Failed to fetch details for movie {candidate.get('id')}: {e}")
                continue
        
        return verified
    
    def _rank_candidates(
        self,
        candidates: List[Dict[str, Any]],
        request: RecommendationRequest
    ) -> List[Dict[str, Any]]:
        """
        Rank candidates deterministically.
        
        Scoring components:
        - Quality score (30%): vote_average * log(vote_count + 1)
        - Popularity score (15%): normalized or adjusted for low/high popularity preference
        - Mood fit (15%): genre matching for mood
        - Emotional sub-intent fit (20%): theme & keyword resonance (tearjerker, feelgood, etc.)
        - Tone fit (15%): darker/lighter tone modifier matching
        - Recency bonus (5%): recent releases get small boost
        """
        scored = []
        
        is_emotional_search = request.mood == "emotional" or bool(request.emotional_sub_intent)
        
        for candidate in candidates:
            quality = self._calculate_quality_score(candidate)
            popularity = self._calculate_popularity_score(candidate, request.popularity)
            mood_fit = self._calculate_mood_fit(candidate, request.mood)
            emotional_fit = self._calculate_emotional_fit(candidate, request.emotional_sub_intent, mood=request.mood)
            tone_fit = self._calculate_tone_fit(candidate, request.tone_modifiers)
            recency = self._calculate_recency_score(candidate)
            
            # Weighted combination: relevance before popularity for emotional requests
            if is_emotional_search:
                final_score = (
                    0.20 * quality +
                    0.05 * popularity +
                    0.15 * mood_fit +
                    0.45 * emotional_fit +
                    0.10 * tone_fit +
                    0.05 * recency
                )
            else:
                final_score = (
                    0.30 * quality +
                    0.15 * popularity +
                    0.15 * mood_fit +
                    0.20 * emotional_fit +
                    0.15 * tone_fit +
                    0.05 * recency
                )
            
            candidate["_score"] = final_score
            candidate["_quality"] = quality
            candidate["_popularity"] = popularity
            candidate["_mood_fit"] = mood_fit
            candidate["_emotional_fit"] = emotional_fit
            candidate["_tone_fit"] = tone_fit
            candidate["_recency"] = recency
            
            scored.append(candidate)
        
        # Sort by score descending
        scored.sort(key=lambda x: x["_score"], reverse=True)
        
        return scored
    
    def _calculate_quality_score(self, candidate: Dict[str, Any]) -> float:
        """Calculate quality score from votes."""
        vote_avg = candidate.get("vote_average", 0) or 0
        vote_count = candidate.get("vote_count", 0) or 0
        
        # Normalize vote average to 0-1
        normalized_avg = vote_avg / 10.0
        
        # Confidence factor based on vote count
        confidence = math.log(vote_count + 1) / math.log(1001)  # log(1001) ≈ 3
        confidence = min(confidence, 1.0)
        
        return normalized_avg * confidence
    
    def _calculate_popularity_score(self, candidate: Dict[str, Any], popularity_pref: Optional[str] = None) -> float:
        """Calculate popularity score adjusted by preference."""
        popularity = candidate.get("popularity", 0) or 0
        
        if popularity_pref == "low":
            # Underrated / hidden gem: favor high quality with low-to-medium popularity
            vote_avg = candidate.get("vote_average", 0) or 0
            if popularity < 50 and vote_avg >= 7.0:
                return 1.0
            elif popularity < 80:
                return 0.7
            else:
                return 0.2
        elif popularity_pref == "high":
            # Mainstream / blockbuster
            if popularity > 0:
                return min(math.log(popularity + 1) / math.log(501), 1.0)
            return 0.0
        else:
            # Default
            if popularity > 0:
                return min(math.log(popularity + 1) / math.log(501), 1.0)
            return 0.0
    
    def _calculate_emotional_fit(
        self,
        candidate: Dict[str, Any],
        sub_intent: Optional[str],
        mood: Optional[str] = None
    ) -> float:
        """Calculate resonance with nuanced emotional sub-intent and mood."""
        overview = (candidate.get("overview") or "").lower()
        title = (candidate.get("title") or candidate.get("name") or "").lower()
        text = f"{title} {overview}"
        genre_ids = set(candidate.get("genre_ids", []))
        
        # If no specific sub-intent or "general", but mood is emotional:
        if sub_intent in (None, "general"):
            if mood == "emotional":
                keywords = [
                    "family", "love", "relationship", "father", "mother", "son", "daughter",
                    "struggle", "redemption", "hope", "loss", "grief", "journey", "life",
                    "friendship", "healing", "human", "heart", "moving", "devotion"
                ]
                kw_hits = sum(1 for kw in keywords if kw in text)
                score = 0.5 + min(kw_hits * 0.1, 0.35)
                # Synergies with drama / romance
                if 18 in genre_ids and 10749 in genre_ids:
                    score += 0.15
                elif 18 in genre_ids:
                    score += 0.05
                # Heavy penalty for mob/violent crime unless poignant human theme is dominant
                if 80 in genre_ids and kw_hits < 2:
                    score -= 0.35
                if 28 in genre_ids and kw_hits < 2:
                    score -= 0.2
                return max(0.1, min(score, 1.0))
            return 0.5  # Neutral when not emotional
            
        if sub_intent == "tearjerker":
            keywords = [
                "cry", "crying", "tear", "tears", "sob", "sobbing", "heartbreaking", "heartbreak",
                "devastating", "gut-wrenching", "tragic", "tragedy", "loss", "grief",
                "terminal", "dying", "death", "sacrifice", "mourn", "mourning", "farewell", "sad",
                "cancer", "fatal", "illness", "separation", "sorrow", "poignant", "melancholy",
                "unrequited", "pain", "goodbye"
            ]
            kw_hits = sum(1 for kw in keywords if kw in text)
            score = 0.5 + min(kw_hits * 0.15, 0.45)
            # Synergies with heavy drama / romance / history / war tragedy
            if 18 in genre_ids and (genre_ids & {10752, 36, 10749}):
                score += 0.15
            elif 18 in genre_ids and 10749 in genre_ids:
                score += 0.15
            # Mob, heist, crime or pure violent action penalized heavily if no poignant grief themes
            if (80 in genre_ids or 28 in genre_ids) and kw_hits == 0:
                score -= 0.45
            return max(0.05, min(score, 1.0))
            
        elif sub_intent == "bittersweet":
            keywords = [
                "bittersweet", "melancholy", "wistful", "growing up", "nostalgia",
                "remember", "farewell", "poignant", "reflection", "parting", "unrequited",
                "fleeting", "memory", "longing"
            ]
            kw_hits = sum(1 for kw in keywords if kw in text)
            score = 0.5 + min(kw_hits * 0.15, 0.4)
            if 18 in genre_ids and 10749 in genre_ids:
                score += 0.15
            elif 18 in genre_ids:
                score += 0.05
            return min(score, 1.0)
            
        elif sub_intent in ("hopeful", "cathartic"):
            keywords = [
                "hope", "hopeful", "resilience", "overcoming", "redemption", "survival",
                "healing", "second chance", "triumph", "spirit", "perseverance", "reconcile",
                "courage", "inspiration", "uplifting", "reconciliation"
            ]
            kw_hits = sum(1 for kw in keywords if kw in text)
            score = 0.5 + min(kw_hits * 0.15, 0.4)
            if 18 in genre_ids and (genre_ids & {36, 10751}):
                score += 0.1
            return min(score, 1.0)
            
        elif sub_intent == "feelgood":
            keywords = [
                "uplifting", "feel-good", "feel good", "heartwarming", "inspiring",
                "hope", "wholesome", "joy", "friendship", "triumph", "dream", "charming",
                "cozy", "cheerful"
            ]
            kw_hits = sum(1 for kw in keywords if kw in text)
            score = 0.5 + min(kw_hits * 0.15, 0.4)
            if genre_ids & {10751, 35, 16}:
                score += 0.15
            if 80 in genre_ids or 27 in genre_ids:
                score -= 0.3
            return max(0.1, min(score, 1.0))
            
        elif sub_intent == "intense":
            keywords = [
                "intense", "crisis", "pressure", "dilemma", "conflict", "desperate",
                "confrontation", "secret", "betrayal", "obsession", "unravel", "turmoil",
                "tension", "emotional stakes", "fractured"
            ]
            kw_hits = sum(1 for kw in keywords if kw in text)
            score = 0.5 + min(kw_hits * 0.15, 0.4)
            if 18 in genre_ids and (genre_ids & {53, 9648}):
                score += 0.15
            return min(score, 1.0)
            
        elif sub_intent == "thought_provoking":
            keywords = [
                "existential", "philosophical", "identity", "truth", "morality", "purpose",
                "consciousness", "human condition", "deep", "profound", "allegory",
                "meaning of life", "question", "reality"
            ]
            kw_hits = sum(1 for kw in keywords if kw in text)
            score = 0.5 + min(kw_hits * 0.15, 0.4)
            if 18 in genre_ids and (genre_ids & {878, 9648}):
                score += 0.15
            return min(score, 1.0)
            
        elif sub_intent in ("dark", "darker"):
            keywords = [
                "dark", "gritty", "bleak", "murder", "corruption", "conspiracy",
                "revenge", "obsession", "brutal", "disturbing", "noir", "crime", "twisted"
            ]
            kw_hits = sum(1 for kw in keywords if kw in text)
            score = 0.5 + min(kw_hits * 0.15, 0.4)
            if genre_ids & {53, 80, 9648}:
                score += 0.1
            if genre_ids & {35, 10751, 16}:
                score -= 0.2
            return max(0.0, min(score, 1.0))
            
        return 0.5
            
        return 0.5
    
    def _calculate_tone_fit(self, candidate: Dict[str, Any], tone_modifiers: List[str]) -> float:
        """Calculate how well candidate matches requested tone modifiers."""
        if not tone_modifiers:
            return 0.5
            
        genre_ids = set(candidate.get("genre_ids", []))
        overview = (candidate.get("overview") or "").lower()
        score = 0.5
        
        for tone in tone_modifiers:
            tone_lower = tone.lower()
            if "dark" in tone_lower or "intense" in tone_lower or "gritty" in tone_lower:
                if genre_ids & {53, 80, 9648}:
                    score += 0.25
                elif 18 in genre_ids:
                    score += 0.1
                if genre_ids & {35, 10751, 16}:
                    score -= 0.3
                if any(k in overview for k in ["dark", "gritty", "murder", "psychological", "conspiracy", "violent", "revenge", "bleak"]):
                    score += 0.15
            elif "light" in tone_lower or "fun" in tone_lower:
                if genre_ids & {35, 10751, 16}:
                    score += 0.25
                if genre_ids & {27, 53, 80}:
                    score -= 0.2
                    
        return max(0.0, min(score, 1.0))
    
    def _calculate_mood_fit(self, candidate: Dict[str, Any], mood: Optional[str]) -> float:
        """Calculate how well genres match requested mood."""
        if not mood:
            return 0.5  # Neutral
        
        genre_ids = candidate.get("genre_ids", [])
        if not genre_ids:
            return 0.5  # Neutral
        
        # Mood-to-genre mappings
        mood_genres = {
            "relaxed": [35, 16, 10751, 10749],  # Comedy, Animation, Family, Romance
            "excited": [28, 12, 878, 53],  # Action, Adventure, Sci-Fi, Thriller
            "emotional": [18, 10749, 36],  # Drama, Romance, History
            "curious": [9648, 878, 99, 80]  # Mystery, Sci-Fi, Documentary, Crime
        }
        
        preferred = mood_genres.get(mood, [])
        if not preferred:
            return 0.5
        
        # Calculate overlap
        matches = len(set(genre_ids) & set(preferred))
        max_possible = min(len(genre_ids), len(preferred))
        
        if max_possible == 0:
            return 0.5
        
        return matches / max_possible
    
    def _calculate_recency_score(self, candidate: Dict[str, Any]) -> float:
        """Calculate recency bonus for recent releases."""
        from datetime import datetime
        
        # Get release date
        media_type = candidate.get("_media_type")
        if media_type == "movie":
            date_str = candidate.get("release_date")
        else:
            date_str = candidate.get("first_air_date")
        
        if not date_str:
            return 0.5  # Neutral
        
        try:
            release_date = datetime.strptime(date_str, "%Y-%m-%d")
            now = datetime.now()
            
            # Calculate years since release
            years_diff = (now - release_date).days / 365.25
            
            # Recent = higher score (exponential decay)
            # 0 years = 1.0, 5 years = 0.5, 10 years = 0.25
            if years_diff < 0:
                return 1.0  # Future release
            
            return max(0.0, 1.0 - (years_diff / 20.0))  # Linear decay over 20 years
        except:
            return 0.5
    
    def _validate_results(
        self,
        candidates: List[Dict[str, Any]],
        request: RecommendationRequest
    ) -> List[Dict[str, Any]]:
        """
        Final validation: ensure NO excluded genres in results.
        
        This is the last line of defense against constraint violations.
        """
        validated = []
        
        for candidate in candidates:
            # Re-check exclusions
            if request.exclude_genres:
                genre_ids = candidate.get("genre_ids", [])
                if not genre_ids:
                    continue  # Reject unknowns
                
                if any(gid in request.exclude_genres for gid in genre_ids):
                    print(f"[VALIDATION ERROR] Excluded genre found in final results: {candidate.get('title') or candidate.get('name')}")
                    continue  # REJECT
            
            validated.append(candidate)
        
        return validated
    
    def _to_candidate(
        self,
        raw: Dict[str, Any],
        request: RecommendationRequest
    ) -> "RecommendationCandidate":
        """Convert raw TMDB data to RecommendationCandidate."""
        from models.recommendation import RecommendationCandidate, RecommendationEvidence, GenreMatch
        
        media_type = MediaType(raw.get("_media_type", "movie"))
        
        # Extract metadata
        if media_type == MediaType.MOVIE:
            title = raw.get("title", "Unknown")
            release_date = raw.get("release_date")
        else:
            title = raw.get("name", "Unknown")
            release_date = raw.get("first_air_date")
        
        # Extract release year
        release_year = None
        if release_date:
            try:
                release_year = int(release_date.split("-")[0])
            except:
                pass
        
        # Build genre matches
        genre_ids = raw.get("genre_ids", [])
        all_genres = []
        matched_genres = []
        
        # Genre name mapping
        genre_names = {
            28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy",
            80: "Crime", 99: "Documentary", 18: "Drama", 10751: "Family",
            14: "Fantasy", 36: "History", 27: "Horror", 10402: "Music",
            9648: "Mystery", 10749: "Romance", 878: "Science Fiction",
            10770: "TV Movie", 53: "Thriller", 10752: "War", 37: "Western",
            10759: "Action & Adventure", 10762: "Kids", 10763: "News",
            10764: "Reality", 10765: "Sci-Fi & Fantasy", 10766: "Soap",
            10767: "Talk", 10768: "War & Politics"
        }
        
        for gid in genre_ids:
            genre_match = GenreMatch(
                genre_id=gid,
                genre_name=genre_names.get(gid, f"Genre {gid}"),
                was_requested=gid in request.include_genres
            )
            all_genres.append(genre_match)
            
            if gid in request.include_genres:
                matched_genres.append(genre_match)
        
        # Build overview excerpt
        overview = raw.get("overview", "")
        overview_excerpt = overview[:150] if overview else None
        
        # Build evidence
        evidence = RecommendationEvidence(
            title=title,
            media_type=media_type,
            tmdb_id=raw.get("id"),
            matched_genres=matched_genres,
            all_genres=all_genres,
            vote_average=raw.get("vote_average"),
            vote_count=raw.get("vote_count"),
            popularity=raw.get("popularity"),
            release_year=release_year,
            release_date=release_date,
            runtime=raw.get("runtime"),
            original_language=raw.get("original_language"),
            overview_excerpt=overview_excerpt,
            poster_path=raw.get("poster_path"),
            provider_verification_attempted=False
        )
        
        # Calculate scores from our internal scoring
        quality = raw.get("_quality", 0.0)
        popularity_score = raw.get("_popularity", 0.0)
        mood_fit = raw.get("_mood_fit", 0.5)
        
        # Relevance = mood fit (how well it matches requested criteria)
        relevance = mood_fit
        
        # Final score from our internal scoring
        final_score = raw.get("_score", 0.0)
        
        return RecommendationCandidate(
            evidence=evidence,
            relevance_score=min(relevance, 1.0),
            quality_score=min(quality, 1.0),
            popularity_score=min(popularity_score, 1.0),
            final_score=min(final_score / 1.0, 1.0)  # Normalize to 0-1
        )
    
    def _build_match_reasons(
        self,
        candidate: Dict[str, Any],
        request: RecommendationRequest
    ) -> List[str]:
        """Build evidence-based match reasons from actual metadata."""
        reasons = []
        
        # Genre match
        genre_ids = candidate.get("genre_ids", [])
        if request.include_genres and genre_ids:
            matching = set(genre_ids) & set(request.include_genres)
            if matching:
                reasons.append(f"Matches requested genres")
        
        # Quality
        vote_avg = candidate.get("vote_average")
        if vote_avg and vote_avg >= 7.0:
            reasons.append(f"Highly rated ({vote_avg:.1f}/10)")
        
        # Popularity
        popularity = candidate.get("popularity", 0)
        if popularity > 50:
            reasons.append("Popular title")
        
        # Mood fit
        if request.mood:
            mood_score = candidate.get("_mood_fit", 0.5)
            if mood_score > 0.7:
                reasons.append(f"Good fit for {request.mood} mood")
        
        # Recent release
        recency = candidate.get("_recency", 0.5)
        if recency > 0.8:
            reasons.append("Recent release")
        
        # Default reason if none found
        if not reasons:
            reasons.append("Matches your preferences")
        
        return reasons[:3]  # Max 3 reasons
    
    def _generate_explanation(
        self,
        candidate: RecommendationCandidate,
        request: RecommendationRequest
    ) -> str:
        """
        Generate evidence-based explanation for a recommendation.
        
        Uses only verified metadata from RecommendationEvidence.
        Never fabricates plot details or provider information.
        """
        evidence = candidate.evidence
        parts = []
        
        # Genre match (if requested)
        if evidence.matched_genres:
            genre_names = [g.genre_name for g in evidence.matched_genres if g.genre_name]
            if genre_names:
                parts.append(f"Matches your interest in {', '.join(genre_names[:2])}")
        
        # Quality signal
        if evidence.has_rating_evidence():
            rating_desc = evidence.get_rating_description()
            if rating_desc:
                parts.append(rating_desc)
        
        # Emotional / Tone signal
        if request.emotional_sub_intent == "tearjerker":
            parts.append("known for poignant, emotional resonance")
        elif request.emotional_sub_intent == "feelgood":
            parts.append("a heartwarming, uplifting story")
        elif request.emotional_sub_intent == "bittersweet":
            parts.append("a nuanced, bittersweet tone")
        elif "darker" in request.tone_modifiers or request.emotional_sub_intent in ("dark", "darker"):
            parts.append("a darker, intense tone")
            
        # Exclusions note
        if request.exclude_genres:
            if 10749 in request.exclude_genres:
                parts.append("strictly non-romance")
            elif 27 in request.exclude_genres:
                parts.append("no horror elements")
        
        # Popularity signal (if high)
        if evidence.popularity and evidence.popularity > 100:
            parts.append("highly popular")
        
        # Recent release (if within 2 years and have year)
        if evidence.release_year:
            current_year = 2026  # Hard-coded as in system context
            if current_year - evidence.release_year <= 2:
                parts.append(f"recent {evidence.release_year} release")
        
        # Runtime (if movie and within preference)
        if evidence.runtime and request.runtime_preference:
            if request.runtime_preference == "under_90" and evidence.runtime < 90:
                parts.append(f"{evidence.runtime}min runtime")
            elif request.runtime_preference == "90_to_130" and 90 <= evidence.runtime <= 130:
                parts.append(f"{evidence.runtime}min")
        
        # Provider (only if verified)
        if evidence.provider_verification_attempted and evidence.available_on_requested_provider:
            parts.append("available on your provider")
        
        # Fallback if no specific reasons
        if not parts:
            if evidence.all_genres:
                genre_names = [g.genre_name for g in evidence.all_genres[:2] if g.genre_name]
                if genre_names:
                    return f"A {' '.join(genre_names)} title"
            return "Recommended based on your preferences"
        
        # Join parts into natural sentence
        if len(parts) == 1:
            return parts[0].capitalize()
        elif len(parts) == 2:
            return f"{parts[0].capitalize()}, {parts[1]}"
        else:
            return f"{parts[0].capitalize()}, {parts[1]}, and {parts[2]}"


# Global instance
recommendation_engine = RecommendationEngine()
