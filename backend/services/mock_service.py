"""Mock data service for when TMDB API is not configured."""

from typing import Dict, Any, List


class MockDataService:
    """Provides mock movie and series data for development without TMDB API key."""
    
    def __init__(self):
        self.mock_movies = self._generate_mock_movies()
        self.mock_series = self._generate_mock_series()
    
    def _generate_mock_movies(self) -> List[Dict[str, Any]]:
        """Generate diverse mock movie data."""
        return [
            {
                "id": 1,
                "title": "The Crimson Dawn",
                "original_title": "The Crimson Dawn",
                "overview": "A breathtaking journey through time as a historian discovers ancient secrets that could change humanity's understanding of history forever.",
                "poster_path": None,
                "backdrop_path": None,
                "release_date": "2023-06-15",
                "genre_ids": [28, 12, 878],
                "vote_average": 8.2,
                "vote_count": 1523,
                "popularity": 95.4,
                "original_language": "en"
            },
            {
                "id": 2,
                "title": "Midnight in Seoul",
                "original_title": "서울의 한밤중",
                "overview": "Two strangers meet on the last train of the night and spend an unforgettable evening exploring the hidden corners of Seoul.",
                "poster_path": None,
                "backdrop_path": None,
                "release_date": "2024-03-22",
                "genre_ids": [10749, 18],
                "vote_average": 7.8,
                "vote_count": 892,
                "popularity": 78.3,
                "original_language": "ko"
            },
            {
                "id": 3,
                "title": "The Quantum Paradox",
                "original_title": "The Quantum Paradox",
                "overview": "A brilliant physicist accidentally creates a portal to parallel universes, unleashing consequences that threaten reality itself.",
                "poster_path": None,
                "backdrop_path": None,
                "release_date": "2023-11-10",
                "genre_ids": [878, 53, 28],
                "vote_average": 8.5,
                "vote_count": 2341,
                "popularity": 123.7,
                "original_language": "en"
            },
            {
                "id": 4,
                "title": "Letters from Mumbai",
                "original_title": "मुंबई से पत्र",
                "overview": "An elderly woman discovers a box of letters that reveal a hidden love story spanning decades across two continents.",
                "poster_path": None,
                "backdrop_path": None,
                "release_date": "2024-01-18",
                "genre_ids": [18, 10749],
                "vote_average": 8.9,
                "vote_count": 1876,
                "popularity": 67.2,
                "original_language": "hi"
            },
            {
                "id": 5,
                "title": "Northern Lights",
                "original_title": "Nordlys",
                "overview": "A documentary filmmaker travels to the Arctic to capture the aurora borealis but discovers a community fighting to preserve their way of life.",
                "poster_path": None,
                "backdrop_path": None,
                "release_date": "2023-09-05",
                "genre_ids": [18, 99],
                "vote_average": 7.4,
                "vote_count": 445,
                "popularity": 34.8,
                "original_language": "no"
            },
            {
                "id": 6,
                "title": "The Last Symphony",
                "original_title": "La Última Sinfonía",
                "overview": "A famous conductor battles a terminal illness while preparing his final performance, a piece that will become his legacy.",
                "poster_path": None,
                "backdrop_path": None,
                "release_date": "2024-02-14",
                "genre_ids": [18, 10402],
                "vote_average": 8.7,
                "vote_count": 1234,
                "popularity": 56.9,
                "original_language": "es"
            },
            {
                "id": 7,
                "title": "Shadow Valley",
                "original_title": "Shadow Valley",
                "overview": "In a small mountain town, a detective investigates a series of mysterious disappearances connected to ancient folklore.",
                "poster_path": None,
                "backdrop_path": None,
                "release_date": "2023-10-31",
                "genre_ids": [27, 53, 9648],
                "vote_average": 7.6,
                "vote_count": 987,
                "popularity": 82.4,
                "original_language": "en"
            },
            {
                "id": 8,
                "title": "Café au Lait",
                "original_title": "Café au Lait",
                "overview": "A charming romantic comedy about a barista who believes she can predict people's futures based on their coffee choices.",
                "poster_path": None,
                "backdrop_path": None,
                "release_date": "2024-04-07",
                "genre_ids": [35, 10749],
                "vote_average": 7.1,
                "vote_count": 623,
                "popularity": 45.3,
                "original_language": "fr"
            }
        ]
    
    def _generate_mock_series(self) -> List[Dict[str, Any]]:
        """Generate diverse mock series data."""
        return [
            {
                "id": 101,
                "name": "Echoes of Tomorrow",
                "original_name": "Echoes of Tomorrow",
                "overview": "A gripping sci-fi thriller where a team of scientists receive messages from their future selves warning of an impending catastrophe.",
                "poster_path": None,
                "backdrop_path": None,
                "first_air_date": "2023-09-15",
                "genre_ids": [18, 878, 9648],
                "vote_average": 8.4,
                "vote_count": 3421,
                "popularity": 156.8,
                "original_language": "en"
            },
            {
                "id": 102,
                "name": "The Tea House Chronicles",
                "original_name": "茶館編年史",
                "overview": "Three generations of a family run a traditional tea house in Tokyo, navigating love, loss, and the changing times.",
                "poster_path": None,
                "backdrop_path": None,
                "first_air_date": "2023-04-12",
                "genre_ids": [18],
                "vote_average": 8.9,
                "vote_count": 2134,
                "popularity": 89.4,
                "original_language": "ja"
            },
            {
                "id": 103,
                "name": "Darkwater Bay",
                "original_name": "Darkwater Bay",
                "overview": "A coastal town harbors dark secrets as new residents uncover a conspiracy that has been hidden for decades.",
                "poster_path": None,
                "backdrop_path": None,
                "first_air_date": "2024-01-08",
                "genre_ids": [18, 9648, 80],
                "vote_average": 7.9,
                "vote_count": 1876,
                "popularity": 112.3,
                "original_language": "en"
            },
            {
                "id": 104,
                "name": "Rising Phoenix",
                "original_name": "凤凰涅槃",
                "overview": "An underdog e-sports team fights their way to the world championships, overcoming personal struggles and fierce competition.",
                "poster_path": None,
                "backdrop_path": None,
                "first_air_date": "2023-07-20",
                "genre_ids": [18],
                "vote_average": 8.2,
                "vote_count": 1543,
                "popularity": 98.7,
                "original_language": "zh"
            },
            {
                "id": 105,
                "name": "The Berlin Diaries",
                "original_name": "Die Berliner Tagebücher",
                "overview": "A historical drama following four friends in Berlin from the fall of the wall through the transformation of the city.",
                "poster_path": None,
                "backdrop_path": None,
                "first_air_date": "2023-11-03",
                "genre_ids": [18, 36],
                "vote_average": 8.6,
                "vote_count": 2987,
                "popularity": 76.5,
                "original_language": "de"
            }
        ]
    
    async def get_trending(self, media_type: str = "all", time_window: str = "week") -> Dict[str, Any]:
        """Get mock trending content."""
        all_content = self.mock_movies[:4] + self.mock_series[:2]
        return {
            "page": 1,
            "results": all_content,
            "total_pages": 1,
            "total_results": len(all_content)
        }
    
    async def get_popular_movies(self, page: int = 1) -> Dict[str, Any]:
        """Get mock popular movies."""
        return {
            "page": page,
            "results": self.mock_movies,
            "total_pages": 1,
            "total_results": len(self.mock_movies)
        }
    
    async def get_popular_series(self, page: int = 1) -> Dict[str, Any]:
        """Get mock popular series."""
        return {
            "page": page,
            "results": self.mock_series,
            "total_pages": 1,
            "total_results": len(self.mock_series)
        }
    
    async def search_multi(self, query: str, page: int = 1) -> Dict[str, Any]:
        """Mock multi search."""
        query_lower = query.lower()
        results = []
        
        for movie in self.mock_movies:
            if query_lower in movie["title"].lower() or query_lower in movie["overview"].lower():
                results.append({**movie, "media_type": "movie"})
        
        for series in self.mock_series:
            if query_lower in series["name"].lower() or query_lower in series["overview"].lower():
                results.append({**series, "media_type": "tv"})
        
        return {
            "page": page,
            "results": results[:20],
            "total_pages": 1,
            "total_results": len(results)
        }
    
    async def get_movie_details(self, movie_id: int) -> Dict[str, Any]:
        """Get mock movie details."""
        movie = next((m for m in self.mock_movies if m["id"] == movie_id), None)
        
        if not movie:
            raise ValueError(f"Movie with id {movie_id} not found")
        
        return {
            **movie,
            "runtime": 127,
            "genres": [{"id": gid, "name": self._get_genre_name(gid)} for gid in movie["genre_ids"]],
            "credits": {
                "cast": [
                    {"id": 1, "name": "Sarah Chen", "character": "Lead Character", "profile_path": None},
                    {"id": 2, "name": "Marcus Johnson", "character": "Supporting Role", "profile_path": None}
                ],
                "crew": [
                    {"id": 3, "name": "Jane Director", "job": "Director", "profile_path": None},
                    {"id": 4, "name": "Alex Writer", "job": "Writer", "profile_path": None}
                ]
            },
            "videos": {"results": []},
            "recommendations": {"results": self.mock_movies[:3]}
        }
    
    async def get_series_details(self, series_id: int) -> Dict[str, Any]:
        """Get mock series details."""
        series = next((s for s in self.mock_series if s["id"] == series_id), None)
        
        if not series:
            raise ValueError(f"Series with id {series_id} not found")
        
        return {
            **series,
            "number_of_seasons": 2,
            "number_of_episodes": 16,
            "genres": [{"id": gid, "name": self._get_genre_name(gid)} for gid in series["genre_ids"]],
            "credits": {
                "cast": [
                    {"id": 1, "name": "Emma Stone", "character": "Protagonist", "profile_path": None},
                    {"id": 2, "name": "David Park", "character": "Deuteragonist", "profile_path": None}
                ],
                "crew": [
                    {"id": 3, "name": "Lisa Showrunner", "job": "Creator", "profile_path": None}
                ]
            },
            "videos": {"results": []},
            "recommendations": {"results": self.mock_series[:2]}
        }
    
    def _get_genre_name(self, genre_id: int) -> str:
        """Map genre ID to name."""
        genre_map = {
            28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy", 80: "Crime",
            99: "Documentary", 18: "Drama", 10751: "Family", 14: "Fantasy", 36: "History",
            27: "Horror", 10402: "Music", 9648: "Mystery", 10749: "Romance", 878: "Science Fiction",
            10770: "TV Movie", 53: "Thriller", 10752: "War", 37: "Western"
        }
        return genre_map.get(genre_id, "Unknown")
    
    async def get_genres_movies(self) -> Dict[str, Any]:
        """Get mock movie genres."""
        return {
            "genres": [
                {"id": 28, "name": "Action"},
                {"id": 12, "name": "Adventure"},
                {"id": 35, "name": "Comedy"},
                {"id": 18, "name": "Drama"},
                {"id": 27, "name": "Horror"},
                {"id": 878, "name": "Science Fiction"},
                {"id": 53, "name": "Thriller"},
                {"id": 10749, "name": "Romance"}
            ]
        }
    
    async def get_genres_series(self) -> Dict[str, Any]:
        """Get mock series genres."""
        return await self.get_genres_movies()


mock_service = MockDataService()
