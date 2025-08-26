"""
XM-Port FastAPI Application Entry Point
"""
from fastapi import FastAPI, Response
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

# CORS middleware MUST be added first (before other middleware)
# In development, use specific origins (cannot use * with credentials)
if settings.is_development:
    cors_origins = [
        "http://localhost:3000",
        "http://localhost:3001", 
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001"
    ]
else:
    cors_origins = settings.cors_origins_list

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
    expose_headers=["X-Total-Count", "X-Page-Count"],
    max_age=3600
)

# Security middleware (added AFTER CORS)
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


@app.options("/api/v1/auth/register")
async def handle_register_preflight():
    """Explicit OPTIONS handler for register endpoint"""
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "http://localhost:3001",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Accept, ngrok-skip-browser-warning",
            "Access-Control-Allow-Credentials": "true",
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True
    )