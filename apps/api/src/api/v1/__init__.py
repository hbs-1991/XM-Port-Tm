"""
API v1 endpoints package
"""
from .auth import router as auth_router
from .admin import router as admin_router
from .processing import router as processing_router
from .users import router as users_router
from .xml_generation import router as xml_generation_router
from .hs_matching import router as hs_matching_router
from .ws import router as ws_router

__all__ = [
    "auth_router",
    "admin_router", 
    "processing_router",
    "users_router",
    "xml_generation_router",
    "hs_matching_router",
    "ws_router"
]