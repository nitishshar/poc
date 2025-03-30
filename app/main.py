import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from app.config.settings import settings
from app.api.routes import router as api_router
from app.api.chat_routes import router as chat_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("app")

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="A service for document processing, semantic parsing, and vector embedding generation",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development - restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(api_router)
app.include_router(chat_router)


@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": settings.PROJECT_NAME,
        "version": "1.0.0",
        "status": "online",
        "docs_url": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred", "error": str(exc)},
    )


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    ) 