"""
User-specific persistent watchlist router for CineVerse.
Ensures full data isolation between users.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from routers.auth import require_user
from database import (
    get_watchlist,
    add_watchlist_item,
    remove_watchlist_item,
    clear_watchlist,
    sync_watchlist
)

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


class AddWatchlistItemRequest(BaseModel):
    item: Dict[str, Any]


class SyncWatchlistRequest(BaseModel):
    items: List[Dict[str, Any]]


@router.get("")
async def get_my_watchlist(user: Dict[str, Any] = Depends(require_user)):
    """Retrieve the authenticated user's watchlist."""
    return get_watchlist(user["id"])


@router.post("")
async def add_to_my_watchlist(req: AddWatchlistItemRequest, user: Dict[str, Any] = Depends(require_user)):
    """Add a movie or series to the authenticated user's watchlist."""
    if not req.item or not req.item.get("id"):
        raise HTTPException(status_code=400, detail="Invalid item data.")
    return add_watchlist_item(user["id"], req.item)


@router.delete("/{media_type}/{item_id}")
async def remove_from_my_watchlist(media_type: str, item_id: int, user: Dict[str, Any] = Depends(require_user)):
    """Remove a movie or series from the authenticated user's watchlist."""
    return remove_watchlist_item(user["id"], item_id, media_type)


@router.delete("")
async def clear_my_watchlist(user: Dict[str, Any] = Depends(require_user)):
    """Clear all items from the authenticated user's watchlist."""
    return clear_watchlist(user["id"])


@router.post("/sync")
async def sync_my_watchlist(req: SyncWatchlistRequest, user: Dict[str, Any] = Depends(require_user)):
    """Merge items from local guest storage into the user's permanent account."""
    return sync_watchlist(user["id"], req.items)
