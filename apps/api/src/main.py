"""
XM-Port FastAPI Application Entry Point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

from src.api.v1 import auth, processing, admin, xml_generation, ws
from src.core.config import settings
from src.middleware import setup_rate_limiting

app = FastAPI(
    title="XM-Port API",
    description="AI-powered customs documentation platform API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Security middleware
if settings.is_production:
    app.add_middleware(HTTPSRedirectMiddleware)
    app.add_middleware(
        TrustedHostMiddleware, 
        allowed_hosts=settings.ALLOWED_HOSTS
    )
else:
    # In development, be more permissive with host headers
    app.add_middleware(
        TrustedHostMiddleware, 
        allowed_hosts=["*"]  # Allow all hosts in development
    )

# CORS middleware with security headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Requested-With",
        "Accept",
        "Origin",
        "User-Agent",
        "X-CSRFToken"
    ],
    expose_headers=["X-Total-Count", "X-Page-Count"],
    max_age=3600
)

# Setup rate limiting
setup_rate_limiting(app)

# API routes
app.include_router(auth.router, prefix="/api/v1/auth", tags=["authentication"])
app.include_router(processing.router, prefix="/api/v1/processing", tags=["processing"])
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