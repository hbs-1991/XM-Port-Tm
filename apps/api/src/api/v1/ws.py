"""
WebSocket API endpoints for real-time processing updates
"""
import json
import logging
import time
from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.core.auth import get_current_user_ws
from src.models.user import User

router = APIRouter()
logger = logging.getLogger(__name__)

# Global connection manager for WebSocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        logger.info(f"WebSocket connected for user {user_id}")

    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"WebSocket disconnected for user {user_id}")

    async def send_personal_message(self, message: dict, user_id: str):
        """Send message to all connections for a specific user"""
        if user_id in self.active_connections:
            disconnected = set()
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_text(json.dumps(message))
                except Exception as e:
                    logger.warning(f"Failed to send WebSocket message to user {user_id}: {e}")
                    disconnected.add(connection)
            
            # Remove disconnected connections
            for connection in disconnected:
                self.active_connections[user_id].discard(connection)

    async def send_processing_update(self, job_id: str, user_id: str, status: str, progress: int = 0, message: str = "", data: dict = None):
        """Send processing update to user"""
        update_message = {
            "type": "processing_update",
            "job_id": job_id,
            "status": status,
            "progress": progress,
            "message": message,
            "timestamp": int(time.time() * 1000),  # Milliseconds
            "data": data or {}
        }
        await self.send_personal_message(update_message, user_id)

manager = ConnectionManager()


@router.websocket("/processing-updates")
async def websocket_processing_updates(
    websocket: WebSocket,
    token: str = None,
    db: Session = Depends(get_db)
):
    """WebSocket endpoint for real-time processing updates"""
    try:
        # Authenticate user via token
        user = None
        if token:
            try:
                user = await get_current_user_ws(token)
                user_id = str(user.id)
            except Exception as e:
                logger.warning(f"WebSocket authentication failed: {e}")
                await websocket.close(code=4001, reason="Authentication failed")
                return
        else:
            await websocket.close(code=4001, reason="Authentication required")
            return
        
        await manager.connect(websocket, user_id)
        
        try:
            while True:
                # Keep connection alive and handle any client messages
                data = await websocket.receive_text()
                # Echo received message or handle ping/pong
                await websocket.send_text(json.dumps({"type": "pong", "message": "Connection alive"}))
                
        except WebSocketDisconnect:
            manager.disconnect(websocket, user_id)
            
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except:
            pass