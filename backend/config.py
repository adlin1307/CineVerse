from pydantic_settings import BaseSettings
from typing import Optional
from pathlib import Path


# Get the directory where this config file is located
BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"


class Settings(BaseSettings):
    """Application configuration settings loaded from environment variables."""
    
    # TMDB API
    tmdb_api_key: Optional[str] = None
    tmdb_base_url: str = "https://api.themoviedb.org/3"
    
    # Gemini API
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-3.5-flash-lite"
    
    # Streaming Provider Configuration
    watch_region: str = "IN"  # Default to India (ISO 3166-1 alpha-2)
    
    # Database
    database_url: str = "sqlite:///./cineverse.db"
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    
    # CORS
    allowed_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    
    model_config = {
        "env_file": str(ENV_FILE),
        "case_sensitive": False
    }


settings = Settings()
