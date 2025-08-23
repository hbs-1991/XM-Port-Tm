"""
API v1 endpoints package
"""
from .auth import router as auth_router
from .admin import router as admin_router
from .processing import router as processing_router
from .xml_generation import router as xml_generation_router
from .ws import router as ws_router

__all__ = [
    "auth_router",
    "admin_router", 
    "processing_router",
    "xml_generation_router",
    "ws_router"
]