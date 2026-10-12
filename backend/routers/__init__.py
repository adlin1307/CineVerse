from .movies import router as movies_router
from .series import router as series_router
from .search import router as search_router

__all__ = ["movies_router", "series_router", "search_router"]
