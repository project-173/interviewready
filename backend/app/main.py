"""Main FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.firebase import init_firebase
from app.api.v1 import api_router

# Safe import for Langfuse
try:
    from langfuse.callback import CallbackHandler
    HAS_LANGFUSE = True
except ImportError:
    HAS_LANGFUSE = False
    print("WARNING: Langfuse package not found. Monitoring is disabled.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    print(f"Starting {settings.APP_NAME} v{settings.VERSION}...")
    
    # Initialize Firebase with error handling to prevent startup crashes
    try:
        if settings.FIREBASE_ENABLED:
            print("Initializing Firebase...")
            init_firebase()
            print("Firebase initialized successfully.")
        else:
            print("Firebase is disabled via configuration.")
    except Exception as e:
        print(f"CRITICAL ERROR during Firebase initialization: {e}")
        # We don't re-raise here to allow the container to start and serve health checks
        # even if Firebase fails, allowing us to debug via logs.
    
    print(f"{settings.APP_NAME} lifespan startup complete.")
    yield
    print(f"Shutting down {settings.APP_NAME}...")


app = FastAPI(
    title=settings.APP_NAME,
    description="Production-Ready Multi-Agent AI Backend with Gemini and Firebase",
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

# Initialize Langfuse Callback Handler safely
langfuse_handler = None
if HAS_LANGFUSE and settings.LANGFUSE_PUBLIC_KEY:
    try:
        langfuse_handler = CallbackHandler(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            host=settings.LANGFUSE_HOST
        )
        print("Langfuse callback handler initialized.")
    except Exception as e:
        print(f"Failed to initialize Langfuse handler: {e}")


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
        "debug": settings.DEBUG
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
        reload=settings.DEBUG,
    )
