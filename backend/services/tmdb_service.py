import httpx
from typing import Optional, Dict, Any, List
from config import settings


class TMDBService:
    """Service for interacting with The Movie Database (TMDB) API."""
    
    def __init__(self):
        self.api_key = settings.tmdb_api_key
        self.base_url = settings.tmdb_base_url
        self.image_base_url = "https://image.tmdb.org/t/p/"
        self.is_configured = self.api_key and self.api_key != "your_api_key_here"
    
    async def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a request to TMDB API."""
        if not self.is_configured:
            raise ValueError("TMDB API key not configured. Please set TMDB_API_KEY in .env file.")
        
        if params is None:
            params = {}
        
        params["api_key"] = self.api_key
        
        url = f"{self.base_url}/{endpoint}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()
    
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
        year: Optional[int] = None
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
        
        return await self._make_request("discover/movie", params)
    
    async def discover_series(
        self,
        page: int = 1,
        sort_by: str = "popularity.desc",
        with_genres: Optional[str] = None,
        with_original_language: Optional[str] = None,
        first_air_date_year: Optional[int] = None
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
        
        return await self._make_request("discover/tv", params)
    
    async def get_genres_movies(self) -> Dict[str, Any]:
        """Get list of movie genres."""
        return await self._make_request("genre/movie/list")
    
    async def get_genres_series(self) -> Dict[str, Any]:
        """Get list of TV genres."""
        return await self._make_request("genre/tv/list")


# Singleton instance
tmdb_service = TMDBService()
