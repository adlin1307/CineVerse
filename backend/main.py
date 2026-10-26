import compat  # Ensures Starlette Router compatibility across versions
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings, ENV_FILE
from routers import (
    movies_router,
    series_router,
    search_router,
    people_router,
    recommendations_router,
    scout_router,
    auth_router,
    watchlist_router
)
from database import init_db
import uvicorn


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management for startup and shutdown."""
    # Initialize SQLite database schema
    init_db()
    
    # Startup logging (without exposing secrets)
    tmdb_configured = bool(settings.tmdb_api_key and settings.tmdb_api_key != "your_api_key_here")
    gemini_configured = bool(settings.gemini_api_key and settings.gemini_api_key != "your_gemini_api_key_here")
    print(f"[Config] Loading .env from: {ENV_FILE}")
    print(f"[Config] .env file exists: {ENV_FILE.exists()}")
    print(f"[Config] TMDB API Key configured: {tmdb_configured}")
    print(f"[Config] Gemini API Key configured: {gemini_configured}")
    print(f"[Config] Active Gemini Model: {settings.gemini_model}")
    print("[Config] Database initialized: SQLite (cineverse.db)")
    yield
    # Cleanup on shutdown
    try:
        from services.tmdb_service import tmdb_service
        await tmdb_service.close()
        print("[Cleanup] TMDB service client closed")
    except Exception as e:
        print(f"[Cleanup] Error closing TMDB client: {e}")


# Initialize FastAPI app with modern lifespan
app = FastAPI(
    title="CineVerse API",
    description="Backend API for CineVerse movie and series discovery platform",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
cors_kwargs = {
    "allow_origins": settings.allowed_origins,
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
}
if getattr(settings, "allow_origin_regex", None):
    cors_kwargs["allow_origin_regex"] = settings.allow_origin_regex

app.add_middleware(CORSMiddleware, **cors_kwargs)

# Include routers
app.include_router(movies_router)
app.include_router(series_router)
app.include_router(search_router)
app.include_router(people_router)
app.include_router(recommendations_router)
app.include_router(scout_router)
app.include_router(auth_router)
app.include_router(watchlist_router)


@app.get("/")
async def root():
    """Root endpoint - API information."""
    return {
        "name": "CineVerse API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint reflecting true system state."""
    tmdb_configured = bool(settings.tmdb_api_key and settings.tmdb_api_key != "your_api_key_here")
    gemini_configured = bool(settings.gemini_api_key and settings.gemini_api_key != "your_gemini_api_key_here")
    
    return {
        "status": "healthy",
        "tmdb_configured": tmdb_configured,
        "gemini_configured": gemini_configured,
        "database": "sqlite",
        "persistence": "sqlite_db"
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=True
    )
