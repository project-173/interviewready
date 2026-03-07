"""Main API router for v1 endpoints."""

from fastapi import APIRouter
from app.api.v1.endpoints import chat, agents, sessions

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
