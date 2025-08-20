"""
File processing API endpoints
"""
from fastapi import APIRouter, Depends

from src.core.auth import get_current_active_user
from src.models.user import User

router = APIRouter()


@router.post("/upload")
async def upload_file(current_user: User = Depends(get_current_active_user)):
    """File upload endpoint - requires authentication"""
    return {"message": "File upload endpoint - to be implemented", "user_id": str(current_user.id)}


@router.get("/jobs")
async def get_processing_jobs(current_user: User = Depends(get_current_active_user)):
    """Get processing jobs endpoint - requires authentication"""
    return {"message": "Processing jobs endpoint - to be implemented", "user_id": str(current_user.id)}