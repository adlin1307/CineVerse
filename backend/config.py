from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Optional, List, Union
from pathlib import Path
import json


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
    gemini_model: str = "gemini-2.5-flash"
    
    # Streaming Provider Configuration
    watch_region: str = "IN"  # Default to India (ISO 3166-1 alpha-2)
    
    # Database
    database_url: str = "sqlite:///./cineverse.db"
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    
    # CORS
    allowed_origins: Union[List[str], str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    allow_origin_regex: Optional[str] = r"https://.*\.vercel\.app|https://.*\.onrender\.com|https://.*\.netlify\.app"

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v):
        if isinstance(v, str):
            v_clean = v.strip()
            if v_clean.startswith("[") and v_clean.endswith("]"):
                try:
                    return json.loads(v_clean)
                except Exception:
                    pass
            return [origin.strip() for origin in v_clean.split(",") if origin.strip()]
        return v
    
    model_config = {
        "env_file": str(ENV_FILE),
        "case_sensitive": False
    }


settings = Settings()
