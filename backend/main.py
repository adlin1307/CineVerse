from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings, ENV_FILE
from routers import movies_router, series_router, search_router, people_router, recommendations_router, scout_router
import uvicorn

# Initialize FastAPI app
app = FastAPI(
    title="CineVerse API",
    description="Backend API for CineVerse movie and series discovery platform",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(movies_router)
app.include_router(series_router)
app.include_router(search_router)
app.include_router(people_router)
app.include_router(recommendations_router)
app.include_router(scout_router)


@app.on_event("startup")
async def startup_event():
    """Log configuration status on startup."""
    tmdb_configured = settings.tmdb_api_key is not None and settings.tmdb_api_key != "your_api_key_here"
    print(f"[Config] Loading .env from: {ENV_FILE}")
    print(f"[Config] .env file exists: {ENV_FILE.exists()}")
    print(f"[Config] TMDB API Key configured: {tmdb_configured}")
    if tmdb_configured:
        print(f"[Config] TMDB API Key loaded: {settings.tmdb_api_key[:8]}... (length: {len(settings.tmdb_api_key)})")
    else:
        print(f"[Config] TMDB API Key status: Not configured or placeholder value")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    from services.tmdb_service import tmdb_service
    await tmdb_service.close()
    print("[Cleanup] TMDB service client closed")


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
    """Health check endpoint."""
    tmdb_configured = settings.tmdb_api_key is not None and settings.tmdb_api_key != "your_api_key_here"
    
    return {
        "status": "healthy",
        "tmdb_configured": tmdb_configured,
        "database": "connected"
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=True
    )
