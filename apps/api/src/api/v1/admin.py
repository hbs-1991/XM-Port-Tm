"""
Admin API endpoints
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/users")
async def get_users():
    """Get all users endpoint"""
    return {"message": "Admin users endpoint - to be implemented"}


@router.get("/analytics")
async def get_analytics():
    """Get analytics endpoint"""
    return {"message": "Admin analytics endpoint - to be implemented"}