"""Session storage abstraction for API endpoints."""

from __future__ import annotations

from threading import RLock

from app.models import SessionContext


class SessionStore:
    """Thread-safe store for user-owned session contexts."""

    def __init__(self) -> None:
        self._sessions: dict[str, SessionContext] = {}
        self._lock = RLock()

    def get_or_create(self, session_id: str, user_id: str) -> SessionContext:
        """Return existing session context or create one for the requesting user."""
        with self._lock:
            context = self._sessions.get(session_id)
            if context is None:
                context = SessionContext(session_id=session_id, user_id=user_id)
                self._sessions[session_id] = context
                return context

            if context.user_id != user_id:
                raise PermissionError("Unauthorized access to session")

            return context

    def get(self, session_id: str, user_id: str) -> SessionContext | None:
        """Return existing session context for the requesting user, if any."""
        with self._lock:
            context = self._sessions.get(session_id)
            if context is None:
                return None

            if context.user_id != user_id:
                raise PermissionError("Unauthorized access to session")

            return context
