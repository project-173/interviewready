"""Firebase authentication and initialization."""

import firebase_admin
from firebase_admin import credentials, auth
from fastapi.concurrency import run_in_threadpool
from app.core.config import settings
from typing import Optional, Dict, Any
import json


def init_firebase() -> None:
    """Initialize Firebase Admin SDK."""
    try:
        if not settings.FIREBASE_ENABLED:
            print("Firebase is disabled in configuration")
            return
            
        if not firebase_admin._apps:
            # Create Firebase credentials from environment variables
            firebase_config = {
                "type": "service_account",
                "project_id": settings.FIREBASE_PROJECT_ID,
                "private_key_id": settings.FIREBASE_PRIVATE_KEY_ID,
                "private_key": settings.FIREBASE_PRIVATE_KEY.replace("\\n", "\n"),
                "client_email": settings.FIREBASE_CLIENT_EMAIL,
                "client_id": settings.FIREBASE_CLIENT_ID,
                "auth_uri": settings.FIREBASE_AUTH_URI,
                "token_uri": settings.FIREBASE_TOKEN_URI,
            }
            
            cred = credentials.Certificate(firebase_config)
            firebase_admin.initialize_app(cred)
            print("Firebase Admin SDK initialized successfully")
    except Exception as e:
        print(f"Failed to initialize Firebase: {e}")
        raise


async def verify_firebase_token(id_token: str) -> Optional[Dict[str, Any]]:
    """
    Verify Firebase ID token and return decoded user information.
    
    Args:
        id_token: Firebase ID token from client
        
    Returns:
        Decoded token payload or None if verification fails
    """
    if not settings.FIREBASE_ENABLED:
        return None
        
    try:
        # Firebase SDK token verification is synchronous; isolate it from the event loop.
        decoded_token = await run_in_threadpool(auth.verify_id_token, id_token)
        return decoded_token
    except auth.InvalidIdTokenError:
        return None
    except auth.ExpiredIdTokenError:
        return None
    except auth.RevokedIdTokenError:
        return None
    except Exception as e:
        print(f"Token verification error: {e}")
        return None


def get_user_from_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Get user information from Firebase token.
    
    Args:
        token: Firebase ID token
        
    Returns:
        User information or None if invalid
    """
    if not settings.FIREBASE_ENABLED:
        return None
        
    try:
        decoded_token = auth.verify_id_token(token)
        return {
            "uid": decoded_token["uid"],
            "email": decoded_token.get("email"),
            "name": decoded_token.get("name"),
            "picture": decoded_token.get("picture"),
        }
    except Exception as e:
        print(f"Error getting user from token: {e}")
        return None
