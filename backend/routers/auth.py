"""
Authentication router for CineVerse.
Provides signup, login, logout, and current user validation.
"""

import re
from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from database import (
    create_user,
    get_user_by_username,
    verify_password,
    create_session,
    get_user_from_token,
    delete_session
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class AuthRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=30)
    password: str = Field(..., min_length=6, max_length=128)


def get_current_user(authorization: Optional[str] = Header(None)) -> Optional[Dict[str, Any]]:
    """Dependency to retrieve the authenticated user from Bearer token."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization[7:].strip()
    return get_user_from_token(token)


def require_user(current_user: Optional[Dict[str, Any]] = Depends(get_current_user)) -> Dict[str, Any]:
    """Dependency that strictly requires an authenticated user."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required. Please log in.")
    return current_user


@router.post("/signup")
async def signup(req: AuthRequest):
    """Register a new user account."""
    username = req.username.strip()
    password = req.password

    # Validate username format (alphanumeric and underscore)
    if not re.match(r"^[a-zA-Z0-9_]{3,30}$", username):
        raise HTTPException(
            status_code=400,
            detail="Username must be 3-30 characters and contain only letters, numbers, and underscores."
        )

    # Check for duplicate username
    existing = get_user_by_username(username)
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Username is already taken. Please choose a different one."
        )

    try:
        user = create_user(username, password)
        token = create_session(user["id"])
        return {
            "token": token,
            "user": {
                "id": user["id"],
                "username": user["username"]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to create account. Please try again.")


@router.post("/login")
async def login(req: AuthRequest):
    """Log in an existing user."""
    username = req.username.strip()
    password = req.password

    user = get_user_by_username(username)
    if not user or not verify_password(password, user["password_hash"]):
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password. Please try again."
        )

    token = create_session(user["id"])
    return {
        "token": token,
        "user": {
            "id": user["id"],
            "username": user["username"]
        }
    }


@router.post("/logout")
async def logout(authorization: Optional[str] = Header(None)):
    """Log out user by invalidating their session token."""
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()
        delete_session(token)
    return {"message": "Logged out successfully"}


@router.get("/me")
async def get_me(user: Optional[Dict[str, Any]] = Depends(get_current_user)):
    """Get current authenticated user profile."""
    if not user:
        raise HTTPException(status_code=401, detail="Session expired or invalid. Please log in again.")
    return {"user": user}
