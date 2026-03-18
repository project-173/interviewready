"""Main FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.api.v1 import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    yield
    # Cleanup can be added here


app = FastAPI(
    title=settings.APP_NAME,
    description="Production-Ready Multi-Agent AI Backend with Gemini",
    version=settings.VERSION,
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": settings.VERSION}


@app.get("/info")
async def app_info():
    """Application info endpoint."""
    return {
        "name": settings.APP_NAME,
        "version": settings.VERSION,
        "log_level": settings.LOG_LEVEL
    }


@app.get("/metrics")
async def metrics():
    """Metrics endpoint placeholder."""
    return {
        "status": "metrics_placeholder",
        "endpoints": ["health", "info", "metrics"]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.SERVER_PORT,
        reload=settings.LOG_LEVEL == "DEBUG",
    )
