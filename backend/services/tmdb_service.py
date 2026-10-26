import httpx
from typing import Optional, Dict, Any, List
from config import settings


class TMDBService:
    """Service for interacting with The Movie Database (TMDB) API."""
    
    def __init__(self):
        self.base_url = settings.tmdb_base_url
        self.image_base_url = "https://image.tmdb.org/t/p/"
        self._api_key_override = None
        # Configure timeouts and limits to prevent connection issues
        self.timeout = httpx.Timeout(
            connect=10.0,  # 10 seconds to establish connection
            read=30.0,     # 30 seconds to read response
            write=10.0,    # 10 seconds to send request
            pool=10.0      # 10 seconds to get connection from pool
        )
        
        # Configure connection limits to prevent overwhelming TMDB
        self.limits = httpx.Limits(
            max_connections=20,        # Max total connections
            max_keepalive_connections=10  # Max persistent connections
        )
        
        # Create a persistent client (reused across requests)
        self._client: Optional[httpx.AsyncClient] = None
    
        
    @property
    def api_key(self) -> str:
        if self._api_key_override is not None:
            return self._api_key_override
        return settings.tmdb_api_key
        
    @property
    def is_configured(self) -> bool:
        if not self.api_key:
            return False
        clean = self.api_key.strip().lower()
        if clean in ["your_api_key_here", "your_tmdb_api_key_here", "your_actual_tmdb_key_here", ""]:
            return False
        return True
        
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                limits=self.limits,
                follow_redirects=True
            )
        return self._client
    
    async def close(self):
        """Close the HTTP client."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
    
    async def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a request to TMDB API with proper error handling and retry logic."""
        if not self.is_configured:
            raise ValueError("TMDB API key not configured. Please set TMDB_API_KEY in .env file.")
        
        if params is None:
            params = {}
        
        params["api_key"] = self.api_key
        url = f"{self.base_url}/{endpoint}"
        
        # Retry logic for transient connection errors
        max_retries = 3
        last_error = None
        
        for attempt in range(max_retries):
            try:
                client = await self._get_client()
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.json()
            except RuntimeError as e:
                # Handle "Event loop is closed" error
                if "Event loop is closed" in str(e):
                    # Client's event loop is stale, close and recreate
                    if self._client:
                        try:
                            await self._client.aclose()
                        except Exception:
                            pass
                        self._client = None
                    
                    if attempt < max_retries - 1:
                        continue
                    raise ValueError(f"TMDB API client event loop closed: {endpoint}") from e
                raise
            except httpx.ConnectError as e:
                last_error = e
                if attempt < max_retries - 1:
                    # Wait before retry (exponential backoff)
                    await self._async_sleep(0.5 * (2 ** attempt))
                    # Close and recreate client on connection error
                    if self._client:
                        await self._client.aclose()
                        self._client = None
                    continue
                # Final attempt failed
                raise ValueError(f"Failed to connect to TMDB API after {max_retries} attempts: {endpoint}") from e
            except httpx.TimeoutException as e:
                # Distinguish between different timeout types
                timeout_type = "connection" if "connect" in str(e).lower() else "read"
                raise ValueError(f"TMDB API request timed out ({timeout_type} timeout after 30s): {endpoint}") from e
            except httpx.HTTPStatusError as e:
                raise ValueError(f"TMDB API returned error {e.response.status_code}: {endpoint}") from e
            except Exception as e:
                raise ValueError(f"TMDB API request failed: {endpoint}. Error: {str(e)}") from e
        
        # Should never reach here, but just in case
        raise ValueError(f"TMDB API request failed after retries: {endpoint}") from last_error
    
    async def _async_sleep(self, seconds: float):
        """Async sleep helper."""
        import asyncio
        await asyncio.sleep(seconds)
    
    def get_image_url(self, path: Optional[str], size: str = "original") -> Optional[str]:
        """Generate full image URL from TMDB image path."""
        if not path:
            return None
        return f"{self.image_base_url}{size}{path}"
    
    async def get_trending(self, media_type: str = "all", time_window: str = "week") -> Dict[str, Any]:
        """Get trending movies/series."""
        return await self._make_request(f"trending/{media_type}/{time_window}")
    
    async def get_popular_movies(self, page: int = 1) -> Dict[str, Any]:
        """Get popular movies."""
        return await self._make_request("movie/popular", {"page": page})
    
    async def get_popular_series(self, page: int = 1) -> Dict[str, Any]:
        """Get popular TV series."""
        return await self._make_request("tv/popular", {"page": page})
    
    async def get_movie_details(self, movie_id: int) -> Dict[str, Any]:
        """Get detailed information about a movie."""
        return await self._make_request(
            f"movie/{movie_id}",
            {"append_to_response": "credits,videos,recommendations,keywords"}
        )
    
    async def get_series_details(self, series_id: int) -> Dict[str, Any]:
        """Get detailed information about a TV series."""
        return await self._make_request(
            f"tv/{series_id}",
            {"append_to_response": "credits,videos,recommendations,keywords"}
        )
    
    async def search_multi(self, query: str, page: int = 1) -> Dict[str, Any]:
        """Search for movies, TV series, and people."""
        return await self._make_request("search/multi", {"query": query, "page": page})
    
    async def search_movies(self, query: str, page: int = 1) -> Dict[str, Any]:
        """Search for movies."""
        return await self._make_request("search/movie", {"query": query, "page": page})
    
    async def search_series(self, query: str, page: int = 1) -> Dict[str, Any]:
        """Search for TV series."""
        return await self._make_request("search/tv", {"query": query, "page": page})
    
    async def discover_movies(
        self,
        page: int = 1,
        sort_by: str = "popularity.desc",
        with_genres: Optional[str] = None,
        with_original_language: Optional[str] = None,
        year: Optional[int] = None,
        **kwargs  # Accept additional TMDB discover parameters
    ) -> Dict[str, Any]:
        """Discover movies with filters."""
        params = {
            "page": page,
            "sort_by": sort_by
        }
        
        if with_genres:
            params["with_genres"] = with_genres
        if with_original_language:
            params["with_original_language"] = with_original_language
        if year:
            params["year"] = year
        
        # Add any additional parameters (e.g., vote_count.gte, release_date.gte)
        params.update(kwargs)
        
        return await self._make_request("discover/movie", params)
    
    async def discover_series(
        self,
        page: int = 1,
        sort_by: str = "popularity.desc",
        with_genres: Optional[str] = None,
        with_original_language: Optional[str] = None,
        first_air_date_year: Optional[int] = None,
        **kwargs  # Accept additional TMDB discover parameters
    ) -> Dict[str, Any]:
        """Discover TV series with filters."""
        params = {
            "page": page,
            "sort_by": sort_by
        }
        
        if with_genres:
            params["with_genres"] = with_genres
        if with_original_language:
            params["with_original_language"] = with_original_language
        if first_air_date_year:
            params["first_air_date_year"] = first_air_date_year
        
        # Add any additional parameters (e.g., vote_count.gte, first_air_date.gte)
        params.update(kwargs)
        
        return await self._make_request("discover/tv", params)
    
    async def get_genres_movies(self) -> Dict[str, Any]:
        """Get list of movie genres."""
        return await self._make_request("genre/movie/list")
    
    async def get_genres_series(self) -> Dict[str, Any]:
        """Get list of TV genres."""
        return await self._make_request("genre/tv/list")
    
    async def get_person_details(self, person_id: int) -> Dict[str, Any]:
        """Get detailed information about a person (actor/crew)."""
        return await self._make_request(
            f"person/{person_id}",
            {"append_to_response": "movie_credits,tv_credits,combined_credits"}
        )
    
    async def get_movie_videos(self, movie_id: int) -> Dict[str, Any]:
        """Get videos (trailers, teasers, etc.) for a movie."""
        return await self._make_request(f"movie/{movie_id}/videos")
    
    async def get_series_videos(self, series_id: int) -> Dict[str, Any]:
        """Get videos (trailers, teasers, etc.) for a TV series."""
        return await self._make_request(f"tv/{series_id}/videos")


# Singleton instance
tmdb_service = TMDBService()
