"""
WebSocket API endpoints
"""
from fastapi import APIRouter

router = APIRouter()


@router.websocket("/updates")
async def websocket_updates():
    """WebSocket endpoint for real-time updates"""
    pass