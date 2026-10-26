"""
Database and authentication persistence layer for CineVerse.
Provides SQLite storage for users, sessions, watchlists, and Scout conversations.
"""

import sqlite3
import hashlib
import os
import secrets
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List

BASE_DIR = Path(__file__).resolve().parent
DB_FILE = BASE_DIR / "cineverse.db"


def get_db():
    """Get a database connection with row factory enabled."""
    conn = sqlite3.connect(str(DB_FILE))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Initialize database tables."""
    with get_db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL
        );

        CREATE TABLE IF NOT EXISTS watchlists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            item_id INTEGER NOT NULL,
            media_type TEXT NOT NULL,
            title TEXT NOT NULL,
            poster_path TEXT,
            vote_average REAL,
            release_date TEXT,
            overview TEXT,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, item_id, media_type)
        );

        CREATE TABLE IF NOT EXISTS scout_conversations (
            id TEXT PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS scout_messages (
            id TEXT PRIMARY KEY,
            conversation_id TEXT NOT NULL REFERENCES scout_conversations(id) ON DELETE CASCADE,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            recommendations_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
        CREATE INDEX IF NOT EXISTS idx_watchlists_user ON watchlists(user_id);
        CREATE INDEX IF NOT EXISTS idx_scout_conv_user ON scout_conversations(user_id);
        CREATE INDEX IF NOT EXISTS idx_scout_msg_conv ON scout_messages(conversation_id);
        """)


# ============================================================================
# Password Hashing & Authentication
# ============================================================================

def hash_password(password: str) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 with 16-byte random salt."""
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return f"{salt.hex()}:{key.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify password against stored salt:hash."""
    try:
        salt_hex, key_hex = stored_hash.split(":")
        salt = bytes.fromhex(salt_hex)
        key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
        return secrets.compare_digest(key.hex(), key_hex)
    except Exception:
        return False


def create_user(username: str, password: str) -> Dict[str, Any]:
    """Create a new user account with secure password hash."""
    hashed = hash_password(password)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username.strip(), hashed)
        )
        user_id = cursor.lastrowid
        return {"id": user_id, "username": username.strip()}


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Retrieve user record by username."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, username, password_hash, created_at FROM users WHERE username = ?",
            (username.strip(),)
        ).fetchone()
        if row:
            return dict(row)
        return None


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve user record by ID."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, username, created_at FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()
        if row:
            return dict(row)
        return None


def create_session(user_id: int) -> str:
    """Create a persistent session token for user (30 days validity)."""
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    with get_db() as conn:
        conn.execute(
            "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
            (token, user_id, expires_at.isoformat())
        )
    return token


def get_user_from_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify session token and return user data if valid and unexpired."""
    if not token:
        return None
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT u.id, u.username, s.expires_at 
            FROM sessions s 
            JOIN users u ON s.user_id = u.id 
            WHERE s.token = ?
            """,
            (token,)
        ).fetchone()
        if not row:
            return None
        
        expires_at_str = row["expires_at"]
        try:
            expires_at = datetime.fromisoformat(expires_at_str)
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > expires_at:
                conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
                return None
        except Exception:
            return None
            
        return {"id": row["id"], "username": row["username"]}


def delete_session(token: str):
    """Delete session token on logout."""
    with get_db() as conn:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))


# ============================================================================
# User-Specific Watchlist Operations
# ============================================================================

def get_watchlist(user_id: int) -> List[Dict[str, Any]]:
    """Retrieve watchlist items for a specific authenticated user."""
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT item_id as id, media_type, title, poster_path, vote_average, release_date, overview, added_at 
            FROM watchlists 
            WHERE user_id = ? 
            ORDER BY added_at DESC
            """,
            (user_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def add_watchlist_item(user_id: int, item: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Add or update a watchlist item for a specific user."""
    item_id = item.get("id")
    media_type = item.get("media_type") or ("tv" if item.get("first_air_date") or item.get("name") else "movie")
    title = item.get("title") or item.get("name") or "Untitled"
    poster_path = item.get("poster_path")
    vote_average = item.get("vote_average")
    release_date = item.get("release_date") or item.get("first_air_date")
    overview = item.get("overview")

    with get_db() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO watchlists 
            (user_id, item_id, media_type, title, poster_path, vote_average, release_date, overview, added_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (user_id, item_id, media_type, title, poster_path, vote_average, release_date, overview)
        )
    return get_watchlist(user_id)


def remove_watchlist_item(user_id: int, item_id: int, media_type: str) -> List[Dict[str, Any]]:
    """Remove item from user's watchlist."""
    with get_db() as conn:
        conn.execute(
            "DELETE FROM watchlists WHERE user_id = ? AND item_id = ? AND media_type = ?",
            (user_id, item_id, media_type)
        )
    return get_watchlist(user_id)


def clear_watchlist(user_id: int) -> List[Dict[str, Any]]:
    """Clear all items from user's watchlist."""
    with get_db() as conn:
        conn.execute("DELETE FROM watchlists WHERE user_id = ?", (user_id,))
    return []


def sync_watchlist(user_id: int, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Safely migrate/merge local items into user's watchlist upon login."""
    if not items:
        return get_watchlist(user_id)
    with get_db() as conn:
        for item in items:
            if not isinstance(item, dict) or not item.get("id"):
                continue
            item_id = item.get("id")
            media_type = item.get("media_type") or ("tv" if item.get("first_air_date") or item.get("name") else "movie")
            title = item.get("title") or item.get("name") or "Untitled"
            poster_path = item.get("poster_path")
            vote_average = item.get("vote_average")
            release_date = item.get("release_date") or item.get("first_air_date")
            overview = item.get("overview")
            conn.execute(
                """
                INSERT OR IGNORE INTO watchlists 
                (user_id, item_id, media_type, title, poster_path, vote_average, release_date, overview, added_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (user_id, item_id, media_type, title, poster_path, vote_average, release_date, overview)
            )
    return get_watchlist(user_id)


# ============================================================================
# Scout Persistent Conversations
# ============================================================================

def list_conversations(user_id: Optional[int]) -> List[Dict[str, Any]]:
    """List conversations owned by user (or anonymous if user_id is None)."""
    with get_db() as conn:
        if user_id is not None:
            rows = conn.execute(
                """
                SELECT id, title, created_at, updated_at 
                FROM scout_conversations 
                WHERE user_id = ? 
                ORDER BY updated_at DESC
                """,
                (user_id,)
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, title, created_at, updated_at 
                FROM scout_conversations 
                WHERE user_id IS NULL 
                ORDER BY updated_at DESC
                """
            ).fetchall()
        return [dict(r) for r in rows]


def get_conversation(conv_id: str, user_id: Optional[int]) -> Optional[Dict[str, Any]]:
    """Get conversation details with messages."""
    with get_db() as conn:
        if user_id is not None:
            conv = conn.execute(
                "SELECT id, user_id, title, created_at, updated_at FROM scout_conversations WHERE id = ? AND user_id = ?",
                (conv_id, user_id)
            ).fetchone()
        else:
            conv = conn.execute(
                "SELECT id, user_id, title, created_at, updated_at FROM scout_conversations WHERE id = ? AND user_id IS NULL",
                (conv_id,)
            ).fetchone()
        if not conv:
            return None

        msg_rows = conn.execute(
            """
            SELECT id, role, content, recommendations_json, created_at 
            FROM scout_messages 
            WHERE conversation_id = ? 
            ORDER BY created_at ASC
            """,
            (conv_id,)
        ).fetchall()

        messages = []
        for m in msg_rows:
            recs = []
            if m["recommendations_json"]:
                try:
                    recs = json.loads(m["recommendations_json"])
                except Exception:
                    recs = []
            messages.append({
                "id": m["id"],
                "role": m["role"],
                "content": m["content"],
                "recommendations": recs,
                "created_at": m["created_at"]
            })

        return {
            "id": conv["id"],
            "title": conv["title"],
            "created_at": conv["created_at"],
            "updated_at": conv["updated_at"],
            "messages": messages
        }


def create_conversation(conv_id: str, user_id: Optional[int], title: str = "New Conversation") -> Dict[str, Any]:
    """Create a new conversation record."""
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO scout_conversations (id, user_id, title, updated_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
            (conv_id, user_id, title)
        )
    return {"id": conv_id, "title": title}


def delete_conversation(conv_id: str, user_id: Optional[int]) -> bool:
    """Delete a single conversation and its associated messages."""
    with get_db() as conn:
        if user_id is not None:
            conv = conn.execute(
                "SELECT id FROM scout_conversations WHERE id = ? AND user_id = ?",
                (conv_id, user_id)
            ).fetchone()
        else:
            conv = conn.execute(
                "SELECT id FROM scout_conversations WHERE id = ? AND user_id IS NULL",
                (conv_id,)
            ).fetchone()
        
        if not conv:
            return False
            
        conn.execute("DELETE FROM scout_messages WHERE conversation_id = ?", (conv_id,))
        conn.execute("DELETE FROM scout_conversations WHERE id = ?", (conv_id,))
        return True


def add_message_to_conversation(
    conv_id: str,
    user_id: Optional[int],
    role: str,
    content: str,
    recommendations: Optional[List[Dict[str, Any]]] = None
):
    """Add a message to a conversation and update title if first message."""
    recs_json = json.dumps(recommendations) if recommendations else None
    msg_id = secrets.token_hex(12)

    with get_db() as conn:
        # Check if conversation exists; create if not
        conv = conn.execute(
            "SELECT id, title FROM scout_conversations WHERE id = ?",
            (conv_id,)
        ).fetchone()
        
        if not conv:
            title = content[:36].strip() + ("..." if len(content) > 36 else "") if role == "user" else "New Chat"
            conn.execute(
                "INSERT INTO scout_conversations (id, user_id, title, updated_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
                (conv_id, user_id, title)
            )
        else:
            # If current title is default, set from first user message
            if conv["title"] in ("New Conversation", "New Chat") and role == "user":
                new_title = content[:36].strip() + ("..." if len(content) > 36 else "")
                conn.execute(
                    "UPDATE scout_conversations SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (new_title, conv_id)
                )
            else:
                conn.execute(
                    "UPDATE scout_conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (conv_id,)
                )
            if user_id is not None:
                conn.execute(
                    "UPDATE scout_conversations SET user_id = COALESCE(user_id, ?) WHERE id = ?",
                    (user_id, conv_id)
                )

        conn.execute(
            """
            INSERT INTO scout_messages (id, conversation_id, role, content, recommendations_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (msg_id, conv_id, role, content, recs_json)
        )
