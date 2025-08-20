"""
Admin API endpoints
"""
from fastapi import APIRouter, Depends

from src.core.auth import get_admin_user
from src.models.user import User

router = APIRouter()


@router.get("/users")
async def get_users(current_user: User = Depends(get_admin_user)):
    """Get all users endpoint - requires ADMIN role"""
    return {"message": "Admin users endpoint - to be implemented", "admin_id": str(current_user.id)}


@router.get("/analytics")
async def get_analytics(current_user: User = Depends(get_admin_user)):
    """Get analytics endpoint - requires ADMIN role"""
    return {"message": "Admin analytics endpoint - to be implemented", "admin_id": str(current_user.id)}