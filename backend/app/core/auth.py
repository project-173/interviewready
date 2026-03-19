"""Authentication and authorization utilities."""

from typing import Any, Dict
from fastapi import HTTPException, status, Header
from app.core.config import settings


async def get_current_user(
    authorization: str | None = Header(None),
) -> Dict[str, Any]:
    """
    Extract the current user from the Authorization header.
    
    If AUTH_ENABLED is False, returns a mock user.
    If AUTH_ENABLED is True, validates the Firebase token.
    
    Args:
        authorization: Bearer token from the Authorization header
        
    Returns:
        Dict with user information (uid, user_id, or sub)
        
    Raises:
        HTTPException: If authentication is required but token is invalid
    """
    
    # If auth is disabled, return a mock user
    if not settings.AUTH_ENABLED:
        return {
            "uid": settings.AUTH_DISABLED_USER_ID,
            "user_id": settings.AUTH_DISABLED_USER_ID,
            "sub": settings.AUTH_DISABLED_USER_ID,
        }
    
    # If auth is enabled, validate the token
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Extract Bearer token
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise ValueError("Invalid authentication scheme")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # For now, just return a mock user from the token
    # In production, this would validate the Firebase token
    return {
        "uid": token[:20],  # Mock UID from token prefix
        "user_id": token[:20],
        "sub": token[:20],
    }
