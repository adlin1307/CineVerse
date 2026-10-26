import compat  # Ensures Starlette Router compatibility
from .movies import router as movies_router
from .series import router as series_router
from .search import router as search_router
from .people import router as people_router
from .recommendations import router as recommendations_router
from .scout import router as scout_router
from .auth import router as auth_router
from .watchlist import router as watchlist_router

__all__ = [
    "movies_router",
    "series_router",
    "search_router",
    "people_router",
    "recommendations_router",
    "scout_router",
    "auth_router",
    "watchlist_router"
]

