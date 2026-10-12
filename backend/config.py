from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application configuration settings loaded from environment variables."""
    
    # TMDB API
    tmdb_api_key: Optional[str] = None
    tmdb_base_url: str = "https://api.themoviedb.org/3"
    
    # Database
    database_url: str = "sqlite:///./cineverse.db"
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    
    # CORS
    allowed_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
