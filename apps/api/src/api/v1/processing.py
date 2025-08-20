"""
File processing API endpoints
"""
from fastapi import APIRouter

router = APIRouter()


@router.post("/upload")
async def upload_file():
    """File upload endpoint"""
    return {"message": "File upload endpoint - to be implemented"}


@router.get("/jobs")
async def get_processing_jobs():
    """Get processing jobs endpoint"""
    return {"message": "Processing jobs endpoint - to be implemented"}