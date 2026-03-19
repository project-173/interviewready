"""Main FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
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
    yield
    print(f"Shutting down {settings.APP_NAME}...")


app = FastAPI(
    title=settings.APP_NAME,
    description="Production-Ready Multi-Agent AI Backend with Gemini",
    version=settings.VERSION,
    lifespan=lifespan,
    redirect_slashes=False,
)

# Configure CORS
# When allow_credentials=True, origins must be explicit (no wildcard)
origins = []
if isinstance(settings.ALLOWED_HOSTS, list):
    origins = [o for o in settings.ALLOWED_HOSTS if o != "*"]
else:
    origins = [settings.ALLOWED_HOSTS] if settings.ALLOWED_HOSTS != "*" else []

# Ensure frontend is always in the list
frontend_url = "https://interviewready-frontend-266623940622.asia-southeast1.run.app"
if frontend_url not in origins:
    origins.append(frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware for logging requests (useful for Cloud Run debugging)
@app.middleware("http")
async def log_requests(request, call_next):
    import time
    start_time = time.time()
    origin = request.headers.get("origin")
    response = await call_next(request)
    duration = time.time() - start_time
    print(f"DEBUG: {request.method} {request.url.path} status={response.status_code} duration={duration:.2f}s origin={origin}")
    return response

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
        "debug": settings.DEBUG,
        "environment": settings.APP_ENV,
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
