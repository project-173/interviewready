"""Firebase authentication middleware for FastAPI."""

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.firebase import verify_firebase_token
from app.core.config import settings
from typing import Optional, Dict, Any

# Initialize HTTP Bearer security scheme
optional_security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(optional_security),
) -> Dict[str, Any]:
    """
    Authenticate and retrieve current user from Firebase token.
    
    Args:
        credentials: HTTP Bearer credentials containing Firebase ID token
        
    Returns:
        Decoded user information from Firebase
        
    Raises:
        HTTPException: If authentication fails
    """
    if not settings.AUTH_ENABLED:
        return {"uid": settings.AUTH_DISABLED_USER_ID}

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    user_info = await verify_firebase_token(token)
    
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user_info


async def get_optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Security(optional_security)) -> Optional[Dict[str, Any]]:
    """
    Optionally retrieve current user from Firebase token.
    Does not raise exception if authentication fails.
    
    Args:
        credentials: Optional HTTP Bearer credentials
        
    Returns:
        Decoded user information from Firebase or None
    """
    if not settings.AUTH_ENABLED:
        return {"uid": settings.AUTH_DISABLED_USER_ID}

    if not credentials:
        return None
    
    token = credentials.credentials
    return await verify_firebase_token(token)
