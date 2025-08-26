"""
XM-Port FastAPI Application Entry Point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from src.api.v1 import auth, processing, admin, users, xml_generation, ws
from src.core.config import settings
from src.middleware.security_headers import SecurityHeadersMiddleware

# Configure logging
logging.basicConfig(level=logging.DEBUG if settings.is_development else logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="XM-Port API",
    description="AI-powered customs documentation platform API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS SETUP - Comprehensive headers for cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1):(3000|3001)$",    
    allow_credentials=True,  # Must be False when using "*"
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[
        "Content-Type",
        "Cache-Control",
        "X-Content-Type-Options",
        "X-Frame-Options",
        "X-XSS-Protection"
    ],
)

# Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

logger.info("CORS and security headers middleware applied")

# API routes
app.include_router(auth.router, prefix="/api/v1/auth", tags=["authentication"])
app.include_router(processing.router, prefix="/api/v1/processing", tags=["processing"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(xml_generation.router, prefix="/api/v1", tags=["xml-generation"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])
app.include_router(ws.router, prefix="/api/v1/ws", tags=["websocket"])


@app.get("/")
async def root():
    """Root endpoint for health check"""
    return {"message": "XM-Port API is running", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "xm-port-api"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True
    )