"""Session storage abstraction for API endpoints."""

from __future__ import annotations

import time
from threading import RLock
from typing import Optional

from app.models import SessionContext


SESSION_EXPIRY_SECONDS = 3600


class SessionStore:
    """Thread-safe store for user-owned session contexts."""

    def __init__(self) -> None:
        self._sessions: dict[str, SessionContext] = {}
        self._session_timestamps: dict[str, float] = {}
        self._lock = RLock()
        self._used_session_ids: set[str] = set()

    def _generate_session_id(self) -> str:
        """Generate a unique session ID that is not currently in use."""
        import uuid
        import random
        import string

        attempts = 0
        while attempts < 100:
            session_id = f"session_{uuid.uuid4().hex[:16]}"
            if session_id not in self._used_session_ids:
                self._used_session_ids.add(session_id)
                return session_id
            attempts += 1

        oldest_session = min(self._session_timestamps.items(), key=lambda x: x[1])
        self._remove_session_id(oldest_session[0])
        session_id = f"session_{uuid.uuid4().hex[:16]}"
        self._used_session_ids.add(session_id)
        return session_id

    def _remove_session_id(self, session_id: str) -> None:
        """Remove a session ID from the used set (called when session is expired)."""
        self._used_session_ids.discard(session_id)
        self._session_timestamps.pop(session_id, None)

    def create_session(self, user_id: str) -> tuple[str, SessionContext]:
        """Create a new session and return the session ID and context."""
        with self._lock:
            session_id = self._generate_session_id()
            timestamp = time.time()
            self._session_timestamps[session_id] = timestamp
            context = SessionContext(session_id=session_id, user_id=user_id)
            self._sessions[session_id] = context
            return session_id, context

    def cleanup_expired_sessions(self) -> int:
        """Remove expired sessions and return count of removed sessions."""
        current_time = time.time()
        expired_session_ids = [
            sid
            for sid, ts in self._session_timestamps.items()
            if current_time - ts > SESSION_EXPIRY_SECONDS
        ]

        for session_id in expired_session_ids:
            self._remove_session_id(session_id)
            self._sessions.pop(session_id, None)

        return len(expired_session_ids)

    def get_or_create(self, session_id: str, user_id: str) -> SessionContext:
        """Return existing session context or create one for the requesting user."""
        with self._lock:
            if session_id in self._sessions:
                context = self._sessions[session_id]
                if context.user_id != user_id:
                    raise PermissionError("Unauthorized access to session")
                self._session_timestamps[session_id] = time.time()
                return context

            if session_id in self._used_session_ids:
                raise ValueError("Session ID already in use")

            context = SessionContext(session_id=session_id, user_id=user_id)
            self._sessions[session_id] = context
            self._session_timestamps[session_id] = time.time()
            self._used_session_ids.add(session_id)
            return context

    def get(self, session_id: str, user_id: str) -> SessionContext | None:
        """Return existing session context for the requesting user, if any."""
        with self._lock:
            context = self._sessions.get(session_id)
            if context is None:
                return None

            if context.user_id != user_id:
                raise PermissionError("Unauthorized access to session")

            self._session_timestamps[session_id] = time.time()
            return context
